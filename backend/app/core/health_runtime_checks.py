from __future__ import annotations

from typing import Any


def compute_dynamic_content_fallback_ratio(payload: dict) -> tuple[float, int]:
    counters = payload.get("counters", {}) if isinstance(payload, dict) else {}
    if not isinstance(counters, dict):
        return 0.0, 0
    attempts = int(counters.get("dynamic_content_generation_attempt_total", 0) or 0)
    if attempts <= 0:
        return 0.0, 0
    fallback_total = 0
    for key, value in counters.items():
        metric_key = str(key)
        if (
            metric_key.startswith("dynamic_content_fallback_")
            and metric_key != "dynamic_content_fallback_degraded_mode_total"
        ):
            fallback_total += max(0, int(value or 0))
    ratio = min(1.0, max(0.0, float(fallback_total) / float(attempts)))
    return round(ratio, 6), attempts


def build_runtime_checks_payload(
    *,
    database_probe: dict[str, Any],
    redis_probe: dict[str, Any],
    providers: dict[str, Any],
    notification_queue_depth: int,
    notification_outbox_depth: int,
    notification_outbox_oldest_pending_age_seconds: int,
    notification_outbox_retry_age_p95_seconds: int,
    notification_outbox_dead_letter_rate: float,
    notification_outbox_stale_processing_count: int,
    notification_outbox_dispatch_lock_heartbeat_age_seconds: int,
    dynamic_content_fallback_ratio: float,
    dynamic_content_fallback_attempts: int,
    journal_queue_depth: int,
    db_pool_runtime: dict[str, Any] | None = None,
    db_query_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "database": database_probe,
        "redis": redis_probe,
        "providers": providers,
        "notification_queue_depth": notification_queue_depth,
        "notification_outbox_depth": notification_outbox_depth,
        "notification_outbox_oldest_pending_age_seconds": notification_outbox_oldest_pending_age_seconds,
        "notification_outbox_retry_age_p95_seconds": notification_outbox_retry_age_p95_seconds,
        "notification_outbox_dead_letter_rate": notification_outbox_dead_letter_rate,
        "notification_outbox_stale_processing_count": notification_outbox_stale_processing_count,
        "notification_outbox_dispatch_lock_heartbeat_age_seconds": notification_outbox_dispatch_lock_heartbeat_age_seconds,
        "dynamic_content_fallback_ratio": dynamic_content_fallback_ratio,
        "dynamic_content_fallback_attempts": dynamic_content_fallback_attempts,
        "journal_queue_depth": journal_queue_depth,
        "db_pool_runtime": db_pool_runtime or {},
        "db_query_runtime": db_query_runtime or {},
    }
