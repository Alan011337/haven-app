# backend/app/core/health_routes.py
"""Health check and SLO routes; use get_health_router() to mount on the app."""
from __future__ import annotations

import logging
import time
from threading import Lock
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.core.health_cache_utils import (
    is_metrics_request_authorized as _is_metrics_request_authorized_from_module,
    merge_runtime_snapshot_if_needed as _merge_runtime_snapshot_if_needed_from_module,
    should_bypass_health_cache as _should_bypass_health_cache_from_module,
)
from app.core.health_runtime_payloads import (
    build_ai_router_runtime_payload as _build_ai_router_runtime_payload_from_module,
    build_dynamic_content_runtime_payload as _build_dynamic_content_runtime_payload_from_module,
    build_events_runtime_payload as _build_events_runtime_payload_from_module,
    build_http_observability_payload as _build_http_observability_payload_from_module,
    build_notification_runtime_payload as _build_notification_runtime_payload_from_module,
    build_posthog_runtime_payload as _build_posthog_runtime_payload_from_module,
    build_rate_limit_sli_payload as _build_rate_limit_sli_payload_from_module,
    build_timeline_runtime_payload as _build_timeline_runtime_payload_from_module,
)
from app.core.health_metrics_helpers import (
    append_counter_metrics as _append_counter_metrics,
    safe_queue_depth as _safe_queue_depth,
)
from app.core.health_runtime_checks import (
    build_runtime_checks_payload as _build_runtime_checks_payload,
    compute_dynamic_content_fallback_ratio as _compute_dynamic_content_fallback_ratio,
)
from app.core.health_degradation import collect_degraded_reasons
from app.core.health_targets import HEALTH_SLO_NOTES, SLI_TARGETS
from app.core.health_providers import (
    provider_checks as _provider_checks_from_module,
)
from app.core.health_route_payloads import (
    apply_sli_evaluation as _apply_sli_evaluation_from_module,
    build_health_payload as _build_health_payload_from_module,
    build_runtime_checks_from_context as _build_runtime_checks_from_context_from_module,
    build_sli_full_payload as _build_sli_full_payload_from_module,
    collect_health_runtime_context as _collect_health_runtime_context_from_module,
)
from app.core.health_slo_config import (
    HEALTH_AI_ROUTER_BURN_RATE_ERROR_BUDGET_FRACTION,
    HEALTH_AI_ROUTER_BURN_RATE_FAST_THRESHOLD,
    HEALTH_AI_ROUTER_BURN_RATE_FAST_WINDOW_SECONDS,
    HEALTH_AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_FAST,
    HEALTH_AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_SLOW,
    HEALTH_AI_ROUTER_BURN_RATE_SLOW_THRESHOLD,
    HEALTH_AI_ROUTER_BURN_RATE_SLOW_WINDOW_SECONDS,
    HEALTH_DYNAMIC_FALLBACK_MIN_ATTEMPTS,
    HEALTH_DYNAMIC_FALLBACK_RATIO_DEGRADED_THRESHOLD,
    HEALTH_OUTBOX_DEAD_LETTER_DEGRADED_THRESHOLD,
    HEALTH_OUTBOX_DEPTH_DEGRADED_THRESHOLD,
    HEALTH_OUTBOX_DISPATCH_LOCK_HEARTBEAT_DEGRADED_SECONDS,
    HEALTH_OUTBOX_OLDEST_PENDING_DEGRADED_SECONDS,
    HEALTH_OUTBOX_RETRY_AGE_P95_DEGRADED_SECONDS,
    HEALTH_OUTBOX_STALE_PROCESSING_DEGRADED_THRESHOLD,
    HEALTH_PUSH_DELIVERY_RATE_TARGET,
    HEALTH_PUSH_DISPATCH_P95_MS_TARGET,
    HEALTH_PUSH_DRY_RUN_P95_MS_TARGET,
    HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS,
    HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES,
    HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX,
    HEALTH_READINESS_CACHE_TTL_SECONDS,
    HEALTH_WS_BURN_RATE_WINDOWS_SECONDS,
    WS_SLI_CONFIG,
)
from app.core.health_ws_sli import (
    build_ws_burn_rate_payload as _build_ws_burn_rate_payload_from_module,
    build_ws_sli_payload as _build_ws_sli_payload_from_module,
    evaluate_ws_burn_rate as _evaluate_ws_burn_rate_from_module,
    evaluate_ws_sli as _evaluate_ws_sli_from_module,
)
from app.core.socket_manager import manager
from app.db.session import engine
from app.db.session import get_db_query_runtime_snapshot
from app.db.session import get_db_pool_runtime_snapshot
from app.services.cuj_sli_runtime import build_cuj_sli_snapshot, evaluate_cuj_sli_snapshot
from app.services.degradation_runtime import evaluate_degradation_status
from app.services.abuse_economics_runtime import build_abuse_economics_runtime_snapshot
from app.services.http_observability import http_observability
from app.services.posthog_events import get_posthog_runtime_snapshot
from app.services.notification import get_notification_queue_depth
from app.services.notification_outbox import get_notification_outbox_dispatch_lock_heartbeat_age_seconds
from app.services.notification_outbox_health import get_notification_outbox_health_snapshot
from app.services.notification_runtime_metrics import notification_runtime_metrics
from app.services.dynamic_content_runtime_metrics import dynamic_content_runtime_metrics
from app.services.events_runtime_metrics import events_runtime_metrics
from app.services.timeline_runtime_metrics import timeline_runtime_metrics
from app.queue.journal_tasks import get_journal_queue_depth
from app.services.ai_router import ai_router_runtime_metrics
from app.services.push_sli_runtime import build_push_sli_snapshot, evaluate_push_sli_snapshot
from app.services.runtime_metrics_snapshot import (
    load_runtime_metrics_snapshot,
    persist_runtime_metrics_snapshot,
)
from app.services.ws_runtime_metrics import ws_runtime_metrics
from app.services.sre_tier_policy import evaluate_tier_policy

