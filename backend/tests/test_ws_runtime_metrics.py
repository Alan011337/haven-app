import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ws_runtime_metrics import WsRuntimeMetrics  # noqa: E402
from app.services import ws_runtime_metrics as ws_metrics_module  # noqa: E402


class WsRuntimeMetricsTests(unittest.TestCase):
    def test_increment_and_snapshot(self) -> None:
        metrics = WsRuntimeMetrics()
        metrics.increment("connections_accepted")
        metrics.increment("connections_accepted")
        metrics.increment("messages_received", amount=3)

        snapshot = metrics.snapshot(active_connections=7)
        self.assertEqual(snapshot["active_connections"], 7)
        counters = snapshot["counters"]
        self.assertEqual(counters["connections_accepted"], 2)
        self.assertEqual(counters["messages_received"], 3)

    def test_snapshot_is_copy(self) -> None:
        metrics = WsRuntimeMetrics()
        metrics.increment("typing_events_forwarded", amount=2)
        snapshot = metrics.snapshot()
        snapshot["counters"]["typing_events_forwarded"] = 999

        new_snapshot = metrics.snapshot()
        self.assertEqual(new_snapshot["counters"]["typing_events_forwarded"], 2)

    def test_invalid_inputs_are_ignored(self) -> None:
        metrics = WsRuntimeMetrics()
        metrics.increment("", amount=1)
        metrics.increment("events", amount=0)
        metrics.increment("events", amount=-2)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["counters"], {})

    def test_window_snapshot_aggregates_within_window(self) -> None:
        metrics = WsRuntimeMetrics(retention_seconds=60 * 60 * 25)
        base_ts = 1_700_000_000.0
        metrics.increment("messages_received", amount=2, timestamp=base_ts - 30)
        metrics.increment("messages_received", amount=3, timestamp=base_ts - 4 * 60)
        metrics.increment("messages_received", amount=5, timestamp=base_ts - 12 * 60)
        metrics.increment("messages_rate_limited", amount=1, timestamp=base_ts - 4 * 60)

        window_5m = metrics.window_snapshot(window_seconds=5 * 60, now_ts=base_ts)
        self.assertEqual(window_5m["messages_received"], 5)
        self.assertEqual(window_5m["messages_rate_limited"], 1)

        window_15m = metrics.window_snapshot(window_seconds=15 * 60, now_ts=base_ts)
        self.assertEqual(window_15m["messages_received"], 10)
        self.assertEqual(window_15m["messages_rate_limited"], 1)

    def test_window_snapshot_prunes_stale_buckets(self) -> None:
        metrics = WsRuntimeMetrics(retention_seconds=60 * 30)
        base_ts = 1_700_000_000.0
        metrics.increment("events", amount=2, timestamp=base_ts - 60 * 60)
        metrics.increment("events", amount=3, timestamp=base_ts)

        snapshot = metrics.window_snapshot(window_seconds=60 * 120, now_ts=base_ts)
        self.assertEqual(snapshot["events"], 3)

    def test_partner_event_helpers_include_publish_and_delivery_ack(self) -> None:
        ws_metrics_module.ws_runtime_metrics.reset()
        ws_metrics_module.record_partner_event_queued()
        ws_metrics_module.record_partner_event_publish_attempted()
        ws_metrics_module.record_partner_event_publish_succeeded()
        ws_metrics_module.record_partner_event_delivered()
        ws_metrics_module.record_partner_event_publish_failed()
        snapshot = ws_metrics_module.ws_runtime_metrics.snapshot()
        counters = snapshot["counters"]
        self.assertEqual(counters.get("partner_events_queued"), 1)
        self.assertEqual(counters.get("partner_events_publish_attempted"), 1)
        self.assertEqual(counters.get("partner_events_publish_succeeded"), 1)
        self.assertEqual(counters.get("partner_events_publish_failed"), 1)
        self.assertEqual(counters.get("partner_events_delivered"), 1)
        self.assertEqual(counters.get("partner_events_delivery_acked"), 1)


if __name__ == "__main__":
    unittest.main()
