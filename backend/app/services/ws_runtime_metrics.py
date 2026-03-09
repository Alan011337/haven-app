from __future__ import annotations

import time
from threading import Lock
from typing import Any


_PARTNER_EVENT_LATENCY_BUCKETS_MS = (10, 25, 50, 100, 250, 500, 1000, 2000, 5000)


class WsRuntimeMetrics:
    def __init__(self, *, retention_seconds: int = 60 * 60 * 25) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self._window_counters: dict[int, dict[str, int]] = {}
        self._retention_seconds = max(60, int(retention_seconds))

    @staticmethod
    def _resolve_bucket_start(now_ts: float) -> int:
        safe_now = max(0.0, float(now_ts))
        return int(safe_now // 60) * 60

    def _prune_windows(self, *, now_bucket_start: int) -> None:
        cutoff = now_bucket_start - self._retention_seconds
        stale_keys = [bucket for bucket in self._window_counters.keys() if bucket < cutoff]
        for bucket in stale_keys:
            self._window_counters.pop(bucket, None)

    def increment(self, key: str, amount: int = 1, *, timestamp: float | None = None) -> None:
        safe_key = (key or "").strip()
        if not safe_key:
            return
        safe_amount = int(amount)
        if safe_amount <= 0:
            return
        now_ts = float(timestamp if timestamp is not None else time.time())
        bucket_start = self._resolve_bucket_start(now_ts)
        with self._lock:
            self._counters[safe_key] = self._counters.get(safe_key, 0) + safe_amount
            bucket_counters = self._window_counters.setdefault(bucket_start, {})
            bucket_counters[safe_key] = bucket_counters.get(safe_key, 0) + safe_amount
            self._prune_windows(now_bucket_start=bucket_start)

    def snapshot(self, *, active_connections: int | None = None) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)

        payload: dict[str, Any] = {"counters": counters}
        if active_connections is not None:
            payload["active_connections"] = max(0, int(active_connections))
        return payload

    def window_snapshot(self, *, window_seconds: int, now_ts: float | None = None) -> dict[str, int]:
        safe_window_seconds = max(1, int(window_seconds))
        current_ts = float(now_ts if now_ts is not None else time.time())
        bucket_start = self._resolve_bucket_start(current_ts)
        window_start_ts = current_ts - safe_window_seconds
        aggregated: dict[str, int] = {}
        with self._lock:
            self._prune_windows(now_bucket_start=bucket_start)
            for bucket, counters in self._window_counters.items():
                if bucket < window_start_ts:
                    continue
                for key, value in counters.items():
                    aggregated[key] = aggregated.get(key, 0) + int(value)
        return aggregated

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._window_counters.clear()


ws_runtime_metrics = WsRuntimeMetrics()


def record_partner_event_queued() -> None:
    """SLO-03: Track partner event queued for WS delivery."""
    ws_runtime_metrics.increment("partner_events_queued")


def record_partner_event_publish_attempted() -> None:
    """Track publish attempts (redis publish / in-process enqueue)."""
    ws_runtime_metrics.increment("partner_events_publish_attempted")


def record_partner_event_publish_succeeded() -> None:
    """Track publish successes before downstream delivery ack."""
    ws_runtime_metrics.increment("partner_events_publish_succeeded")


def record_partner_event_publish_failed() -> None:
    """Track publish failures before downstream delivery ack."""
    ws_runtime_metrics.increment("partner_events_publish_failed")


def record_partner_event_delivered() -> None:
    """SLO-03: Track partner event successfully delivered via WS (delivery ack)."""
    ws_runtime_metrics.increment("partner_events_delivered")
    ws_runtime_metrics.increment("partner_events_delivery_acked")


def record_partner_event_failed() -> None:
    """SLO-03: Track partner event delivery failure."""
    ws_runtime_metrics.increment("partner_events_failed")


def record_partner_event_delivery_latency_ms(latency_ms: float | int) -> None:
    """
    Track partner-event delivery latency with fixed buckets for cheap runtime observability.
    """
    try:
        safe_latency_ms = max(0.0, float(latency_ms))
    except (TypeError, ValueError):
        return
    ws_runtime_metrics.increment("partner_event_delivery_latency_samples_total")
    for bucket_ms in _PARTNER_EVENT_LATENCY_BUCKETS_MS:
        if safe_latency_ms <= float(bucket_ms):
            ws_runtime_metrics.increment(
                f"partner_event_delivery_latency_bucket_le_{bucket_ms}ms_total"
            )
            return
    ws_runtime_metrics.increment("partner_event_delivery_latency_bucket_gt_5000ms_total")
