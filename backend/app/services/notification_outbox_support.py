from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.notification_outbox import NotificationOutboxStatus


def normalize_status_counts(rows: list[tuple[object, int | None]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status_value, raw_count in rows:
        normalized_status = (
            status_value.value
            if isinstance(status_value, NotificationOutboxStatus)
            else str(status_value or "UNKNOWN")
        )
        counts[normalized_status.upper()] = int(raw_count or 0)
    return counts


def compute_dead_letter_rate_from_counts(counts: dict[str, int]) -> float:
    dead = int(counts.get(NotificationOutboxStatus.DEAD.value, 0))
    sent = int(counts.get(NotificationOutboxStatus.SENT.value, 0))
    retry = int(counts.get(NotificationOutboxStatus.RETRY.value, 0))
    pending = int(counts.get(NotificationOutboxStatus.PENDING.value, 0))
    denominator = dead + sent + retry + pending
    if denominator <= 0:
        return 0.0
    return round(dead / denominator, 6)


def compute_retry_age_p95_seconds(
    *,
    created_at_rows: list[datetime | None],
    now_utc: datetime,
) -> int:
    if not created_at_rows:
        return 0
    ages = sorted(
        max(0, int((now_utc - created_at).total_seconds()))
        for created_at in created_at_rows
        if created_at is not None
    )
    if not ages:
        return 0
    index = max(0, min(len(ages) - 1, int(round(0.95 * (len(ages) - 1)))))
    return int(ages[index])


def build_backpressure_summary(*, enabled: bool) -> dict[str, int | str | bool]:
    return {
        "enabled": bool(enabled),
        "throttle": False,
        "reason": "none",
        "depth": -1,
        "oldest_pending_age_seconds": -1,
    }


def is_outbox_backpressure_exempt(
    *,
    event_type: str | None,
    action_type: str | None,
    exempt_event_types: tuple[str, ...] | list[str],
    exempt_action_types: tuple[str, ...] | list[str],
) -> bool:
    normalized_event = str(event_type or "").strip().lower()
    normalized_action = str(action_type or "").strip().lower()
    if normalized_event and normalized_event in set(exempt_event_types):
        return True
    if normalized_action and normalized_action in set(exempt_action_types):
        return True
    return False


def evaluate_backpressure_summary(
    *,
    enabled: bool,
    event_type: str | None,
    action_type: str | None,
    exempt_event_types: tuple[str, ...] | list[str],
    exempt_action_types: tuple[str, ...] | list[str],
    depth: int,
    oldest_pending_age_seconds: int,
    depth_threshold: int,
    oldest_pending_age_seconds_threshold: int,
) -> dict[str, int | str | bool]:
    summary = build_backpressure_summary(enabled=enabled)
    if not enabled:
        return summary
    if is_outbox_backpressure_exempt(
        event_type=event_type,
        action_type=action_type,
        exempt_event_types=exempt_event_types,
        exempt_action_types=exempt_action_types,
    ):
        summary["reason"] = "exempt"
        return summary

    summary["depth"] = int(depth)
    summary["oldest_pending_age_seconds"] = int(oldest_pending_age_seconds)

    if depth < 0 or oldest_pending_age_seconds < 0:
        summary["reason"] = "probe_unavailable"
        return summary

    if int(depth) >= int(depth_threshold):
        summary["throttle"] = True
        summary["reason"] = "depth_threshold"
        return summary

    if int(oldest_pending_age_seconds) >= int(oldest_pending_age_seconds_threshold):
        summary["throttle"] = True
        summary["reason"] = "oldest_pending_age_threshold"
        return summary

    return summary


def resolve_depth_adaptive_claim_limit(
    *,
    base_limit: int,
    backlog_depth: int,
    adaptive_max_limit: int,
) -> int:
    safe_base_limit = max(1, int(base_limit))
    safe_backlog_depth = max(0, int(backlog_depth))
    safe_adaptive_max = max(safe_base_limit, int(adaptive_max_limit))
    if safe_backlog_depth < safe_base_limit * 3:
        return safe_base_limit
    if safe_backlog_depth >= safe_base_limit * 20:
        return min(safe_base_limit * 8, safe_adaptive_max)
    if safe_backlog_depth >= safe_base_limit * 10:
        return min(safe_base_limit * 4, safe_adaptive_max)
    if safe_backlog_depth >= safe_base_limit * 5:
        return min(safe_base_limit * 3, safe_adaptive_max)
    return min(safe_base_limit * 2, safe_adaptive_max)


def resolve_age_adaptive_claim_limit(
    *,
    base_limit: int,
    oldest_pending_age_seconds: int,
    adaptive_max_limit: int,
    age_scale_threshold_seconds: int,
    age_critical_seconds: int,
) -> int:
    safe_base_limit = max(1, int(base_limit))
    safe_oldest_age = max(0, int(oldest_pending_age_seconds))
    safe_adaptive_max = max(safe_base_limit, int(adaptive_max_limit))
    safe_threshold = max(1, int(age_scale_threshold_seconds))
    safe_critical = max(safe_threshold, int(age_critical_seconds))

    if safe_oldest_age < safe_threshold:
        return safe_base_limit
    if safe_oldest_age >= safe_critical:
        return min(safe_base_limit * 8, safe_adaptive_max)
    if safe_oldest_age >= safe_threshold * 2:
        return min(safe_base_limit * 4, safe_adaptive_max)
    return min(safe_base_limit * 2, safe_adaptive_max)


def resolve_adaptive_claim_limit(
    *,
    base_limit: int,
    backlog_depth: int,
    oldest_pending_age_seconds: int,
    adaptive_enabled: bool,
    adaptive_max_limit: int,
    age_scale_threshold_seconds: int,
    age_critical_seconds: int,
) -> int:
    safe_base_limit = max(1, int(base_limit))
    if not adaptive_enabled:
        return safe_base_limit

    depth_limit = resolve_depth_adaptive_claim_limit(
        base_limit=safe_base_limit,
        backlog_depth=backlog_depth,
        adaptive_max_limit=adaptive_max_limit,
    )
    age_limit = resolve_age_adaptive_claim_limit(
        base_limit=safe_base_limit,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        adaptive_max_limit=adaptive_max_limit,
        age_scale_threshold_seconds=age_scale_threshold_seconds,
        age_critical_seconds=age_critical_seconds,
    )
    return max(depth_limit, age_limit)


def build_process_summary(
    *,
    base_limit: int,
    selected_limit: int,
    backlog_depth: int,
    oldest_pending_age_seconds: int,
    adaptive_enabled: bool,
) -> dict[str, int]:
    return {
        "selected": 0,
        "sent": 0,
        "retried": 0,
        "dead": 0,
        "errors": 0,
        "reclaimed": 0,
        "base_limit": int(base_limit),
        "selected_limit": int(selected_limit),
        "backlog_depth": max(-1, int(backlog_depth)),
        "oldest_pending_age_seconds": max(-1, int(oldest_pending_age_seconds)),
        "adaptive_enabled": 1 if adaptive_enabled else 0,
    }


def build_cleanup_summary() -> dict[str, int]:
    return {
        "purged_sent": 0,
        "purged_dead": 0,
        "errors": 0,
    }


def build_replay_summary() -> dict[str, int]:
    return {
        "selected": 0,
        "replayed": 0,
        "errors": 0,
    }


def build_auto_replay_summary(*, enabled: bool) -> dict[str, int | float]:
    return {
        "enabled": 1 if enabled else 0,
        "triggered": 0,
        "dead_rows": 0,
        "dead_letter_rate": 0.0,
        "replayed": 0,
        "errors": 0,
    }


def build_backpressure_metric_flags(summary: dict[str, Any]) -> dict[str, bool]:
    reason = str(summary.get("reason", "none"))
    return {
        "is_exempt": reason == "exempt",
        "probe_unavailable": reason == "probe_unavailable",
        "depth_triggered": bool(summary.get("throttle")) and reason == "depth_threshold",
        "oldest_triggered": bool(summary.get("throttle"))
        and reason == "oldest_pending_age_threshold",
    }