logger = logging.getLogger(__name__)

_HEALTH_CACHE_LOCK = Lock()
_HEALTH_CACHE_STATE: dict[str, object] = {
    "expires_at_monotonic": 0.0,
    "payload": None,
}



def _outbox_snapshot_value(snapshot: dict | None, key: str, default):
    if isinstance(snapshot, dict):
        return snapshot.get(key, default)
    return default


def get_notification_outbox_depth(*, snapshot: dict | None = None) -> int:
    return int(_outbox_snapshot_value(snapshot, "depth", -1))


def get_notification_outbox_oldest_pending_age_seconds(*, snapshot: dict | None = None) -> int:
    return int(_outbox_snapshot_value(snapshot, "oldest_pending_age_seconds", -1))


def get_notification_outbox_retry_age_p95_seconds(*, snapshot: dict | None = None) -> int:
    return int(_outbox_snapshot_value(snapshot, "retry_age_p95_seconds", -1))


def get_notification_outbox_dead_letter_rate(*, snapshot: dict | None = None) -> float:
    return float(_outbox_snapshot_value(snapshot, "dead_letter_rate", -1.0))


def get_notification_outbox_stale_processing_count(*, snapshot: dict | None = None) -> int:
    return int(_outbox_snapshot_value(snapshot, "stale_processing_count", -1))


def get_notification_outbox_status_counts(*, snapshot: dict | None = None) -> dict[str, int]:
    raw = _outbox_snapshot_value(snapshot, "status_counts", {})
    return raw if isinstance(raw, dict) else {}


def _is_metrics_request_authorized(request: Request) -> bool:
    return _is_metrics_request_authorized_from_module(
        metrics_auth_token=getattr(settings, "METRICS_AUTH_TOKEN", None),
        auth_header=request.headers.get("authorization"),
        metrics_header=request.headers.get("x-metrics-token"),
    )


def _should_bypass_health_cache() -> bool:
    return _should_bypass_health_cache_from_module()


def _merge_runtime_snapshot_if_needed(sli_payload: dict) -> dict:
    if not isinstance(sli_payload, dict):
        return sli_payload
    snapshot = load_runtime_metrics_snapshot()
    return _merge_runtime_snapshot_if_needed_from_module(
        sli_payload=sli_payload,
        snapshot=snapshot if isinstance(snapshot, dict) else None,
    )


def _build_full_sli_snapshot_cached(*, uptime_seconds: int) -> dict:
    if _should_bypass_health_cache() or HEALTH_READINESS_CACHE_TTL_SECONDS <= 0:
        return _build_full_sli_snapshot(uptime_seconds=uptime_seconds)

    now_mono = time.monotonic()
    with _HEALTH_CACHE_LOCK:
        cached_payload = _HEALTH_CACHE_STATE.get("payload")
        expires = float(_HEALTH_CACHE_STATE.get("expires_at_monotonic", 0.0) or 0.0)
        if isinstance(cached_payload, dict) and now_mono <= expires:
            return cached_payload

    computed = _build_full_sli_snapshot(uptime_seconds=uptime_seconds)
    with _HEALTH_CACHE_LOCK:
        _HEALTH_CACHE_STATE["payload"] = computed
        _HEALTH_CACHE_STATE["expires_at_monotonic"] = now_mono + HEALTH_READINESS_CACHE_TTL_SECONDS
    return computed


