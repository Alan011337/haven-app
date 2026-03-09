from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.health_ws_sli import build_ws_sli_payload  # noqa: E402


class HealthWsSliTests(unittest.TestCase):
    def test_partner_event_latency_p95_absent_when_no_samples(self) -> None:
        payload = build_ws_sli_payload(ws_snapshot={"counters": {}})
        self.assertIsNone(payload.get("partner_event_delivery_latency_p95_ms"))

    def test_partner_event_latency_p95_uses_bucket_histogram(self) -> None:
        counters = {
            "partner_event_delivery_latency_samples_total": 20,
            "partner_event_delivery_latency_bucket_le_10ms_total": 2,
            "partner_event_delivery_latency_bucket_le_25ms_total": 5,
            "partner_event_delivery_latency_bucket_le_50ms_total": 10,
            "partner_event_delivery_latency_bucket_le_100ms_total": 19,
            "partner_event_delivery_latency_bucket_le_250ms_total": 20,
        }
        payload = build_ws_sli_payload(ws_snapshot={"counters": counters})
        self.assertEqual(payload.get("partner_event_delivery_latency_p95_ms"), 100)

    def test_partner_event_publish_and_ack_rates(self) -> None:
        counters = {
            "partner_events_queued": 20,
            "partner_events_publish_attempted": 10,
            "partner_events_publish_succeeded": 8,
            "partner_events_publish_failed": 2,
            "partner_events_delivery_acked": 15,
            "partner_events_delivered": 15,
            "partner_events_failed": 5,
        }
        payload = build_ws_sli_payload(ws_snapshot={"counters": counters})
        self.assertEqual(payload.get("partner_events_publish_attempted_total"), 10)
        self.assertEqual(payload.get("partner_events_publish_succeeded_total"), 8)
        self.assertEqual(payload.get("partner_events_publish_failed_total"), 2)
        self.assertEqual(payload.get("partner_events_delivery_acked_total"), 15)
        self.assertEqual(payload.get("partner_event_publish_success_rate"), 0.8)
        self.assertEqual(payload.get("partner_event_delivery_ack_rate"), 0.75)


if __name__ == "__main__":
    unittest.main()
