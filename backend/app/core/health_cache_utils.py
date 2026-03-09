from __future__ import annotations

import os
from typing import Any

from app.core.config import settings


def is_metrics_request_authorized(*, metrics_auth_token: str | None, auth_header: str | None, metrics_header: str | None) -> bool:
    configured_token = (metrics_auth_token or "").strip()
    require_auth = bool(getattr(settings, "METRICS_REQUIRE_AUTH", False)) or bool(configured_token)
    if not require_auth:
        return True

    provided_token = (metrics_header or "").strip()
    if not provided_token:
        auth_header_value = (auth_header or "").strip()
        if auth_header_value.lower().startswith("bearer "):
            provided_token = auth_header_value[7:].strip()

    if not provided_token:
        return False
    return provided_token == configured_token


def should_bypass_health_cache() -> bool:
    # Never cache in test runs to avoid cross-test state bleed.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    env = (getattr(settings, "ENV", "") or "").strip().lower()
    return env == "test"


def is_runtime_counter_payload_empty(payload: object) -> bool:
    if not isinstance(payload, dict):
        return True
    counters = payload.get("counters")
    if not isinstance(counters, dict) or not counters:
        return True
    for value in counters.values():
        if isinstance(value, (int, float)) and value > 0:
            return False
    return True


def merge_runtime_snapshot_if_needed(sli_payload: dict[str, Any], snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(sli_payload, dict):
        return sli_payload
    if not isinstance(snapshot, dict):
        return sli_payload
    snap_sli = snapshot.get("sli")
    if not isinstance(snap_sli, dict):
        return sli_payload

    for runtime_key in (
        "notification_runtime",
        "dynamic_content_runtime",
        "events_runtime",
        "timeline_runtime",
        "write_rate_limit",
    ):
        current_value = sli_payload.get(runtime_key)
        snapshot_value = snap_sli.get(runtime_key)
        if runtime_key == "write_rate_limit":
            if isinstance(current_value, dict) and isinstance(snapshot_value, dict):
                current_blocked = int(current_value.get("blocked_total", 0) or 0)
                current_attempt = int(current_value.get("attempt_total", 0) or 0)
                if current_attempt == 0 and current_blocked == 0:
                    sli_payload[runtime_key] = snapshot_value
            continue

        if is_runtime_counter_payload_empty(current_value) and isinstance(snapshot_value, dict):
            sli_payload[runtime_key] = snapshot_value
    return sli_payload