def _build_ws_sli_payload() -> dict:
    snapshot = ws_runtime_metrics.snapshot(active_connections=manager.total_connection_count())
    return _build_ws_sli_payload_from_module(ws_snapshot=snapshot)


def _build_ws_burn_rate_payload() -> dict:
    window_snapshots = {
        window_seconds: ws_runtime_metrics.window_snapshot(window_seconds=window_seconds)
        for window_seconds in HEALTH_WS_BURN_RATE_WINDOWS_SECONDS
    }
    return _build_ws_burn_rate_payload_from_module(
        ws_window_snapshots=window_snapshots,
        config=WS_SLI_CONFIG,
    )


def _build_rate_limit_sli_payload() -> dict:
    return _build_rate_limit_sli_payload_from_module()


def _build_abuse_economics_sli_payload(*, uptime_seconds: int) -> dict:
    try:
        rate_limit_snapshot = _build_rate_limit_sli_payload()
        ws_runtime_snapshot = ws_runtime_metrics.snapshot(
            active_connections=manager.total_connection_count()
        )
        return build_abuse_economics_runtime_snapshot(
            rate_limit_snapshot=rate_limit_snapshot,
            ws_runtime_snapshot=ws_runtime_snapshot,
            uptime_seconds=uptime_seconds,
        )
    except Exception as exc:
        logger.warning(
            "Health abuse economics snapshot unavailable: reason=%s",
            type(exc).__name__,
        )
        return {
            "status": "insufficient_data",
            "uptime_seconds": max(0, int(uptime_seconds)),
            "evaluation": {
                "status": "insufficient_data",
                "reasons": ["abuse_economics_snapshot_unavailable"],
                "signal_present": False,
            },
            "vectors": [],
            "estimated_daily_total_usd": 0.0,
            "thresholds": {},
        }


def _build_http_observability_payload() -> dict:
    return _build_http_observability_payload_from_module()


def _build_ai_router_runtime_payload() -> dict:
    return _build_ai_router_runtime_payload_from_module()


def _build_notification_runtime_payload() -> dict:
    payload = _build_notification_runtime_payload_from_module()
    if not isinstance(payload, dict):
        payload = {}
    outbox_snapshot = get_notification_outbox_health_snapshot()
    payload["outbox"] = {
        "status_counts": get_notification_outbox_status_counts(snapshot=outbox_snapshot),
        "retry_age_p95_seconds": get_notification_outbox_retry_age_p95_seconds(snapshot=outbox_snapshot),
        "dead_letter_rate": get_notification_outbox_dead_letter_rate(snapshot=outbox_snapshot),
        "stale_processing_count": get_notification_outbox_stale_processing_count(snapshot=outbox_snapshot),
    }
    return payload


def _build_dynamic_content_runtime_payload() -> dict:
    return _build_dynamic_content_runtime_payload_from_module()


def _build_events_runtime_payload() -> dict:
    return _build_events_runtime_payload_from_module()


def _build_timeline_runtime_payload() -> dict:
    return _build_timeline_runtime_payload_from_module()


def _build_posthog_runtime_payload() -> dict:
    return _build_posthog_runtime_payload_from_module()


_RUNTIME_PAYLOAD_BUILDERS: tuple[tuple[str, str], ...] = (
    ("ai_router_runtime", "_build_ai_router_runtime_payload"),
    ("notification_runtime", "_build_notification_runtime_payload"),
    ("dynamic_content_runtime", "_build_dynamic_content_runtime_payload"),
    ("events_runtime", "_build_events_runtime_payload"),
    ("timeline_runtime", "_build_timeline_runtime_payload"),
    ("http_runtime", "_build_http_observability_payload"),
    ("posthog_runtime", "_build_posthog_runtime_payload"),
)


def _build_runtime_payloads() -> dict[str, dict]:
    payloads: dict[str, dict] = {}
    for key, builder_name in _RUNTIME_PAYLOAD_BUILDERS:
        try:
            builder = globals().get(builder_name)
            if not callable(builder):
                payloads[key] = {}
                continue
            raw = builder()
            payloads[key] = raw if isinstance(raw, dict) else {}
        except Exception as exc:
            logger.warning("Health runtime payload unavailable: key=%s reason=%s", key, type(exc).__name__)
            payloads[key] = {}
    return payloads


