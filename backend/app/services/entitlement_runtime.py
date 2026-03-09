"""MON-01/MON-02: Entitlement quota runtime evaluation.

Server-side source-of-truth for plan-based feature gating.
Evaluates user entitlements based on billing state.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import settings

logger = logging.getLogger(__name__)

# Plan quota definitions: Free / Premium / Couple
PLAN_QUOTAS: dict[str, dict[str, Any]] = {
    "free": {
        "journals_per_day": 3,
        "card_draws_per_day": 5,
        "ai_analysis_enabled": True,
        "push_notifications_enabled": True,
        "partner_binding_enabled": True,
        "export_enabled": False,
        "priority_support": False,
    },
    "premium": {
        "journals_per_day": -1,  # unlimited
        "card_draws_per_day": -1,
        "ai_analysis_enabled": True,
        "push_notifications_enabled": True,
        "partner_binding_enabled": True,
        "export_enabled": True,
        "priority_support": True,
    },
    "couple": {
        "journals_per_day": -1,
        "card_draws_per_day": -1,
        "ai_analysis_enabled": True,
        "push_notifications_enabled": True,
        "partner_binding_enabled": True,
        "export_enabled": True,
        "priority_support": True,
    },
}

# States that grant "active" entitlements
ACTIVE_BILLING_STATES = {"TRIAL", "ACTIVE", "GRACE_PERIOD"}


def resolve_user_plan(*, session: Session, user_id: UUID) -> str:
    """Resolve the effective plan for a user based on billing state.

    Returns: 'free', 'premium', or 'couple'
    """
    try:
        from app.models.billing import BillingEntitlementState

        state = session.exec(
            select(BillingEntitlementState)
            .where(BillingEntitlementState.user_id == user_id)
            .order_by(BillingEntitlementState.revision.desc())
        ).first()
        if not state:
            return "free"
        current_state = str(
            getattr(state, "lifecycle_state", None)
            or getattr(state, "current_state", None)
            or ""
        ).strip().upper()
        if current_state not in ACTIVE_BILLING_STATES:
            return "free"
        current_plan = (
            getattr(state, "current_plan", None)
            or getattr(state, "plan_id", None)
            or "free"
        )
        return str(current_plan).strip().lower()
    except Exception:
        logger.warning(
            "entitlement_resolve_failed user_id=%s", user_id,
            exc_info=settings.LOG_INCLUDE_STACKTRACE,
        )
        return "free"


def evaluate_entitlement(
    *,
    session: Session,
    user_id: UUID,
    feature: str,
) -> dict[str, Any]:
    """Evaluate whether a user is entitled to a specific feature.

    Returns dict with 'allowed', 'plan', 'quota', 'reason'.
    """
    plan = resolve_user_plan(session=session, user_id=user_id)
    quotas = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
    feature_key = feature.strip().lower()

    if feature_key not in quotas:
        return {
            "allowed": True,
            "plan": plan,
            "quota": None,
            "reason": "feature_not_gated",
        }

    value = quotas[feature_key]
    if isinstance(value, bool):
        return {
            "allowed": value,
            "plan": plan,
            "quota": value,
            "reason": "allowed" if value else "feature_disabled_for_plan",
        }
    if isinstance(value, int) and value == -1:
        return {
            "allowed": True,
            "plan": plan,
            "quota": "unlimited",
            "reason": "allowed",
        }
    return {
        "allowed": True,
        "plan": plan,
        "quota": value,
        "reason": "quota_enforced",
    }


def list_entitlements(*, session: Session, user_id: UUID) -> dict[str, Any]:
    """Return full entitlement snapshot for a user."""
    plan = resolve_user_plan(session=session, user_id=user_id)
    quotas = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
    return {
        "plan": plan,
        "quotas": dict(quotas),
    }


def resolve_quota_limit(
    *,
    session: Session,
    user_id: UUID,
    feature: str,
) -> int | None:
    """Resolve integer quota limit for a feature.

    Returns:
      - None: unlimited or not quota-based
      - int >= 0: concrete daily quota limit
    """
    decision = evaluate_entitlement(session=session, user_id=user_id, feature=feature)
    if not bool(decision.get("allowed", True)):
        return 0
    quota = decision.get("quota")
    if quota == "unlimited":
        return None
    if isinstance(quota, bool):
        return None
    if isinstance(quota, int):
        return max(0, quota)
    return None
