from __future__ import annotations

import unittest

from app.core.health_runtime_checks import build_runtime_checks_payload


class HealthRuntimeChecksContractTests(unittest.TestCase):
    def test_build_runtime_checks_includes_db_runtime_blocks(self) -> None:
        payload = build_runtime_checks_payload(
            database_probe={"status": "ok"},
            redis_probe={"status": "ok"},
            providers={},
            notification_queue_depth=0,
            notification_outbox_depth=0,
            notification_outbox_oldest_pending_age_seconds=0,
            notification_outbox_retry_age_p95_seconds=0,
            notification_outbox_dead_letter_rate=0.0,
            notification_outbox_stale_processing_count=0,
            notification_outbox_dispatch_lock_heartbeat_age_seconds=0,
            dynamic_content_fallback_ratio=0.0,
            dynamic_content_fallback_attempts=0,
            journal_queue_depth=0,
            db_pool_runtime={"checked_out": 1},
            db_query_runtime={"query_total": 10},
        )
        self.assertIn("db_pool_runtime", payload)
        self.assertEqual(payload["db_pool_runtime"]["checked_out"], 1)
        self.assertIn("db_query_runtime", payload)
        self.assertEqual(payload["db_query_runtime"]["query_total"], 10)


if __name__ == "__main__":
    unittest.main()