def _build_openmetrics_payload(*, app_title: str, app_version: str) -> str:
    ws_snapshot = ws_runtime_metrics.snapshot(active_connections=manager.total_connection_count())
    ws_counters = ws_snapshot.get("counters", {}) if isinstance(ws_snapshot, dict) else {}
    if not isinstance(ws_counters, dict):
        ws_counters = {}
    notification_counters = notification_runtime_metrics.snapshot()
    dynamic_counters = dynamic_content_runtime_metrics.snapshot()
    events_counters = events_runtime_metrics.snapshot()
    timeline_counters = timeline_runtime_metrics.snapshot()
    outbox_snapshot = get_notification_outbox_health_snapshot()
    outbox_depth = get_notification_outbox_depth(snapshot=outbox_snapshot)
    outbox_oldest_age_seconds = get_notification_outbox_oldest_pending_age_seconds(snapshot=outbox_snapshot)
    outbox_retry_age_p95_seconds = get_notification_outbox_retry_age_p95_seconds(snapshot=outbox_snapshot)
    outbox_stale_processing_count = get_notification_outbox_stale_processing_count(snapshot=outbox_snapshot)
    outbox_dead_letter_rate = get_notification_outbox_dead_letter_rate(snapshot=outbox_snapshot)
    outbox_status_counts = get_notification_outbox_status_counts(snapshot=outbox_snapshot)
    db_query_runtime = get_db_query_runtime_snapshot()
    queue_depth = get_notification_queue_depth()
    journal_queue_depth = get_journal_queue_depth()
    http_snapshot = http_observability.snapshot(window_seconds=15 * 60)
    http_counters = http_snapshot.get("counts", {}) if isinstance(http_snapshot, dict) else {}
    if not isinstance(http_counters, dict):
        http_counters = {}
    ai_router_counters = ai_router_runtime_metrics.snapshot()
    if not isinstance(ai_router_counters, dict):
        ai_router_counters = {}
    posthog_counters = get_posthog_runtime_snapshot()
    if not isinstance(posthog_counters, dict):
        posthog_counters = {}

    lines = [
        "# HELP haven_service_info Static service metadata.",
        "# TYPE haven_service_info gauge",
        (
            'haven_service_info{service="%s",version="%s",environment="%s"} 1'
            % (app_title, app_version, settings.ENV)
        ),
        "# HELP haven_notification_outbox_depth Notification outbox queue depth.",
        "# TYPE haven_notification_outbox_depth gauge",
        f"haven_notification_outbox_depth {_safe_queue_depth(outbox_depth)}",
        "# HELP haven_notification_outbox_oldest_pending_age_seconds Oldest pending notification outbox age in seconds.",
        "# TYPE haven_notification_outbox_oldest_pending_age_seconds gauge",
        (
            "haven_notification_outbox_oldest_pending_age_seconds "
            f"{max(0, int(outbox_oldest_age_seconds)) if int(outbox_oldest_age_seconds) >= 0 else -1}"
        ),
        "# HELP haven_notification_outbox_retry_age_p95_seconds P95 age of RETRY outbox rows in seconds.",
        "# TYPE haven_notification_outbox_retry_age_p95_seconds gauge",
        (
            "haven_notification_outbox_retry_age_p95_seconds "
            f"{max(0, int(outbox_retry_age_p95_seconds)) if int(outbox_retry_age_p95_seconds) >= 0 else -1}"
        ),
        "# HELP haven_notification_outbox_dead_letter_rate Ratio of DEAD rows in outbox states.",
        "# TYPE haven_notification_outbox_dead_letter_rate gauge",
        f"haven_notification_outbox_dead_letter_rate {float(outbox_dead_letter_rate):.6f}",
        "# HELP haven_notification_outbox_stale_processing_count Count of stale PROCESSING outbox rows.",
        "# TYPE haven_notification_outbox_stale_processing_count gauge",
        (
            "haven_notification_outbox_stale_processing_count "
            f"{max(0, int(outbox_stale_processing_count)) if int(outbox_stale_processing_count) >= 0 else -1}"
        ),
        "# HELP haven_notification_queue_depth In-process notification queue depth.",
        "# TYPE haven_notification_queue_depth gauge",
        f"haven_notification_queue_depth {_safe_queue_depth(queue_depth)}",
        "# HELP haven_journal_queue_depth Journal task queue depth.",
        "# TYPE haven_journal_queue_depth gauge",
        f"haven_journal_queue_depth {_safe_queue_depth(journal_queue_depth)}",
        "# HELP haven_db_query_total Total DB cursor execute calls since process start.",
        "# TYPE haven_db_query_total counter",
        f"haven_db_query_total {max(0, int(db_query_runtime.get('query_total', 0)))}",
        "# HELP haven_db_slow_query_total Total DB queries slower than configured threshold.",
        "# TYPE haven_db_slow_query_total counter",
        f"haven_db_slow_query_total {max(0, int(db_query_runtime.get('slow_query_total', 0)))}",
        "# HELP haven_db_slow_query_threshold_ms Configured slow query threshold in milliseconds.",
        "# TYPE haven_db_slow_query_threshold_ms gauge",
        f"haven_db_slow_query_threshold_ms {max(1, int(db_query_runtime.get('slow_query_threshold_ms', 1)))}",
        "# HELP haven_db_last_slow_query_duration_ms Last observed slow query duration in milliseconds.",
        "# TYPE haven_db_last_slow_query_duration_ms gauge",
        f"haven_db_last_slow_query_duration_ms {max(0, int(db_query_runtime.get('last_slow_query_duration_ms', 0)))}",
    ]
    _append_counter_metrics(lines, prefix="haven_notification_runtime", counters=notification_counters)
    _append_counter_metrics(lines, prefix="haven_dynamic_content_runtime", counters=dynamic_counters)
    _append_counter_metrics(lines, prefix="haven_events_runtime", counters=events_counters)
    _append_counter_metrics(lines, prefix="haven_timeline_runtime", counters=timeline_counters)
    _append_counter_metrics(lines, prefix="haven_ws_runtime", counters=ws_counters)
    _append_counter_metrics(lines, prefix="haven_http_runtime", counters=http_counters)
    _append_counter_metrics(lines, prefix="haven_ai_router_runtime", counters=ai_router_counters)
    _append_counter_metrics(lines, prefix="haven_posthog_runtime", counters=posthog_counters)
    _append_counter_metrics(lines, prefix="haven_notification_outbox_status", counters=outbox_status_counts)
    return "\n".join(lines) + "\n"


