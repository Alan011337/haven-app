from __future__ import annotations


def collect_degraded_reasons(
    *,
    db_probe: dict,
    redis_probe: dict,
    evaluation_map: dict,
    abuse_evaluation: dict | None,
    outbox_depth: int,
    outbox_oldest_pending_age_seconds: int,
    outbox_retry_age_p95_seconds: int,
    outbox_stale_processing_count: int,
    outbox_dead_letter_rate: float,
    outbox_dispatch_lock_heartbeat_age_seconds: int,
    outbox_depth_threshold: int,
    outbox_oldest_pending_threshold_seconds: int,
    outbox_retry_age_p95_threshold_seconds: int,
    outbox_stale_processing_threshold: int,
    outbox_dead_letter_threshold: float,
    outbox_dispatch_lock_heartbeat_threshold_seconds: int,
    dynamic_fallback_ratio: float,
    dynamic_fallback_attempts: int,
    dynamic_fallback_ratio_threshold: float,
    dynamic_fallback_min_attempts: int,
) -> list[str]:
    degraded_reasons: list[str] = []
    if db_probe.get("status") != "ok":
        degraded_reasons.append("database_unhealthy")
    if redis_probe.get("status") == "error":
        degraded_reasons.append("redis_unhealthy")

    if evaluation_map.get("ws", {}).get("status") == "degraded":
        degraded_reasons.append("ws_sli_below_target")
    if evaluation_map.get("ws_burn_rate", {}).get("status") == "degraded":
        degraded_reasons.append("ws_burn_rate_above_threshold")
    if evaluation_map.get("push", {}).get("status") == "degraded":
        degraded_reasons.append("push_sli_below_target")
    if evaluation_map.get("cuj", {}).get("status") == "degraded":
        degraded_reasons.append("cuj_sli_below_target")
    if evaluation_map.get("tier_policy", {}).get("status") == "degraded":
        degraded_reasons.append("sre_tier_budget_exceeded")
    if evaluation_map.get("ai_router_burn_rate", {}).get("status") == "degraded":
        degraded_reasons.append("ai_router_burn_rate_above_threshold")

    if isinstance(abuse_evaluation, dict) and abuse_evaluation.get("status") == "block":
        degraded_reasons.append("abuse_economics_budget_block")

    if outbox_depth_threshold > 0 and outbox_depth >= outbox_depth_threshold:
        degraded_reasons.append("notification_outbox_depth_high")
    if (
        outbox_oldest_pending_threshold_seconds > 0
        and outbox_oldest_pending_age_seconds >= outbox_oldest_pending_threshold_seconds
    ):
        degraded_reasons.append("notification_outbox_oldest_pending_high")
    if (
        outbox_retry_age_p95_threshold_seconds > 0
        and outbox_retry_age_p95_seconds >= outbox_retry_age_p95_threshold_seconds
    ):
        degraded_reasons.append("notification_outbox_retry_age_high")
    if (
        outbox_stale_processing_threshold > 0
        and outbox_stale_processing_count >= outbox_stale_processing_threshold
    ):
        degraded_reasons.append("notification_outbox_stale_processing_high")
    if (
        outbox_dispatch_lock_heartbeat_threshold_seconds > 0
        and outbox_depth > 0
        and outbox_dispatch_lock_heartbeat_age_seconds
        >= outbox_dispatch_lock_heartbeat_threshold_seconds
    ):
        degraded_reasons.append("notification_outbox_dispatch_lock_heartbeat_stale")
    if outbox_dead_letter_rate >= outbox_dead_letter_threshold:
        degraded_reasons.append("notification_outbox_dead_letter_rate_high")

    if (
        dynamic_fallback_attempts >= dynamic_fallback_min_attempts
        and dynamic_fallback_ratio >= dynamic_fallback_ratio_threshold
    ):
        degraded_reasons.append("dynamic_content_fallback_ratio_high")

    return degraded_reasons
