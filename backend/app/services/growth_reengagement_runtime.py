from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.datetime_utils import utcnow
from app.models.card_response import CardResponse
from app.models.journal import Journal
from app.models.user import User
from app.services.feature_flags import resolve_feature_flags

logger = logging.getLogger(__name__)

DEFAULT_SOCIAL_SHARE_RECENT_ACTIVITY_DAYS = 7
DEFAULT_TIME_CAPSULE_MIN_ACCOUNT_AGE_DAYS = 30
DEFAULT_TIME_CAPSULE_MIN_COMBINED_JOURNALS = 6


@dataclass(frozen=True)
class ReengagementHookRecommendation:
    hook_type: str
    eligible: bool
    reason: str
    dedupe_key: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ReengagementHooksEvaluation:
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    hooks: list[ReengagementHookRecommendation]


def _safe_count(session: Session, statement) -> int:
    value = session.exec(statement).one()
    return int(value or 0)


def _stable_dedupe_key(
    *,
    hook_type: str,
    actor_user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
    bucket: str,
) -> str:
    seed = f"{hook_type}:{actor_user_id}:{partner_user_id}:{bucket}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _weekly_bucket(now) -> str:
    iso_year, iso_week, _ = now.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _monthly_bucket(now) -> str:
    return f"{now.year:04d}-{now.month:02d}"