def _build_push_sli_payload() -> dict:
    try:
        with Session(engine) as session:
            return build_push_sli_snapshot(session=session)
    except Exception as exc:
        logger.warning("Health push SLI snapshot unavailable: reason=%s", type(exc).__name__)
        return {
            "status": "insufficient_data",
            "reasons": ["push_snapshot_unavailable"],
        }


def _evaluate_push_sli(push_sli: dict) -> dict:
    try:
        return evaluate_push_sli_snapshot(push_sli)
    except Exception as exc:
        logger.warning("Health push SLI evaluation failed: reason=%s", type(exc).__name__)
        return {
            "status": "insufficient_data",
            "reasons": ["push_evaluation_unavailable"],
            "evaluated": {
                "delivery_rate": {
                    "target": HEALTH_PUSH_DELIVERY_RATE_TARGET,
                    "min_samples": HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS,
                },
                "dry_run_latency_p95_ms": {
                    "target": HEALTH_PUSH_DRY_RUN_P95_MS_TARGET,
                    "min_samples": HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES,
                },
                "dispatch_latency_p95_ms": {
                    "target": HEALTH_PUSH_DISPATCH_P95_MS_TARGET,
                    "min_samples": HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS,
                },
                "cleanup_stale_backlog_count": {
                    "target": HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX,
                },
            },
        }


def _build_cuj_sli_payload() -> dict:
    try:
        with Session(engine) as session:
            return build_cuj_sli_snapshot(session=session)
    except Exception as exc:
        logger.warning("Health CUJ SLI snapshot unavailable: reason=%s", type(exc).__name__)
        return {
            "status": "insufficient_data",
            "reasons": ["cuj_snapshot_unavailable"],
            "targets": dict(SLI_TARGETS.get("cuj", {})),
        }


def _evaluate_cuj_sli(cuj_sli: dict) -> dict:
    try:
        return evaluate_cuj_sli_snapshot(cuj_sli)
    except Exception as exc:
        logger.warning("Health CUJ SLI evaluation failed: reason=%s", type(exc).__name__)
        return {
            "status": "insufficient_data",
            "reasons": ["cuj_evaluation_unavailable"],
            "evaluated": {},
        }


def _evaluate_ws_sli(ws_sli: dict) -> dict:
    return _evaluate_ws_sli_from_module(ws_sli=ws_sli, config=WS_SLI_CONFIG)


def _evaluate_ws_burn_rate(ws_burn_rate: dict) -> dict:
    return _evaluate_ws_burn_rate_from_module(
        ws_burn_rate=ws_burn_rate,
        config=WS_SLI_CONFIG,
    )


