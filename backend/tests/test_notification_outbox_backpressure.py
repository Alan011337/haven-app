from __future__ import annotations

import unittest

from app.services.notification_outbox import resolve_notification_outbox_claim_limit


class NotificationOutboxBackpressureTests(unittest.TestCase):
    def test_claim_limit_scales_up_when_backlog_depth_high(self) -> None:
        selected = resolve_notification_outbox_claim_limit(
            base_limit=20,
            backlog_depth=600,
            oldest_pending_age_seconds=0,
            adaptive_enabled=True,
            adaptive_max_limit=200,
            age_scale_threshold_seconds=300,
            age_critical_seconds=1200,
        )
        self.assertGreaterEqual(selected, 80)

    def test_claim_limit_scales_up_when_oldest_pending_age_high(self) -> None:
        selected = resolve_notification_outbox_claim_limit(
            base_limit=15,
            backlog_depth=0,
            oldest_pending_age_seconds=1800,
            adaptive_enabled=True,
            adaptive_max_limit=120,
            age_scale_threshold_seconds=300,
            age_critical_seconds=1200,
        )
        self.assertGreaterEqual(selected, 60)


if __name__ == "__main__":
    unittest.main()
