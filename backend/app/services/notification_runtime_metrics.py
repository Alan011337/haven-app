from __future__ import annotations

import re
from threading import Lock


def _sanitize_metric_key(raw: str, *, max_length: int) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw or "").strip().lower()).strip("_")
    cleaned = cleaned[: max(1, int(max_length))]
    return cleaned or "unknown"


class NotificationRuntimeMetrics:
    _CARDINALITY_OVERFLOW_KEY = "notification_runtime_metric_cardinality_overflow_total"
    _REASON_ALLOWLIST = frozenset(
        {
            "provider_unavailable",
            "no_subscriptions",
            "channel_disabled",
            "transport_error",
            "unexpected_error",
            "db_error",
            "payload_error",
            "timeout",
            "unknown",
        }
    )

    def __init__(self, *, max_keys: int = 400, key_max_length: int = 96) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self._max_keys = max(2, int(max_keys))
        self._key_max_length = max(8, int(key_max_length))

    def increment(self, key: str, *, amount: int = 1) -> None:
        if amount <= 0:
            return
        metric_key = _sanitize_metric_key(key, max_length=self._key_max_length)
        with self._lock:
            if metric_key not in self._counters and len(self._counters) >= self._max_keys:
                self._counters[self._CARDINALITY_OVERFLOW_KEY] = (
                    self._counters.get(self._CARDINALITY_OVERFLOW_KEY, 0) + amount
                )
                return
            self._counters[metric_key] = self._counters.get(metric_key, 0) + amount

    def record_attempt(self, *, channel: str) -> None:
        safe_channel = _sanitize_metric_key(channel, max_length=self._key_max_length)
        self.increment(f"notification_attempt_{safe_channel}_total")

    def record_result(self, *, channel: str, success: bool, reason: str | None = None) -> None:
        safe_channel = _sanitize_metric_key(channel, max_length=self._key_max_length)
        if success:
            self.increment(f"notification_success_{safe_channel}_total")
            return

        safe_reason = _sanitize_metric_key(reason or "unknown", max_length=self._key_max_length)
        if safe_reason not in self._REASON_ALLOWLIST:
            safe_reason = "other"
        self.increment(f"notification_failure_{safe_channel}_total")
        self.increment(f"notification_failure_{safe_channel}_{safe_reason}_total")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


notification_runtime_metrics = NotificationRuntimeMetrics()