def _evaluate_ai_router_burn_rate(ai_router_runtime: dict) -> dict:
    if not isinstance(ai_router_runtime, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["ai_router_runtime_unavailable"],
            "evaluated": {},
        }
    burn_rate = ai_router_runtime.get("burn_rate")
    if not isinstance(burn_rate, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["ai_router_burn_rate_missing"],
            "evaluated": {},
        }
    fast_window = burn_rate.get("fast_window")
    slow_window = burn_rate.get("slow_window")
    if not isinstance(fast_window, dict) or not isinstance(slow_window, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["ai_router_burn_rate_window_invalid"],
            "evaluated": {},
        }

    fast_rate = float(fast_window.get("burn_rate", 0.0) or 0.0)
    slow_rate = float(slow_window.get("burn_rate", 0.0) or 0.0)
    fast_enough = bool(fast_window.get("enough_samples", False))
    slow_enough = bool(slow_window.get("enough_samples", False))

    reasons: list[str] = []
    status_value = "ok"
    if not fast_enough and not slow_enough:
        status_value = "insufficient_data"
        reasons.append("ai_router_burn_rate_insufficient_samples")
    else:
        if fast_enough and fast_rate > HEALTH_AI_ROUTER_BURN_RATE_FAST_THRESHOLD:
            reasons.append("ai_router_burn_rate_fast_window_exceeded")
        if slow_enough and slow_rate > HEALTH_AI_ROUTER_BURN_RATE_SLOW_THRESHOLD:
            reasons.append("ai_router_burn_rate_slow_window_exceeded")
        if reasons:
            status_value = "degraded"

    return {
        "status": status_value,
        "reasons": reasons,
        "evaluated": {
            "fast_window_seconds": HEALTH_AI_ROUTER_BURN_RATE_FAST_WINDOW_SECONDS,
            "slow_window_seconds": HEALTH_AI_ROUTER_BURN_RATE_SLOW_WINDOW_SECONDS,
            "fast_threshold": HEALTH_AI_ROUTER_BURN_RATE_FAST_THRESHOLD,
            "slow_threshold": HEALTH_AI_ROUTER_BURN_RATE_SLOW_THRESHOLD,
            "fast_min_attempts": HEALTH_AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_FAST,
            "slow_min_attempts": HEALTH_AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_SLOW,
            "error_budget_fraction": HEALTH_AI_ROUTER_BURN_RATE_ERROR_BUDGET_FRACTION,
        },
    }


def _probe_database() -> dict:
    started = time.perf_counter()
    try:
        with Session(engine) as session:
            session.exec(select(1)).first()
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.warning("Health check database probe failed: reason=%s", type(exc).__name__)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "error": type(exc).__name__,
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"status": "ok", "latency_ms": latency_ms}


def _probe_redis_if_configured() -> dict:
    backend = (settings.ABUSE_GUARD_STORE_BACKEND or "memory").strip().lower()
    if backend != "redis":
        return {"status": "skipped", "reason": "backend_not_redis"}

    redis_url = (settings.ABUSE_GUARD_REDIS_URL or "").strip()
    if not redis_url:
        return {"status": "error", "reason": "missing_redis_url"}

    try:
        import redis
    except Exception:
        return {"status": "error", "reason": "redis_package_missing"}

    started = time.perf_counter()
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.warning("Health check redis probe failed: reason=%s", type(exc).__name__)
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "error": type(exc).__name__,
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"status": "ok", "latency_ms": latency_ms}


def _provider_checks() -> dict:
    return _provider_checks_from_module()


# Shared SLI target contract (single source of truth).
_SLI_TARGETS = SLI_TARGETS


def _build_full_sli_snapshot(*, uptime_seconds: int) -> dict:
    """Build SLI metrics + evaluations — single source of truth for all health endpoints."""
    ws_sli = _build_ws_sli_payload()
    ws_burn_rate = _build_ws_burn_rate_payload()
    push_sli = _build_push_sli_payload()
    cuj_sli = _build_cuj_sli_payload()
    abuse_economics_sli = _build_abuse_economics_sli_payload(uptime_seconds=uptime_seconds)
    tier_policy_evaluation = evaluate_tier_policy(
        health_payload={"sli": {"ws": ws_sli, "cuj": cuj_sli}}
    )

    evaluation = {
        "ws": _evaluate_ws_sli(ws_sli),
        "ws_burn_rate": _evaluate_ws_burn_rate(ws_burn_rate),
        "push": _evaluate_push_sli(push_sli),
        "cuj": _evaluate_cuj_sli(cuj_sli),
        "tier_policy": tier_policy_evaluation,
    }

    return {
        "ws": ws_sli,
        "ws_burn_rate": ws_burn_rate,
        "push": push_sli,
        "cuj": cuj_sli,
        "abuse_economics": abuse_economics_sli,
        "evaluation": evaluation,
    }


def _build_health_slo_payload_for_degradation(app_started_at):
    """Build minimal health payload (sli + evaluation) for degradation evaluation."""
    uptime_seconds = max(0, int((utcnow() - app_started_at).total_seconds()))
    return {"sli": _build_full_sli_snapshot_cached(uptime_seconds=uptime_seconds)}


