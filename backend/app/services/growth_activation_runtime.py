from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.card_response import CardResponse
from app.models.growth_referral_event import GrowthReferralEvent, GrowthReferralEventType
from app.models.journal import Journal
from app.models.user import User
from app.services.feature_flags import resolve_feature_flags

DEFAULT_WINDOW_DAYS = 30
DEFAULT_MIN_SIGNUPS = 10
DEFAULT_TARGET_BIND_RATE = 0.3
DEFAULT_TARGET_FIRST_JOURNAL_RATE = 0.2
DEFAULT_TARGET_FIRST_DECK_RATE = 0.15

ACTIVATION_DEFINITION_VERSION = "1.0.0"


def _safe_int(value: Any, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return minimum
    return parsed if parsed >= minimum else minimum


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _normalize_rate(value: Any, *, default: float) -> float:
    parsed = _safe_float(value)
    if parsed is None:
        return default
    return max(0.0, min(1.0, parsed))


def _iso_utc(value: Any) -> str:
    return f"{value.isoformat()}Z"


def is_growth_activation_dashboard_enabled() -> bool:
    resolved = resolve_feature_flags(has_partner=True)
    if bool(resolved.kill_switches.get("disable_growth_activation_dashboard", False)):
        return False
    return bool(resolved.flags.get("growth_activation_dashboard_enabled", False))


def build_growth_activation_funnel_snapshot(
    *,
    session: Session,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    safe_window_days = max(1, int(window_days))
    now = utcnow()
    window_started_at = now - timedelta(days=safe_window_days)

    targets = {
        "bind_rate": DEFAULT_TARGET_BIND_RATE,
        "first_journal_rate": DEFAULT_TARGET_FIRST_JOURNAL_RATE,
        "first_deck_rate": DEFAULT_TARGET_FIRST_DECK_RATE,
    }

    if not is_growth_activation_dashboard_enabled():
        return {
            "status": "disabled",
            "definition_version": ACTIVATION_DEFINITION_VERSION,
            "window_days": safe_window_days,
            "window_started_at": _iso_utc(window_started_at),
            "window_ended_at": _iso_utc(now),
            "counts": {
                "signup_completed_users": 0,
                "partner_bound_users": 0,
                "first_journal_users": 0,
                "first_deck_users": 0,
            },
            "metrics": {
                "bind_rate": None,
                "first_journal_rate": None,
                "first_deck_rate": None,
                "journal_from_bound_rate": None,
                "deck_from_journal_rate": None,
            },
            "targets": targets,
            "referral_companion": {
                "counts": {
                    GrowthReferralEventType.LANDING_VIEW.value: 0,
                    GrowthReferralEventType.SIGNUP.value: 0,
                    GrowthReferralEventType.COUPLE_INVITE.value: 0,
                    GrowthReferralEventType.BIND.value: 0,
                },
                "metrics": {
                    "signup_from_view_rate": None,
                    "bind_from_signup_rate": None,
                },
            },
        }

    signup_user_ids = set(
        session.exec(
            select(User.id).where(
                User.deleted_at.is_(None),
                User.terms_accepted_at.is_not(None),
                User.terms_accepted_at >= window_started_at,
            )
        ).all()
    )

    if signup_user_ids:
        partner_bound_user_ids = set(
            session.exec(
                select(User.id).where(
                    User.id.in_(signup_user_ids),
                    User.deleted_at.is_(None),
                    User.partner_id.is_not(None),
                )
            ).all()
        )
        first_journal_user_ids = set(
            session.exec(
                select(Journal.user_id).where(
                    Journal.user_id.in_(signup_user_ids),
                    Journal.deleted_at.is_(None),
                )
            ).all()
        )
        first_deck_user_ids = set(
            session.exec(
                select(CardResponse.user_id).where(
                    CardResponse.user_id.in_(signup_user_ids),
                    CardResponse.deleted_at.is_(None),
                )
            ).all()
        )
    else:
        partner_bound_user_ids = set()
        first_journal_user_ids = set()
        first_deck_user_ids = set()

    signup_total = len(signup_user_ids)
    partner_bound_total = len(partner_bound_user_ids)
    first_journal_total = len(first_journal_user_ids)
    first_deck_total = len(first_deck_user_ids)

    referral_counts = {
        GrowthReferralEventType.LANDING_VIEW.value: 0,
        GrowthReferralEventType.SIGNUP.value: 0,
        GrowthReferralEventType.COUPLE_INVITE.value: 0,
        GrowthReferralEventType.BIND.value: 0,
    }
    for event_type in session.exec(
        select(GrowthReferralEvent.event_type).where(
            GrowthReferralEvent.created_at >= window_started_at
        )
    ).all():
        key = str(getattr(event_type, "value", event_type)).upper()
        if key in referral_counts:
            referral_counts[key] += 1

    referral_view_total = _safe_int(referral_counts[GrowthReferralEventType.LANDING_VIEW.value])
    referral_signup_total = _safe_int(referral_counts[GrowthReferralEventType.SIGNUP.value])
    referral_bind_total = _safe_int(referral_counts[GrowthReferralEventType.BIND.value])

    return {
        "status": "ok",
        "definition_version": ACTIVATION_DEFINITION_VERSION,
        "window_days": safe_window_days,
        "window_started_at": _iso_utc(window_started_at),
        "window_ended_at": _iso_utc(now),
        "counts": {
            "signup_completed_users": signup_total,
            "partner_bound_users": partner_bound_total,
            "first_journal_users": first_journal_total,
            "first_deck_users": first_deck_total,
        },
        "metrics": {
            "bind_rate": _safe_ratio(partner_bound_total, signup_total),
            "first_journal_rate": _safe_ratio(first_journal_total, signup_total),
            "first_deck_rate": _safe_ratio(first_deck_total, signup_total),
            "journal_from_bound_rate": _safe_ratio(first_journal_total, partner_bound_total),
            "deck_from_journal_rate": _safe_ratio(first_deck_total, first_journal_total),
        },
        "targets": targets,
        "referral_companion": {
            "counts": referral_counts,
            "metrics": {
                "signup_from_view_rate": _safe_ratio(referral_signup_total, referral_view_total),
                "bind_from_signup_rate": _safe_ratio(referral_bind_total, referral_signup_total),
            },
        },
    }


def evaluate_growth_activation_funnel_snapshot(
    snapshot: dict[str, Any],
    *,
    min_signups: int = DEFAULT_MIN_SIGNUPS,
    target_bind_rate: float = DEFAULT_TARGET_BIND_RATE,
    target_first_journal_rate: float = DEFAULT_TARGET_FIRST_JOURNAL_RATE,
    target_first_deck_rate: float = DEFAULT_TARGET_FIRST_DECK_RATE,
) -> dict[str, Any]:
    safe_min_signups = max(1, int(min_signups))
    safe_target_bind_rate = _normalize_rate(target_bind_rate, default=DEFAULT_TARGET_BIND_RATE)
    safe_target_first_journal_rate = _normalize_rate(
        target_first_journal_rate,
        default=DEFAULT_TARGET_FIRST_JOURNAL_RATE,
    )
    safe_target_first_deck_rate = _normalize_rate(
        target_first_deck_rate,
        default=DEFAULT_TARGET_FIRST_DECK_RATE,
    )

    status_value = str(snapshot.get("status") or "").strip().lower()
    if status_value == "disabled":
        return {
            "status": "insufficient_data",
            "reasons": ["growth_activation_dashboard_disabled"],
            "evaluated": {
                "min_signups": safe_min_signups,
                "target_bind_rate": safe_target_bind_rate,
                "target_first_journal_rate": safe_target_first_journal_rate,
                "target_first_deck_rate": safe_target_first_deck_rate,
            },
        }
    if status_value != "ok":
        return {
            "status": "insufficient_data",
            "reasons": ["growth_activation_snapshot_unavailable"],
            "evaluated": {
                "min_signups": safe_min_signups,
                "target_bind_rate": safe_target_bind_rate,
                "target_first_journal_rate": safe_target_first_journal_rate,
                "target_first_deck_rate": safe_target_first_deck_rate,
            },
        }

    counts = snapshot.get("counts")
    metrics = snapshot.get("metrics")
    if not isinstance(counts, dict) or not isinstance(metrics, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["growth_activation_snapshot_shape_invalid"],
            "evaluated": {
                "min_signups": safe_min_signups,
                "target_bind_rate": safe_target_bind_rate,
                "target_first_journal_rate": safe_target_first_journal_rate,
                "target_first_deck_rate": safe_target_first_deck_rate,
            },
        }

    signup_total = _safe_int(counts.get("signup_completed_users"))
    partner_bound_total = _safe_int(counts.get("partner_bound_users"))
    first_journal_total = _safe_int(counts.get("first_journal_users"))
    first_deck_total = _safe_int(counts.get("first_deck_users"))

    bind_rate = _safe_float(metrics.get("bind_rate"))
    first_journal_rate = _safe_float(metrics.get("first_journal_rate"))
    first_deck_rate = _safe_float(metrics.get("first_deck_rate"))

    if signup_total < safe_min_signups:
        return {
            "status": "insufficient_data",
            "reasons": [],
            "evaluated": {
                "min_signups": safe_min_signups,
                "target_bind_rate": safe_target_bind_rate,
                "target_first_journal_rate": safe_target_first_journal_rate,
                "target_first_deck_rate": safe_target_first_deck_rate,
            },
            "meta": {
                "signup_completed_users": signup_total,
                "partner_bound_users": partner_bound_total,
                "first_journal_users": first_journal_total,
                "first_deck_users": first_deck_total,
            },
        }

    reasons: list[str] = []
    if bind_rate is None:
        reasons.append("bind_rate_missing")
    elif bind_rate < safe_target_bind_rate:
        reasons.append("bind_rate_below_target")

    if first_journal_rate is None:
        reasons.append("first_journal_rate_missing")
    elif first_journal_rate < safe_target_first_journal_rate:
        reasons.append("first_journal_rate_below_target")

    if first_deck_rate is None:
        reasons.append("first_deck_rate_missing")
    elif first_deck_rate < safe_target_first_deck_rate:
        reasons.append("first_deck_rate_below_target")

    return {
        "status": "pass" if not reasons else "degraded",
        "reasons": reasons,
        "evaluated": {
            "min_signups": safe_min_signups,
            "target_bind_rate": safe_target_bind_rate,
            "target_first_journal_rate": safe_target_first_journal_rate,
            "target_first_deck_rate": safe_target_first_deck_rate,
        },
        "meta": {
            "signup_completed_users": signup_total,
            "partner_bound_users": partner_bound_total,
            "first_journal_users": first_journal_total,
            "first_deck_users": first_deck_total,
            "bind_rate": bind_rate,
            "first_journal_rate": first_journal_rate,
            "first_deck_rate": first_deck_rate,
        },
    }
