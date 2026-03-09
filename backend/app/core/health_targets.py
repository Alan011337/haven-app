"""Shared SLI target contract for health endpoints."""

from __future__ import annotations

from app.core.config import settings
from app.services.cuj_sli_runtime import CUJ_TARGETS

HEALTH_SLO_NOTES = (
    "SLI includes websocket burn-rate windows and CUJ runtime metrics from tracked event snapshots."
)

SLI_TARGETS = {
    "ws_connection_accept_rate": float(settings.HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET),
    "ws_message_pass_rate": float(settings.HEALTH_WS_MESSAGE_PASS_RATE_TARGET),
    "ws_burn_rate_fast_threshold": float(settings.HEALTH_WS_BURN_RATE_FAST_THRESHOLD),
    "ws_burn_rate_slow_threshold": float(settings.HEALTH_WS_BURN_RATE_SLOW_THRESHOLD),
    "push_delivery_rate": float(settings.HEALTH_PUSH_DELIVERY_RATE_TARGET),
    "push_dispatch_latency_p95_ms": float(settings.HEALTH_PUSH_DISPATCH_P95_MS_TARGET),
    "push_dry_run_latency_p95_ms": float(settings.HEALTH_PUSH_DRY_RUN_P95_MS_TARGET),
    "push_cleanup_stale_backlog_max": int(settings.HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX),
    "notification_outbox_depth_max": int(
        getattr(settings, "HEALTH_NOTIFICATION_OUTBOX_DEPTH_DEGRADED_THRESHOLD", 500)
    ),
    "notification_outbox_oldest_pending_age_seconds_max": int(
        getattr(settings, "HEALTH_NOTIFICATION_OUTBOX_OLDEST_PENDING_DEGRADED_SECONDS", 1800)
    ),
    "notification_outbox_retry_age_p95_seconds_max": int(
        getattr(settings, "HEALTH_NOTIFICATION_OUTBOX_RETRY_AGE_P95_DEGRADED_SECONDS", 2400)
    ),
    "notification_outbox_stale_processing_max": int(
        getattr(settings, "HEALTH_NOTIFICATION_OUTBOX_STALE_PROCESSING_DEGRADED_THRESHOLD", 10)
    ),
    "notification_outbox_dispatch_lock_heartbeat_age_seconds_max": int(
        getattr(settings, "HEALTH_NOTIFICATION_OUTBOX_DISPATCH_LOCK_HEARTBEAT_DEGRADED_SECONDS", 180)
    ),
    "notification_outbox_dead_letter_rate_max": float(
        getattr(settings, "HEALTH_NOTIFICATION_OUTBOX_DEAD_LETTER_RATE_DEGRADED_THRESHOLD", 0.4)
    ),
    "dynamic_content_fallback_ratio_max": float(
        getattr(settings, "HEALTH_DYNAMIC_CONTENT_FALLBACK_RATIO_DEGRADED_THRESHOLD", 0.65)
    ),
    "dynamic_content_fallback_min_attempts": int(
        getattr(settings, "HEALTH_DYNAMIC_CONTENT_FALLBACK_MIN_ATTEMPTS", 20)
    ),
    "ai_router_burn_rate_fast_window_seconds": int(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_FAST_WINDOW_SECONDS", 300)
    ),
    "ai_router_burn_rate_slow_window_seconds": int(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_SLOW_WINDOW_SECONDS", 3600)
    ),
    "ai_router_burn_rate_fast_threshold": float(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_FAST_THRESHOLD", 14.0)
    ),
    "ai_router_burn_rate_slow_threshold": float(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_SLOW_THRESHOLD", 4.0)
    ),
    "ai_router_burn_rate_fast_min_attempts": int(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_FAST", 20)
    ),
    "ai_router_burn_rate_slow_min_attempts": int(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_SLOW", 100)
    ),
    "ai_router_burn_rate_error_budget_fraction": float(
        getattr(settings, "HEALTH_AI_ROUTER_BURN_RATE_ERROR_BUDGET_FRACTION", 0.01)
    ),
    "cuj": dict(CUJ_TARGETS),
}
