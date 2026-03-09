from __future__ import annotations

import re
from threading import Lock


def _sanitize_metric_key(raw: str, *, max_length: int) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw or "").strip().lower()).strip("_")
    cleaned = cleaned[: max(1, int(max_length))]
    return cleaned or "unknown"


class EventsRuntimeMetrics:
    _CARDINALITY_OVERFLOW_KEY = "events_runtime_metric_cardinality_overflow_total"

    def __init__(self, *, max_keys: int = 240, key_max_length: int = 96) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self._max_keys = max(8, int(max_keys))
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

    def record_ingest_attempt(self, *, event_name: str) -> None:
        safe_event = _sanitize_metric_key(event_name, max_length=self._key_max_length)
        self.increment("events_ingest_attempt_total")
        self.increment(f"events_ingest_attempt_{safe_event}_total")

    def record_ingest_result(self, *, event_name: str, deduped: bool) -> None:
        safe_event = _sanitize_metric_key(event_name, max_length=self._key_max_length)
        if deduped:
            self.increment("events_ingest_deduped_total")
            self.increment(f"events_ingest_deduped_{safe_event}_total")
            return
        self.increment("events_ingest_accepted_total")
        self.increment(f"events_ingest_accepted_{safe_event}_total")

    def record_ingest_blocked(self, *, event_name: str, reason: str) -> None:
        safe_event = _sanitize_metric_key(event_name, max_length=self._key_max_length)
        safe_reason = _sanitize_metric_key(reason, max_length=self._key_max_length)
        self.increment("events_ingest_blocked_total")
        self.increment(f"events_ingest_blocked_{safe_event}_total")
        self.increment(f"events_ingest_blocked_reason_{safe_reason}_total")

    def record_sanitize(self, *, blocked_keys: int, dropped_items: int, oversized_payloads: int) -> None:
        if blocked_keys > 0:
            self.increment("events_sanitize_blocked_keys_total", amount=blocked_keys)
        if dropped_items > 0:
            self.increment("events_sanitize_dropped_items_total", amount=dropped_items)
        if oversized_payloads > 0:
            self.increment("events_sanitize_oversized_payload_total", amount=oversized_payloads)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


events_runtime_metrics = EventsRuntimeMetrics()
