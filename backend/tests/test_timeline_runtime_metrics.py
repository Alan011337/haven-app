from __future__ import annotations

import unittest

from app.services.timeline_runtime_metrics import timeline_runtime_metrics


class TimelineRuntimeMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        timeline_runtime_metrics.reset()

    def tearDown(self) -> None:
        timeline_runtime_metrics.reset()

    def test_records_query_budget_and_clamp(self) -> None:
        timeline_runtime_metrics.record_query_budget(
            requested_fetch_limit=120,
            effective_fetch_limit=80,
        )
        snapshot = timeline_runtime_metrics.snapshot()
        self.assertEqual(snapshot.get("timeline_query_total"), 1)
        self.assertEqual(snapshot.get("timeline_budget_requested_fetch_total"), 120)
        self.assertEqual(snapshot.get("timeline_budget_effective_fetch_total"), 80)
        self.assertEqual(snapshot.get("timeline_budget_clamped_total"), 1)

    def test_records_page_result(self) -> None:
        timeline_runtime_metrics.record_page_result(has_more=True, item_count=25)
        snapshot = timeline_runtime_metrics.snapshot()
        self.assertEqual(snapshot.get("timeline_page_served_total"), 1)
        self.assertEqual(snapshot.get("timeline_page_item_total"), 25)
        self.assertEqual(snapshot.get("timeline_page_has_more_total"), 1)


if __name__ == "__main__":
    unittest.main()
