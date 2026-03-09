from __future__ import annotations

from threading import Lock


class TimelineRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}

    def increment(self, key: str, *, amount: int = 1) -> None:
        if amount <= 0:
            return
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def record_query_budget(
        self,
        *,
        requested_fetch_limit: int,
        effective_fetch_limit: int,
    ) -> None:
        self.increment("timeline_query_total")
        self.increment("timeline_budget_requested_fetch_total", amount=max(0, requested_fetch_limit))
        self.increment("timeline_budget_effective_fetch_total", amount=max(0, effective_fetch_limit))
        if effective_fetch_limit < requested_fetch_limit:
            self.increment("timeline_budget_clamped_total")

    def record_page_result(self, *, has_more: bool, item_count: int) -> None:
        self.increment("timeline_page_served_total")
        self.increment("timeline_page_item_total", amount=max(0, item_count))
        if has_more:
            self.increment("timeline_page_has_more_total")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


timeline_runtime_metrics = TimelineRuntimeMetrics()

