from __future__ import annotations

import time
import unittest

from app.services.worker_lock import WorkerSingletonLock


class WorkerLockStateTests(unittest.TestCase):
    def test_read_lock_state_returns_payload_when_acquired(self) -> None:
        lock = WorkerSingletonLock(
            lock_name="worker-lock-state-test",
            heartbeat_seconds=1.0,
        )
        self.assertTrue(lock.acquire())
        try:
            time.sleep(0.05)
            payload = WorkerSingletonLock.read_lock_state("worker-lock-state-test")
            self.assertIsInstance(payload, dict)
            self.assertIsInstance(payload.get("pid"), int)
            self.assertIn(payload.get("status"), {"acquired", "heartbeat"})
            self.assertIn("updated_at", payload)
        finally:
            lock.release()


if __name__ == "__main__":
    unittest.main()
