import sys
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class _FakeStateStore:
    supports_global_cleanup_scan = True

    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def load(self, key: str):
        value = self.data.get(key)
        return deepcopy(value) if value is not None else None

    def save(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:
        self.data[key] = deepcopy(value)

    def delete(self, key: str) -> None:
        self.data.pop(key, None)

    def iter_keys(self) -> list[str]:
        return list(self.data.keys())


class PairingAbuseGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)

        def _now_fn() -> datetime:
            return self.now

        self.guard = PairingAbuseGuard(
            limit_count=2,
            window_seconds=60,
            failure_threshold=2,
            cooldown_seconds=120,
            now_fn=_now_fn,
        )

    def test_rate_limit_blocks_after_window_quota(self) -> None:
        guard = PairingAbuseGuard(
            limit_count=2,
            window_seconds=60,
            failure_threshold=999,
            cooldown_seconds=120,
            now_fn=lambda: self.now,
        )
        key = "user-a:127.0.0.1"

        allowed, _, _ = guard.allow_attempt(key=key)
        self.assertTrue(allowed)
        guard.record_attempt(key=key, success=False)

        allowed, _, _ = guard.allow_attempt(key=key)
        self.assertTrue(allowed)
        guard.record_attempt(key=key, success=False)

        allowed, reason, retry_after = guard.allow_attempt(key=key)
        self.assertFalse(allowed)
        self.assertEqual(reason, "rate_limited")
        self.assertGreaterEqual(retry_after, 1)

    def test_cooldown_expires_and_allows_next_attempt(self) -> None:
        key = "user-b:127.0.0.1"

        self.guard.record_attempt(key=key, success=False)
        self.guard.record_attempt(key=key, success=False)

        allowed, reason, _ = self.guard.allow_attempt(key=key)
        self.assertFalse(allowed)
        self.assertEqual(reason, "cooldown_active")

        self.now = self.now + timedelta(seconds=121)
        allowed, reason, retry_after = self.guard.allow_attempt(key=key)
        self.assertTrue(allowed)
        self.assertIsNone(reason)
        self.assertEqual(retry_after, 0)

    def test_success_resets_failure_streak(self) -> None:
        guard = PairingAbuseGuard(
            limit_count=10,
            window_seconds=60,
            failure_threshold=2,
            cooldown_seconds=120,
            now_fn=lambda: self.now,
        )
        key = "user-c:127.0.0.1"

        guard.record_attempt(key=key, success=False)
        guard.record_attempt(key=key, success=True)
        guard.record_attempt(key=key, success=False)

        allowed, reason, _ = guard.allow_attempt(key=key)
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_cleanup_prunes_idle_states(self) -> None:
        guard = PairingAbuseGuard(
            limit_count=2,
            window_seconds=10,
            failure_threshold=2,
            cooldown_seconds=5,
            cleanup_interval_seconds=1,
            now_fn=lambda: self.now,
        )
        key = "user-d:127.0.0.1"

        guard.record_attempt(key=key, success=False)
        self.assertEqual(guard.tracked_key_count(), 1)

        self.now = self.now + timedelta(seconds=20)
        guard.allow_attempt(key="trigger:127.0.0.1")

        self.assertEqual(guard.tracked_key_count(), 1)
        self.assertNotIn(key, guard._states)

    def test_guard_works_with_custom_state_store(self) -> None:
        store = _FakeStateStore()
        guard = PairingAbuseGuard(
            limit_count=2,
            window_seconds=60,
            failure_threshold=2,
            cooldown_seconds=120,
            now_fn=lambda: self.now,
            state_store=store,
        )
        key = "user-e:127.0.0.1"

        allowed, _, _ = guard.allow_attempt(key=key)
        self.assertTrue(allowed)
        guard.record_attempt(key=key, success=False)
        guard.record_attempt(key=key, success=False)

        allowed, reason, _ = guard.allow_attempt(key=key)
        self.assertFalse(allowed)
        self.assertEqual(reason, "cooldown_active")
        self.assertIn(key, store.data)

        guard.reset()
        self.assertEqual(store.data, {})


if __name__ == "__main__":
    unittest.main()
