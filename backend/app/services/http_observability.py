from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Deque


@dataclass
class _RequestSample:
    ts: float
    latency_ms: float
    status_code: int


class HttpObservability:
    """Lightweight in-memory HTTP observability snapshot for /health."""

    def __init__(self, *, max_samples: int = 20000) -> None:
        self._samples: Deque[_RequestSample] = deque(maxlen=max(1000, max_samples))
        self._lock = Lock()

    def record(self, *, latency_ms: float, status_code: int, now_ts: float | None = None) -> None:
        ts = float(now_ts if now_ts is not None else time())
        sample = _RequestSample(ts=ts, latency_ms=max(0.0, float(latency_ms)), status_code=int(status_code))
        with self._lock:
            self._samples.append(sample)

    def snapshot(self, *, window_seconds: int = 900) -> dict:
        now = time()
        cutoff = now - max(1, int(window_seconds))
        with self._lock:
            values = [item for item in self._samples if item.ts >= cutoff]
        if not values:
            return {
                "window_seconds": window_seconds,
                "sample_count": 0,
                "error_rate": 0.0,
                "latency_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0},
            }
        latencies = sorted(item.latency_ms for item in values)
        sample_count = len(latencies)
        error_count = sum(1 for item in values if item.status_code >= 500)
        return {
            "window_seconds": window_seconds,
            "sample_count": sample_count,
            "error_rate": round(error_count / sample_count, 4),
            "latency_ms": {
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
                "p99": _percentile(latencies, 0.99),
            },
        }


def _percentile(sorted_values: list[float], ratio: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int(round((len(sorted_values) - 1) * ratio))
    idx = max(0, min(idx, len(sorted_values) - 1))
    return round(float(sorted_values[idx]), 3)


http_observability = HttpObservability()