def _resolve_pair_journal_count(*, session: Session, user_id: uuid.UUID, partner_id: uuid.UUID) -> int:
    statement = select(func.count(Journal.id)).where(
        col(Journal.user_id).in_([user_id, partner_id]),
        Journal.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _resolve_user_journal_count(*, session: Session, user_id: uuid.UUID) -> int:
    statement = select(func.count(Journal.id)).where(
        Journal.user_id == user_id,
        Journal.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _resolve_pair_card_response_count(*, session: Session, user_id: uuid.UUID, partner_id: uuid.UUID) -> int:
    statement = select(func.count(CardResponse.id)).where(
        col(CardResponse.user_id).in_([user_id, partner_id]),
        CardResponse.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _resolve_pair_latest_journal_at(
    *,
    session: Session,
    user_id: uuid.UUID,
    partner_id: uuid.UUID,
):
    return session.exec(
        select(func.max(Journal.created_at)).where(
            col(Journal.user_id).in_([user_id, partner_id]),
            Journal.deleted_at.is_(None),
        )
    ).one()


def _resolve_user_terms_accepted_at(*, session: Session, user_id: uuid.UUID):
    return session.exec(select(User.terms_accepted_at).where(User.id == user_id)).one()


def evaluate_reengagement_hooks(
    *,
    session: Session,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
) -> ReengagementHooksEvaluation:
    has_partner_context = partner_user_id is not None
    resolved = resolve_feature_flags(has_partner=has_partner_context)
    kill_switch_active = bool(resolved.kill_switches.get("disable_growth_reengagement_hooks", False))
    feature_enabled = bool(resolved.flags.get("growth_reengagement_hooks_enabled", False))

    if not has_partner_context or kill_switch_active or not feature_enabled:
        growth_reengagement_runtime_metrics.record_evaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            social_share_eligible=False,
            time_capsule_eligible=False,
        )
        return ReengagementHooksEvaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            kill_switch_active=kill_switch_active,
            hooks=[],
        )

    assert partner_user_id is not None
    now = utcnow()
    user_journal_count = _resolve_user_journal_count(session=session, user_id=current_user_id)
    partner_journal_count = _resolve_user_journal_count(session=session, user_id=partner_user_id)
    pair_journal_count = _resolve_pair_journal_count(
        session=session,
        user_id=current_user_id,
        partner_id=partner_user_id,
    )
    pair_card_response_count = _resolve_pair_card_response_count(
        session=session,
        user_id=current_user_id,
        partner_id=partner_user_id,
    )
    pair_latest_journal_at = _resolve_pair_latest_journal_at(
        session=session,
        user_id=current_user_id,
        partner_id=partner_user_id,
    )
    recent_activity_floor = now - timedelta(days=DEFAULT_SOCIAL_SHARE_RECENT_ACTIVITY_DAYS)
    has_recent_pair_activity = bool(pair_latest_journal_at and pair_latest_journal_at >= recent_activity_floor)

    user_terms_accepted_at = _resolve_user_terms_accepted_at(session=session, user_id=current_user_id)
    partner_terms_accepted_at = _resolve_user_terms_accepted_at(session=session, user_id=partner_user_id)
    account_age_floor = now - timedelta(days=DEFAULT_TIME_CAPSULE_MIN_ACCOUNT_AGE_DAYS)
    pair_mature_enough = bool(
        user_terms_accepted_at
        and partner_terms_accepted_at
        and user_terms_accepted_at <= account_age_floor
        and partner_terms_accepted_at <= account_age_floor
    )

    social_share_eligible = (
        user_journal_count >= 1 and partner_journal_count >= 1 and has_recent_pair_activity
    )
    if user_journal_count < 1 or partner_journal_count < 1:
        social_share_reason = "insufficient_pair_journals"
    elif not has_recent_pair_activity:
        social_share_reason = "recent_activity_missing"
    else:
        social_share_reason = "eligible"

    time_capsule_eligible = (
        pair_mature_enough
        and pair_journal_count >= DEFAULT_TIME_CAPSULE_MIN_COMBINED_JOURNALS
        and pair_card_response_count >= 2
    )
    if not pair_mature_enough:
        time_capsule_reason = "pair_too_new"
    elif pair_journal_count < DEFAULT_TIME_CAPSULE_MIN_COMBINED_JOURNALS:
        time_capsule_reason = "insufficient_history_journals"
    elif pair_card_response_count < 2:
        time_capsule_reason = "insufficient_history_card_responses"
    else:
        time_capsule_reason = "eligible"

    hooks = [
        ReengagementHookRecommendation(
            hook_type="SOCIAL_SHARE_CARD",
            eligible=social_share_eligible,
            reason=social_share_reason,
            dedupe_key=_stable_dedupe_key(
                hook_type="SOCIAL_SHARE_CARD",
                actor_user_id=current_user_id,
                partner_user_id=partner_user_id,
                bucket=_weekly_bucket(now),
            ),
            metadata={
                "user_journal_count": user_journal_count,
                "partner_journal_count": partner_journal_count,
                "pair_journal_count": pair_journal_count,
                "recent_activity_window_days": DEFAULT_SOCIAL_SHARE_RECENT_ACTIVITY_DAYS,
                "has_recent_pair_activity": has_recent_pair_activity,
            },
        ),
        ReengagementHookRecommendation(
            hook_type="TIME_CAPSULE",
            eligible=time_capsule_eligible,
            reason=time_capsule_reason,
            dedupe_key=_stable_dedupe_key(
                hook_type="TIME_CAPSULE",
                actor_user_id=current_user_id,
                partner_user_id=partner_user_id,
                bucket=_monthly_bucket(now),
            ),
            metadata={
                "pair_journal_count": pair_journal_count,
                "pair_card_response_count": pair_card_response_count,
                "minimum_account_age_days": DEFAULT_TIME_CAPSULE_MIN_ACCOUNT_AGE_DAYS,
                "minimum_combined_journals": DEFAULT_TIME_CAPSULE_MIN_COMBINED_JOURNALS,
                "pair_mature_enough": pair_mature_enough,
            },
        ),
    ]

    logger.info(
        "reengagement_hooks_evaluated enabled=true has_partner=%s social_share=%s time_capsule=%s",
        has_partner_context,
        social_share_eligible,
        time_capsule_eligible,
    )
    growth_reengagement_runtime_metrics.record_evaluation(
        enabled=True,
        has_partner_context=has_partner_context,
        social_share_eligible=social_share_eligible,
        time_capsule_eligible=time_capsule_eligible,
    )
    return ReengagementHooksEvaluation(
        enabled=True,
        has_partner_context=has_partner_context,
        kill_switch_active=False,
        hooks=hooks,
    )


class GrowthReengagementRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._counts: dict[str, int] = {}

    def _increment(self, key: str, value: int = 1) -> None:
        self._counts[key] = self._counts.get(key, 0) + value

    def record_evaluation(
        self,
        *,
        enabled: bool,
        has_partner_context: bool,
        social_share_eligible: bool,
        time_capsule_eligible: bool,
    ) -> None:
        with self._lock:
            self._increment("growth_reengagement_evaluations_total")
            if enabled:
                self._increment("growth_reengagement_enabled_total")
            else:
                self._increment("growth_reengagement_disabled_total")
            if has_partner_context:
                self._increment("growth_reengagement_partner_context_total")
            if social_share_eligible:
                self._increment("growth_reengagement_social_share_eligible_total")
            if time_capsule_eligible:
                self._increment("growth_reengagement_time_capsule_eligible_total")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


growth_reengagement_runtime_metrics = GrowthReengagementRuntimeMetrics()