def _collect_health_runtime_context(*, uptime_seconds: int) -> dict:
    return _collect_health_runtime_context_from_module(
        uptime_seconds=uptime_seconds,
        probe_database=_probe_database,
        probe_redis_if_configured=_probe_redis_if_configured,
        provider_checks=_provider_checks,
        get_notification_outbox_health_snapshot=get_notification_outbox_health_snapshot,
        get_notification_outbox_depth=get_notification_outbox_depth,
        get_notification_outbox_oldest_pending_age_seconds=get_notification_outbox_oldest_pending_age_seconds,
        get_notification_outbox_retry_age_p95_seconds=get_notification_outbox_retry_age_p95_seconds,
        get_notification_outbox_dead_letter_rate=get_notification_outbox_dead_letter_rate,
        get_notification_outbox_stale_processing_count=get_notification_outbox_stale_processing_count,
        get_notification_outbox_dispatch_lock_heartbeat_age_seconds=get_notification_outbox_dispatch_lock_heartbeat_age_seconds,
        outbox_snapshot_value=_outbox_snapshot_value,
        build_runtime_payloads=_build_runtime_payloads,
        compute_dynamic_content_fallback_ratio=_compute_dynamic_content_fallback_ratio,
        get_notification_queue_depth=get_notification_queue_depth,
        get_journal_queue_depth=get_journal_queue_depth,
        get_db_pool_runtime_snapshot=get_db_pool_runtime_snapshot,
        get_db_query_runtime_snapshot=get_db_query_runtime_snapshot,
    )


def _apply_ai_router_burn_rate_to_sli(*, sli: dict, runtime_context: dict) -> tuple[dict, dict]:
    return _apply_sli_evaluation_from_module(
        sli=sli,
        evaluation_key="ai_router_burn_rate",
        evaluation_value=_evaluate_ai_router_burn_rate(runtime_context["ai_router_runtime_payload"]),
    )


def _build_runtime_checks_from_context(*, runtime_context: dict) -> dict:
    return _build_runtime_checks_from_context_from_module(
        runtime_context=runtime_context,
        build_runtime_checks_payload=_build_runtime_checks_payload,
    )


def _build_sli_full_payload(*, sli: dict, runtime_context: dict) -> dict:
    return _build_sli_full_payload_from_module(
        sli=sli,
        runtime_payloads=runtime_context["runtime_payloads"],
        build_rate_limit_sli_payload=_build_rate_limit_sli_payload,
        sli_targets=_SLI_TARGETS,
        merge_runtime_snapshot_if_needed=_merge_runtime_snapshot_if_needed,
        persist_runtime_metrics_snapshot=persist_runtime_metrics_snapshot,
    )


