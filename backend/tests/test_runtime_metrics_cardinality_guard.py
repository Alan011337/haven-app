from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.dynamic_content_runtime_metrics import DynamicContentRuntimeMetrics  # noqa: E402
from app.services.notification_runtime_metrics import NotificationRuntimeMetrics  # noqa: E402


class RuntimeMetricsCardinalityGuardTests(unittest.TestCase):
    def test_notification_metrics_caps_unique_keys(self) -> None:
        metrics = NotificationRuntimeMetrics(max_keys=3, key_max_length=32)
        metrics.increment("a")
        metrics.increment("b")
        metrics.increment("c")
        metrics.increment("d")
        metrics.increment("e")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.get("a"), 1)
        self.assertEqual(snapshot.get("b"), 1)
        self.assertEqual(snapshot.get("c"), 1)
        self.assertEqual(snapshot.get("notification_runtime_metric_cardinality_overflow_total"), 2)

    def test_dynamic_metrics_caps_unique_keys(self) -> None:
        metrics = DynamicContentRuntimeMetrics(max_keys=2, key_max_length=24)
        metrics.increment("metric_one")
        metrics.increment("metric_two")
        metrics.increment("metric_three")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.get("metric_one"), 1)
        self.assertEqual(snapshot.get("metric_two"), 1)
        self.assertEqual(snapshot.get("dynamic_content_runtime_metric_cardinality_overflow_total"), 1)

    def test_notification_failure_reason_not_in_allowlist_maps_to_other(self) -> None:
        metrics = NotificationRuntimeMetrics(max_keys=10, key_max_length=48)
        metrics.record_result(channel="push", success=False, reason="third_party_http_503_retry_later")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.get("notification_failure_push_total"), 1)
        self.assertEqual(snapshot.get("notification_failure_push_other_total"), 1)


if __name__ == "__main__":
    unittest.main()
