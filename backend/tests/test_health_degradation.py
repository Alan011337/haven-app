from __future__ import annotations

import unittest

from app.core.health_degradation import collect_degraded_reasons


class HealthDegradationTests(unittest.TestCase):
    def test_collect_degraded_reasons_includes_runtime_thresholds(self) -> None:
        reasons = collect_degraded_reasons(
            db_probe={"status": "error"},
            redis_probe={"status": "error"},
            evaluation_map={
                "ws": {"status": "degraded"},
                "ws_burn_rate": {"status": "degraded"},
                "push": {"status": "degraded"},
                "cuj": {"status": "degraded"},
                "tier_policy": {"status": "degraded"},
            },
            abuse_evaluation={"status": "block"},
            outbox_depth=100,
            outbox_oldest_pending_age_seconds=4000,
            outbox_retry_age_p95_seconds=5000,
            outbox_stale_processing_count=10,
            outbox_dead_letter_rate=0.8,
            outbox_dispatch_lock_heartbeat_age_seconds=300,
            outbox_depth_threshold=20,
            outbox_oldest_pending_threshold_seconds=30,
            outbox_retry_age_p95_threshold_seconds=90,
            outbox_stale_processing_threshold=5,
            outbox_dead_letter_threshold=0.1,
            outbox_dispatch_lock_heartbeat_threshold_seconds=60,
            dynamic_fallback_ratio=0.9,
            dynamic_fallback_attempts=100,
            dynamic_fallback_ratio_threshold=0.5,
            dynamic_fallback_min_attempts=10,
        )
        expected = {
            "database_unhealthy",
            "redis_unhealthy",
            "ws_sli_below_target",
            "ws_burn_rate_above_threshold",
            "push_sli_below_target",
            "cuj_sli_below_target",
            "sre_tier_budget_exceeded",
            "abuse_economics_budget_block",
            "notification_outbox_depth_high",
            "notification_outbox_oldest_pending_high",
            "notification_outbox_retry_age_high",
            "notification_outbox_stale_processing_high",
            "notification_outbox_dispatch_lock_heartbeat_stale",
            "notification_outbox_dead_letter_rate_high",
            "dynamic_content_fallback_ratio_high",
        }
        self.assertEqual(set(reasons), expected)


if __name__ == "__main__":
    unittest.main()
