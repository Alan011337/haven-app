from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from urllib import error as url_error
from urllib import request

from app.core.config import settings

logger = logging.getLogger(__name__)

_POSTHOG_PATH = "/capture/"
_MAX_STRING_LENGTH = 200
_PII_KEY_PATTERN = re.compile(
    r"(email|token|password|secret|authorization|cookie|content|journal|body_text|raw)",
    re.IGNORECASE,
)
_executor_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None
_inflight_lock = threading.Lock()
_inflight_count = 0
_runtime_lock = threading.Lock()
_runtime_counters: dict[str, int] = {
    "capture_attempted_total": 0,
    "capture_submitted_total": 0,
    "capture_dropped_queue_full_total": 0,
    "capture_send_success_total": 0,
    "capture_send_failed_total": 0,
    "capture_retry_total": 0,
    "capture_retry_exhausted_total": 0,
}
_TRANSIENT_SEND_ERRORS = (url_error.HTTPError, url_error.URLError, TimeoutError, OSError)


def _increment_runtime_counter(key: str, *, amount: int = 1) -> None:
    if amount <= 0:
        return
    with _runtime_lock:
        _runtime_counters[key] = int(_runtime_counters.get(key, 0)) + int(amount)


def get_posthog_runtime_snapshot() -> dict[str, Any]:
    with _runtime_lock:
        counters = dict(_runtime_counters)
    with _inflight_lock:
        inflight = int(_inflight_count)
    counters["inflight_count"] = inflight
    counters["max_inflight_limit"] = _max_inflight_events()
    return counters


def _ensure_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="posthog")
        return _executor


def _max_inflight_events() -> int:
    return max(1, int(getattr(settings, "POSTHOG_MAX_INFLIGHT_EVENTS", 128) or 128))


def _try_acquire_inflight_slot() -> bool:
    global _inflight_count
    with _inflight_lock:
        if _inflight_count >= _max_inflight_events():
            return False
        _inflight_count += 1
        return True


def _release_inflight_slot() -> None:
    global _inflight_count
    with _inflight_lock:
        if _inflight_count <= 0:
            _inflight_count = 0
            return
        _inflight_count -= 1


def _retry_attempts() -> int:
    return max(1, int(getattr(settings, "POSTHOG_RETRY_ATTEMPTS", 2) or 2))


def _retry_base_seconds() -> float:
    return max(0.01, float(getattr(settings, "POSTHOG_RETRY_BASE_SECONDS", 0.05) or 0.05))


def _send_posthog_with_retry(payload: dict[str, Any]) -> None:
    max_attempts = _retry_attempts()
    base_seconds = _retry_base_seconds()
    for attempt in range(1, max_attempts + 1):
        try:
            _send_posthog(payload)
            _increment_runtime_counter("capture_send_success_total")
            return
        except _TRANSIENT_SEND_ERRORS:
            if attempt >= max_attempts:
                _increment_runtime_counter("capture_retry_exhausted_total")
                raise
            _increment_runtime_counter("capture_retry_total")
            delay = min(0.5, base_seconds * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, delay)
            time.sleep(delay + jitter)


def _sanitize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if len(cleaned) > _MAX_STRING_LENGTH:
            return cleaned[:_MAX_STRING_LENGTH]
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value[:20]]
    if isinstance(value, dict):
        return _sanitize_properties(value)
    return str(value)[:_MAX_STRING_LENGTH]


def _sanitize_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    if not properties:
        return {}
    sanitized: dict[str, Any] = {}
    for raw_key, raw_value in properties.items():
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip().lower()
        if not key:
            continue
        if _PII_KEY_PATTERN.search(key):
            continue
        sanitized[key[:64]] = _sanitize_value(raw_value)
    return sanitized


def _send_posthog(payload: dict[str, Any]) -> None:
    host = (getattr(settings, "POSTHOG_HOST", "") or "").strip().rstrip("/")
    api_key = (getattr(settings, "POSTHOG_API_KEY", "") or "").strip()
    if not host or not api_key:
        return
    timeout = max(0.2, float(getattr(settings, "POSTHOG_TIMEOUT_SECONDS", 1.0)))
    req = request.Request(
        url=f"{host}{_POSTHOG_PATH}",
        data=json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        _ = resp.read(32)


def capture_posthog_event(
    *,
    event_name: str,
    distinct_id: str,
    properties: dict[str, Any] | None = None,
) -> None:
    if not bool(getattr(settings, "POSTHOG_ENABLED", False)):
        return
    _increment_runtime_counter("capture_attempted_total")

    normalized_event = (event_name or "").strip().lower()
    normalized_distinct_id = (distinct_id or "").strip()
    if not normalized_event or not normalized_distinct_id:
        return

    api_key = (getattr(settings, "POSTHOG_API_KEY", "") or "").strip()
    host = (getattr(settings, "POSTHOG_HOST", "") or "").strip()
    if not api_key or not host:
        return

    if not _try_acquire_inflight_slot():
        _increment_runtime_counter("capture_dropped_queue_full_total")
        logger.debug("posthog_capture_dropped reason=queue_full")
        return

    payload = {
        "api_key": api_key,
        "event": normalized_event,
        "distinct_id": normalized_distinct_id,
        "properties": {
            "$lib": "haven-backend",
            **_sanitize_properties(properties),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    def _submit() -> None:
        try:
            _send_posthog_with_retry(payload)
        except _TRANSIENT_SEND_ERRORS as exc:
            _increment_runtime_counter("capture_send_failed_total")
            logger.debug("posthog_capture_failed reason=%s", type(exc).__name__)
        except ValueError as exc:
            _increment_runtime_counter("capture_send_failed_total")
            logger.debug("posthog_capture_failed reason=%s", type(exc).__name__)
        except Exception as exc:
            _increment_runtime_counter("capture_send_failed_total")
            logger.debug("posthog_capture_failed reason=%s", type(exc).__name__)
        finally:
            _release_inflight_slot()

    try:
        _ensure_executor().submit(_submit)
        _increment_runtime_counter("capture_submitted_total")
    except Exception:
        _release_inflight_slot()
        _increment_runtime_counter("capture_send_failed_total")
        logger.debug("posthog_capture_submit_failed")
