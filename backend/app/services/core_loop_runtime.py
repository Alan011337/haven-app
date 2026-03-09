from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.events_log import EventsLog

DEFAULT_WINDOW_DAYS = 1
DEFAULT_MIN_ACTIVE_USERS = 10
DEFAULT_TARGET_DAILY_LOOP_COMPLETION_RATE = 0.35
DEFAULT_TARGET_DUAL_REVEAL_RATE = 0.2

CORE_LOOP_DEFINITION_VERSION = "1.0.0"

CORE_LOOP_REQUIRED_EVENTS: tuple[str, ...] = (
    "daily_sync_submitted",
    "daily_card_revealed",
    "card_answer_submitted",
    "appreciation_sent",
)
CORE_LOOP_COMPLETION_EVENT = "daily_loop_completed"
CORE_LOOP_TRACKED_EVENTS: tuple[str, ...] = CORE_LOOP_REQUIRED_EVENTS + (
    CORE_LOOP_COMPLETION_EVENT,
)


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


def _normalize_pair_key(user_id: str, partner_user_id: str) -> str:
    lower = user_id.strip().lower()
    upper = partner_user_id.strip().lower()
    if lower <= upper:
        return f"{lower}:{upper}"
    return f"{upper}:{lower}"


def _pair_fingerprint(pair_key: str) -> str:
    return hashlib.sha256(pair_key.encode("utf-8")).hexdigest()[:12]


