from __future__ import annotations

from app.services.ai_router import build_ai_router_runtime_payload as _build_ai_router_runtime_payload_from_module
from app.services.dynamic_content_pipeline import get_dynamic_content_runtime_state
from app.services.dynamic_content_runtime_metrics import dynamic_content_runtime_metrics
from app.services.events_runtime_metrics import events_runtime_metrics
from app.services.events_log import get_core_loop_ingest_guard_state
from app.services.http_observability import http_observability
from app.services.notification_runtime_metrics import notification_runtime_metrics
from app.services.posthog_events import get_posthog_runtime_snapshot
from app.services.rate_limit_runtime_metrics import rate_limit_runtime_metrics
from app.services.timeline_runtime_metrics import timeline_runtime_metrics


def build_rate_limit_sli_payload() -> dict:
    snapshot = rate_limit_runtime_metrics.snapshot()
    if not isinstance(snapshot, dict):
        return {
            "attempt_total": 0,
            "attempt_by_scope": {},
            "attempt_by_action": {},
            "attempt_by_endpoint": {},
            "attempt_by_action_scope": {},
            "blocked_total": 0,
            "blocked_by_scope": {},
            "blocked_by_action": {},
            "blocked_by_endpoint": {},
            "blocked_by_action_scope": {},
            "block_rate_overall": 0.0,
            "block_rate_by_scope": {},
        }
    return snapshot


def build_http_observability_payload() -> dict:
    return http_observability.snapshot(window_seconds=15 * 60)


def build_ai_router_runtime_payload() -> dict:
    return _build_ai_router_runtime_payload_from_module()


def build_notification_runtime_payload() -> dict:
    return {"counters": notification_runtime_metrics.snapshot()}


def build_dynamic_content_runtime_payload() -> dict:
    return {
        "counters": dynamic_content_runtime_metrics.snapshot(),
        "state": get_dynamic_content_runtime_state(),
    }


def build_events_runtime_payload() -> dict:
    counters = events_runtime_metrics.snapshot()
    attempts = int(counters.get("events_ingest_attempt_total", 0) or 0)
    dropped = int(counters.get("events_sanitize_dropped_items_total", 0) or 0)
    blocked = int(counters.get("events_sanitize_blocked_keys_total", 0) or 0)
    oversized = int(counters.get("events_sanitize_oversized_payload_total", 0) or 0)
    rate_limited = int(counters.get("events_ingest_blocked_total", 0) or 0)
    drop_rate = 0.0 if attempts <= 0 else round(float(dropped + blocked + oversized) / float(attempts), 6)
    rate_limited_rate = 0.0 if attempts <= 0 else round(float(rate_limited) / float(attempts), 6)
    return {
        "counters": counters,
        "drop_rate_overall": drop_rate,
        "rate_limited_rate_overall": rate_limited_rate,
        "ingest_guard": get_core_loop_ingest_guard_state(),
    }


def build_timeline_runtime_payload() -> dict:
    return {"counters": timeline_runtime_metrics.snapshot()}


def build_posthog_runtime_payload() -> dict:
    return {"counters": get_posthog_runtime_snapshot()}