def get_health_router(app_started_at, app_title: str, app_version: str) -> APIRouter:
    router = APIRouter()

    def read_root():
        return {"message": "Hello, Haven v2 is alive!", "status": "active"}

    def health_check():
        now = utcnow()
        uptime_seconds = max(0, int((now - app_started_at).total_seconds()))
        runtime_context = _collect_health_runtime_context(uptime_seconds=uptime_seconds)
        sli = _build_full_sli_snapshot_cached(uptime_seconds=uptime_seconds)
        sli, evaluation_map = _apply_ai_router_burn_rate_to_sli(
            sli=sli,
            runtime_context=runtime_context,
        )
        abuse_evaluation = (
            sli.get("abuse_economics", {}).get("evaluation")
            if isinstance(sli.get("abuse_economics"), dict)
            else {}
        )
        degraded_reasons = collect_degraded_reasons(
            db_probe=runtime_context["db_probe"],
            redis_probe=runtime_context["redis_probe"],
            evaluation_map=evaluation_map,
            abuse_evaluation=abuse_evaluation,
            outbox_depth=runtime_context["outbox_depth"],
            outbox_oldest_pending_age_seconds=runtime_context["outbox_oldest_pending_age_seconds"],
            outbox_retry_age_p95_seconds=runtime_context["outbox_retry_age_p95_seconds"],
            outbox_stale_processing_count=runtime_context["outbox_stale_processing_count"],
            outbox_dead_letter_rate=runtime_context["outbox_dead_letter_rate"],
            outbox_dispatch_lock_heartbeat_age_seconds=runtime_context[
                "outbox_dispatch_lock_heartbeat_age_seconds"
            ],
            outbox_depth_threshold=HEALTH_OUTBOX_DEPTH_DEGRADED_THRESHOLD,
            outbox_oldest_pending_threshold_seconds=HEALTH_OUTBOX_OLDEST_PENDING_DEGRADED_SECONDS,
            outbox_retry_age_p95_threshold_seconds=HEALTH_OUTBOX_RETRY_AGE_P95_DEGRADED_SECONDS,
            outbox_stale_processing_threshold=HEALTH_OUTBOX_STALE_PROCESSING_DEGRADED_THRESHOLD,
            outbox_dead_letter_threshold=HEALTH_OUTBOX_DEAD_LETTER_DEGRADED_THRESHOLD,
            outbox_dispatch_lock_heartbeat_threshold_seconds=HEALTH_OUTBOX_DISPATCH_LOCK_HEARTBEAT_DEGRADED_SECONDS,
            dynamic_fallback_ratio=runtime_context["dynamic_fallback_ratio"],
            dynamic_fallback_attempts=runtime_context["dynamic_fallback_attempts"],
            dynamic_fallback_ratio_threshold=HEALTH_DYNAMIC_FALLBACK_RATIO_DEGRADED_THRESHOLD,
            dynamic_fallback_min_attempts=HEALTH_DYNAMIC_FALLBACK_MIN_ATTEMPTS,
        )
        checks = _build_runtime_checks_from_context(runtime_context=runtime_context)
        sli_full = _build_sli_full_payload(sli=sli, runtime_context=runtime_context)
        payload = _build_health_payload_from_module(
            status_value="degraded" if degraded_reasons else "ok",
            app_title=app_title,
            app_version=app_version,
            environment=settings.ENV,
            timestamp=f"{now.isoformat()}Z",
            uptime_seconds=uptime_seconds,
            checks=checks,
            sli_full=sli_full,
            degraded_reasons=degraded_reasons,
        )

        if degraded_reasons:
            return JSONResponse(status_code=503, content=payload)

        return payload

    def health_degradation():
        """DEG-01/DEG-02: Explicit degradation API for frontend consumption.

        Returns per-feature degradation status and fallback copy for UX banners.
        No auth required; degradation status is non-sensitive.
        """
        health_payload = _build_health_slo_payload_for_degradation(app_started_at)
        result = evaluate_degradation_status(health_payload=health_payload)
        return {
            "status": result["status"],
            "features": result["features"],
            "timestamp": f"{utcnow().isoformat()}Z",
        }

    def health_slo_snapshot():
        now = utcnow()
        uptime_seconds = max(0, int((now - app_started_at).total_seconds()))
        runtime_context = _collect_health_runtime_context(uptime_seconds=uptime_seconds)
        sli = _build_full_sli_snapshot_cached(uptime_seconds=uptime_seconds)
        sli, _ = _apply_ai_router_burn_rate_to_sli(
            sli=sli,
            runtime_context=runtime_context,
        )
        checks = _build_runtime_checks_from_context(runtime_context=runtime_context)
        sli_full = _build_sli_full_payload(sli=sli, runtime_context=runtime_context)
        return _build_health_payload_from_module(
            status_value="ok",
            app_title=app_title,
            app_version=app_version,
            environment=settings.ENV,
            timestamp=f"{now.isoformat()}Z",
            uptime_seconds=uptime_seconds,
            checks=checks,
            sli_full=sli_full,
            notes=HEALTH_SLO_NOTES,
        )

    def health_live():
        return {
            "status": "ok",
            "service": app_title,
            "version": app_version,
            "environment": settings.ENV,
            "timestamp": f"{utcnow().isoformat()}Z",
        }

    def health_ready():
        now = utcnow()
        uptime_seconds = max(0, int((now - app_started_at).total_seconds()))
        db_probe = _probe_database()
        redis_probe = _probe_redis_if_configured()
        status_value = "ok"
        degraded_reasons: list[str] = []
        if db_probe.get("status") != "ok":
            status_value = "degraded"
            degraded_reasons.append("database_unhealthy")
        if redis_probe.get("status") == "error":
            status_value = "degraded"
            degraded_reasons.append("redis_unhealthy")
        payload = {
            "status": status_value,
            "service": app_title,
            "version": app_version,
            "environment": settings.ENV,
            "timestamp": f"{now.isoformat()}Z",
            "uptime_seconds": uptime_seconds,
            "checks": {
                "database": db_probe,
                "redis": redis_probe,
            },
        }
        if degraded_reasons:
            payload["degraded_reasons"] = degraded_reasons
            return JSONResponse(status_code=503, content=payload)
        return payload

    def health_deep():
        # Deep probe alias for operators/tools that expect explicit readiness depth tiers.
        return health_slo_snapshot()

    def metrics_snapshot(request: Request):
        if not _is_metrics_request_authorized(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Metrics authentication failed.",
            )
        payload = _build_openmetrics_payload(app_title=app_title, app_version=app_version)
        return PlainTextResponse(
            content=payload,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    router.get("/")(read_root)
    router.get("/health")(health_check)
    router.get("/health/live")(health_live)
    router.get("/health/ready")(health_ready)
    router.get("/health/deep")(health_deep)
    router.get("/health/degradation")(health_degradation)
    router.get("/health/slo")(health_slo_snapshot)
    router.get("/metrics")(metrics_snapshot)
    return router
