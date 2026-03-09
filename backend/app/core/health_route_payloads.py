"""Pure helpers for building health route runtime context and response payloads."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def collect_health_runtime_context(
    *,
    uptime_seconds: int,
    probe_database: Callable[[], dict],
    probe_redis_if_configured: Callable[[], dict],
    provider_checks: Callable[[], dict],
    get_notification_outbox_health_snapshot: Callable[[], dict],
    get_notification_outbox_depth: Callable[..., int],
    get_notification_outbox_oldest_pending_age_seconds: Callable[..., int],
    get_notification_outbox_retry_age_p95_seconds: Callable[..., int],
    get_notification_outbox_dead_letter_rate: Callable[..., float],
    get_notification_outbox_stale_processing_count: Callable[..., int],
    get_notification_outbox_dispatch_lock_heartbeat_age_seconds: Callable[[], int],
    outbox_snapshot_value: Callable[[dict | None, str, Any], Any],
    build_runtime_payloads: Callable[[], dict[str, dict]],
    compute_dynamic_content_fallback_ratio: Callable[[dict], tuple[float, int]],
    get_notification_queue_depth: Callable[[], int],
    get_journal_queue_depth: Callable[[], int],
    get_db_pool_runtime_snapshot: Callable[[], dict],
    get_db_query_runtime_snapshot: Callable[[], dict],
) -> dict[str, Any]:
    outbox_snapshot = get_notification_outbox_health_snapshot()
    runtime_payloads = build_runtime_payloads()
    dynamic_content_runtime_payload = runtime_payloads.get("dynamic_content_runtime", {})
    ai_router_runtime_payload = runtime_payloads.get("ai_router_runtime", {})
    dynamic_fallback_ratio, dynamic_fallback_attempts = compute_dynamic_content_fallback_ratio(
        dynamic_content_runtime_payload
    )
    return {
        "db_probe": probe_database(),
        "redis_probe": probe_redis_if_configured(),
        "providers": provider_checks(),
        "outbox_depth": get_notification_outbox_depth(snapshot=outbox_snapshot),
        "outbox_oldest_pending_age_seconds": get_notification_outbox_oldest_pending_age_seconds(
            snapshot=outbox_snapshot
        ),
        "outbox_retry_age_p95_seconds": get_notification_outbox_retry_age_p95_seconds(
            snapshot=outbox_snapshot
        ),
        "outbox_dead_letter_rate": get_notification_outbox_dead_letter_rate(
            snapshot=outbox_snapshot
        ),
        "outbox_stale_processing_count": get_notification_outbox_stale_processing_count(
            snapshot=outbox_snapshot
        ),
        "outbox_dispatch_lock_heartbeat_age_seconds": int(
            outbox_snapshot_value(
                outbox_snapshot,
                "dispatch_lock_heartbeat_age_seconds",
                get_notification_outbox_dispatch_lock_heartbeat_age_seconds(),
            )
        ),
        "runtime_payloads": runtime_payloads,
        "dynamic_fallback_ratio": dynamic_fallback_ratio,
        "dynamic_fallback_attempts": dynamic_fallback_attempts,
        "ai_router_runtime_payload": ai_router_runtime_payload,
        "notification_queue_depth": get_notification_queue_depth(),
        "journal_queue_depth": get_journal_queue_depth(),
        "db_pool_runtime": get_db_pool_runtime_snapshot(),
        "db_query_runtime": get_db_query_runtime_snapshot(),
        "uptime_seconds": max(0, int(uptime_seconds)),
    }


def apply_sli_evaluation(
    *,
    sli: dict,
    evaluation_key: str,
    evaluation_value: dict,
) -> tuple[dict, dict]:
    next_sli = dict(sli) if isinstance(sli, dict) else {}
    raw_evaluation = next_sli.get("evaluation")
    evaluation_map = dict(raw_evaluation) if isinstance(raw_evaluation, dict) else {}
    evaluation_map[evaluation_key] = evaluation_value
    next_sli["evaluation"] = evaluation_map
    return next_sli, evaluation_map


def build_sli_full_payload(
    *,
    sli: dict,
    runtime_payloads: dict[str, dict],
    build_rate_limit_sli_payload: Callable[[], dict],
    sli_targets: dict,
    merge_runtime_snapshot_if_needed: Callable[[dict], dict],
    persist_runtime_metrics_snapshot: Callable[[dict], None],
) -> dict:
    sli_full = merge_runtime_snapshot_if_needed(
        {
            **sli,
            "write_rate_limit": build_rate_limit_sli_payload(),
            **runtime_payloads,
            "targets": sli_targets,
        }
    )
    persist_runtime_metrics_snapshot({"sli": sli_full})
    return sli_full


def build_runtime_checks_from_context(
    *,
    runtime_context: dict[str, Any],
    build_runtime_checks_payload: Callable[..., dict],
) -> dict:
    return build_runtime_checks_payload(
        database_probe=runtime_context["db_probe"],
        redis_probe=runtime_context["redis_probe"],
        providers=runtime_context["providers"],
        notification_queue_depth=runtime_context["notification_queue_depth"],
        notification_outbox_depth=runtime_context["outbox_depth"],
        notification_outbox_oldest_pending_age_seconds=runtime_context[
            "outbox_oldest_pending_age_seconds"
        ],
        notification_outbox_retry_age_p95_seconds=runtime_context[
            "outbox_retry_age_p95_seconds"
        ],
        notification_outbox_dead_letter_rate=runtime_context["outbox_dead_letter_rate"],
        notification_outbox_stale_processing_count=runtime_context[
            "outbox_stale_processing_count"
        ],
        notification_outbox_dispatch_lock_heartbeat_age_seconds=runtime_context[
            "outbox_dispatch_lock_heartbeat_age_seconds"
        ],
        dynamic_content_fallback_ratio=runtime_context["dynamic_fallback_ratio"],
        dynamic_content_fallback_attempts=runtime_context["dynamic_fallback_attempts"],
        journal_queue_depth=runtime_context["journal_queue_depth"],
        db_pool_runtime=runtime_context["db_pool_runtime"],
        db_query_runtime=runtime_context["db_query_runtime"],
    )


def build_health_payload(
    *,
    status_value: str,
    app_title: str,
    app_version: str,
    environment: str,
    timestamp: str,
    uptime_seconds: int,
    checks: dict,
    sli_full: dict,
    degraded_reasons: list[str] | None = None,
    notes: dict | None = None,
) -> dict:
    payload = {
        "status": status_value,
        "service": app_title,
        "version": app_version,
        "environment": environment,
        "timestamp": timestamp,
        "uptime_seconds": uptime_seconds,
        "checks": checks,
        "sli": sli_full,
    }
    if degraded_reasons:
        payload["degraded_reasons"] = degraded_reasons
    if notes is not None:
        payload["notes"] = notes
    return payload