def build_core_loop_snapshot(
    *,
    session: Session,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    safe_window_days = max(1, int(window_days))
    now = utcnow()
    window_started_at = now - timedelta(days=safe_window_days)

    rows = session.exec(
        select(
            EventsLog.user_id,
            EventsLog.partner_user_id,
            EventsLog.event_name,
        ).where(
            EventsLog.ts >= window_started_at,
            EventsLog.event_name.in_(CORE_LOOP_TRACKED_EVENTS),
        )
    ).all()

    events_by_name = {event_name: 0 for event_name in CORE_LOOP_TRACKED_EVENTS}
    ignored_rows = 0
    active_users: set[str] = set()
    completed_users: set[str] = set()
    user_steps: dict[str, set[str]] = {}
    reveal_pair_participants: dict[str, set[str]] = {}

    for row in rows:
        if isinstance(row, (tuple, list)):
            row_values = list(row)
        else:
            try:
                row_values = [row[0], row[1], row[2]]  # type: ignore[index]
            except Exception:
                ignored_rows += 1
                continue
        if len(row_values) < 3:
            ignored_rows += 1
            continue

        user_id = str(row_values[0] or "").strip().lower()
        partner_user_id = str(row_values[1] or "").strip().lower()
        event_name = str(row_values[2] or "").strip().lower()

        if not user_id:
            ignored_rows += 1
            continue
        if event_name not in events_by_name:
            ignored_rows += 1
            continue

        events_by_name[event_name] += 1
        if event_name in CORE_LOOP_REQUIRED_EVENTS:
            active_users.add(user_id)
            user_steps.setdefault(user_id, set()).add(event_name)
        if event_name == CORE_LOOP_COMPLETION_EVENT:
            completed_users.add(user_id)
        if event_name == "daily_card_revealed" and partner_user_id and partner_user_id != user_id:
            pair_key = _normalize_pair_key(user_id, partner_user_id)
            reveal_pair_participants.setdefault(pair_key, set()).add(user_id)

    derived_completed_users = {
        user_id
        for user_id, steps in user_steps.items()
        if set(CORE_LOOP_REQUIRED_EVENTS).issubset(steps)
    }

    reveal_pairs_total = len(reveal_pair_participants)
    reveal_pairs_dual_total = sum(
        1 for participants in reveal_pair_participants.values() if len(participants) >= 2
    )

    active_users_total = len(active_users)
    loop_completed_users_total = len(completed_users)
    derived_loop_completed_users_total = len(derived_completed_users)

    return {
        "status": "ok",
        "definition_version": CORE_LOOP_DEFINITION_VERSION,
        "window_days": safe_window_days,
        "window_started_at": _iso_utc(window_started_at),
        "window_ended_at": _iso_utc(now),
        "tracked_event_names": list(CORE_LOOP_TRACKED_EVENTS),
        "counts": {
            "events_total": sum(events_by_name.values()),
            "ignored_rows_total": ignored_rows,
            "active_users_total": active_users_total,
            "loop_completed_users_total": loop_completed_users_total,
            "derived_loop_completed_users_total": derived_loop_completed_users_total,
            "reveal_pairs_total": reveal_pairs_total,
            "reveal_pairs_dual_total": reveal_pairs_dual_total,
            "events_by_name": events_by_name,
        },
        "metrics": {
            "daily_loop_completion_rate": _safe_ratio(
                loop_completed_users_total,
                active_users_total,
            ),
            "derived_loop_completion_rate": _safe_ratio(
                derived_loop_completed_users_total,
                active_users_total,
            ),
            "dual_reveal_pair_rate": _safe_ratio(
                reveal_pairs_dual_total,
                reveal_pairs_total,
            ),
        },
        "targets": {
            "daily_loop_completion_rate": DEFAULT_TARGET_DAILY_LOOP_COMPLETION_RATE,
            "dual_reveal_pair_rate": DEFAULT_TARGET_DUAL_REVEAL_RATE,
        },
        "samples": {
            "dual_reveal_pair_fingerprints": sorted(
                _pair_fingerprint(pair_key)
                for pair_key, participants in reveal_pair_participants.items()
                if len(participants) >= 2
            )[:10],
            "reveal_pair_samples": min(10, reveal_pairs_total),
        },
    }


def evaluate_core_loop_snapshot(
    snapshot: dict[str, Any],
    *,
    min_active_users: int = DEFAULT_MIN_ACTIVE_USERS,
    target_daily_loop_completion_rate: float = DEFAULT_TARGET_DAILY_LOOP_COMPLETION_RATE,
    target_dual_reveal_pair_rate: float = DEFAULT_TARGET_DUAL_REVEAL_RATE,
) -> dict[str, Any]:
    safe_min_active_users = max(1, int(min_active_users))
    safe_target_completion = _normalize_rate(
        target_daily_loop_completion_rate,
        default=DEFAULT_TARGET_DAILY_LOOP_COMPLETION_RATE,
    )
    safe_target_dual_reveal = _normalize_rate(
        target_dual_reveal_pair_rate,
        default=DEFAULT_TARGET_DUAL_REVEAL_RATE,
    )

    status_value = str(snapshot.get("status") or "").strip().lower()
    if status_value != "ok":
        return {
            "status": "insufficient_data",
            "reasons": ["core_loop_snapshot_unavailable"],
            "evaluated": {
                "min_active_users": safe_min_active_users,
                "target_daily_loop_completion_rate": safe_target_completion,
                "target_dual_reveal_pair_rate": safe_target_dual_reveal,
            },
        }

    counts = snapshot.get("counts")
    metrics = snapshot.get("metrics")
    if not isinstance(counts, dict) or not isinstance(metrics, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["core_loop_snapshot_shape_invalid"],
            "evaluated": {
                "min_active_users": safe_min_active_users,
                "target_daily_loop_completion_rate": safe_target_completion,
                "target_dual_reveal_pair_rate": safe_target_dual_reveal,
            },
        }

    active_users_total = _safe_int(counts.get("active_users_total"))
    loop_completed_users_total = _safe_int(counts.get("loop_completed_users_total"))
    reveal_pairs_total = _safe_int(counts.get("reveal_pairs_total"))
    reveal_pairs_dual_total = _safe_int(counts.get("reveal_pairs_dual_total"))

    completion_rate = _safe_float(metrics.get("daily_loop_completion_rate"))
    dual_reveal_rate = _safe_float(metrics.get("dual_reveal_pair_rate"))

    if active_users_total < safe_min_active_users:
        return {
            "status": "insufficient_data",
            "reasons": [],
            "evaluated": {
                "min_active_users": safe_min_active_users,
                "target_daily_loop_completion_rate": safe_target_completion,
                "target_dual_reveal_pair_rate": safe_target_dual_reveal,
            },
            "meta": {
                "active_users_total": active_users_total,
                "loop_completed_users_total": loop_completed_users_total,
                "reveal_pairs_total": reveal_pairs_total,
                "reveal_pairs_dual_total": reveal_pairs_dual_total,
                "daily_loop_completion_rate": completion_rate,
                "dual_reveal_pair_rate": dual_reveal_rate,
            },
        }

    reasons: list[str] = []
    if completion_rate is None:
        reasons.append("daily_loop_completion_rate_missing")
    elif completion_rate < safe_target_completion:
        reasons.append("daily_loop_completion_rate_below_target")

    if dual_reveal_rate is None:
        reasons.append("dual_reveal_pair_rate_missing")
    elif dual_reveal_rate < safe_target_dual_reveal:
        reasons.append("dual_reveal_pair_rate_below_target")

    return {
        "status": "pass" if not reasons else "degraded",
        "reasons": reasons,
        "evaluated": {
            "min_active_users": safe_min_active_users,
            "target_daily_loop_completion_rate": safe_target_completion,
            "target_dual_reveal_pair_rate": safe_target_dual_reveal,
        },
        "meta": {
            "active_users_total": active_users_total,
            "loop_completed_users_total": loop_completed_users_total,
            "reveal_pairs_total": reveal_pairs_total,
            "reveal_pairs_dual_total": reveal_pairs_dual_total,
            "daily_loop_completion_rate": completion_rate,
            "dual_reveal_pair_rate": dual_reveal_rate,
        },
    }
