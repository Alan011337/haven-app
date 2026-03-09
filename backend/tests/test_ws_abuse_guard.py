import sys
import unittest
from copy import deepcopy
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ws_abuse_guard import WsAbuseGuard  # noqa: E402


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


class _FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def now(self) -> float:
        return self.current


class WsAbuseGuardTests(unittest.TestCase):
    def test_connection_caps(self) -> None:
        guard = WsAbuseGuard(
            limit_count=10,
            window_seconds=60,
            backoff_seconds=30,
            max_payload_bytes=4096,
        )

        ok, reason = guard.allow_new_connection(
            user_id="u1",
            active_user_connections=0,
            active_total_connections=10,
            max_connections_per_user=1,
            max_connections_global=100,
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

        ok, reason = guard.allow_new_connection(
            user_id="u1",
            active_user_connections=1,
            active_total_connections=10,
            max_connections_per_user=1,
            max_connections_global=100,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "per_user_connection_cap")

        ok, reason = guard.allow_new_connection(
            user_id="u2",
            active_user_connections=0,
            active_total_connections=100,
            max_connections_per_user=2,
            max_connections_global=100,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "global_connection_cap")

    def test_payload_size_limit(self) -> None:
        guard = WsAbuseGuard(
            limit_count=10,
            window_seconds=60,
            backoff_seconds=30,
            max_payload_bytes=8,
        )
        allowed, violation = guard.evaluate_message(
            user_id="u1",
            payload_text="0123456789",
        )
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "payload_too_large")
        self.assertEqual(violation["retry_after_seconds"], 30)

    def test_rate_limit_and_backoff(self) -> None:
        fake_clock = _FakeClock()
        guard = WsAbuseGuard(
            limit_count=2,
            window_seconds=10,
            backoff_seconds=5,
            max_payload_bytes=4096,
            clock=fake_clock.now,
        )

        allowed, _ = guard.evaluate_message(user_id="u1", payload_text="a")
        self.assertTrue(allowed)

        fake_clock.current = 1.0
        allowed, _ = guard.evaluate_message(user_id="u1", payload_text="b")
        self.assertTrue(allowed)

        fake_clock.current = 2.0
        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="c")
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "message_rate_limited")
        self.assertEqual(violation["retry_after_seconds"], 5)

        fake_clock.current = 4.0
        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="d")
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "backoff_active")
        self.assertEqual(violation["retry_after_seconds"], 3)

        fake_clock.current = 7.1
        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="e")
        self.assertTrue(allowed)
        self.assertIsNone(violation)

    def test_cleanup_prunes_idle_user_state(self) -> None:
        fake_clock = _FakeClock()
        guard = WsAbuseGuard(
            limit_count=1,
            window_seconds=1,
            backoff_seconds=1,
            max_payload_bytes=4096,
            cleanup_interval_seconds=1,
            clock=fake_clock.now,
        )

        allowed, _ = guard.evaluate_message(user_id="u1", payload_text="a")
        self.assertTrue(allowed)
        self.assertEqual(guard.tracked_user_count(), 1)

        fake_clock.current = 5.0
        allowed, _ = guard.evaluate_message(user_id="u2", payload_text="b")
        self.assertTrue(allowed)

        self.assertEqual(guard.tracked_user_count(), 1)
        self.assertNotIn("u1", guard._message_windows)

    def test_cleanup_prunes_expired_backoff_state(self) -> None:
        fake_clock = _FakeClock()
        guard = WsAbuseGuard(
            limit_count=1,
            window_seconds=10,
            backoff_seconds=2,
            max_payload_bytes=4096,
            cleanup_interval_seconds=1,
            clock=fake_clock.now,
        )

        allowed, _ = guard.evaluate_message(user_id="u1", payload_text="a")
        self.assertTrue(allowed)
        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="b")
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "message_rate_limited")
        self.assertIn("u1", guard._backoff_until)

        fake_clock.current = 5.0
        allowed, _ = guard.evaluate_message(user_id="u2", payload_text="c")
        self.assertTrue(allowed)

        self.assertNotIn("u1", guard._backoff_until)

    def test_guard_works_with_custom_state_store(self) -> None:
        fake_clock = _FakeClock()
        store = _FakeStateStore()
        guard = WsAbuseGuard(
            limit_count=1,
            window_seconds=10,
            backoff_seconds=3,
            max_payload_bytes=4096,
            cleanup_interval_seconds=1,
            clock=fake_clock.now,
            state_store=store,
        )

        allowed, _ = guard.evaluate_message(user_id="u1", payload_text="a")
        self.assertTrue(allowed)
        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="b")
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "message_rate_limited")
        self.assertIn("u1", store.data)

        fake_clock.current = 4.0
        allowed, _ = guard.evaluate_message(user_id="u2", payload_text="c")
        self.assertTrue(allowed)
        # cleanup should drop expired backoff state for u1
        self.assertNotIn("u1", store.data)

    def test_scope_key_isolated_from_user_id(self) -> None:
        fake_clock = _FakeClock()
        guard = WsAbuseGuard(
            limit_count=1,
            window_seconds=10,
            backoff_seconds=3,
            max_payload_bytes=4096,
            cleanup_interval_seconds=1,
            clock=fake_clock.now,
        )

        allowed, _ = guard.evaluate_message(
            user_id="u1",
            payload_text="a",
            scope_key="user:u1|ip:1.1.1.1",
        )
        self.assertTrue(allowed)

        allowed, violation = guard.evaluate_message(
            user_id="u1",
            payload_text="b",
            scope_key="user:u1|ip:1.1.1.1",
        )
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "message_rate_limited")

        # Different scope key should not be blocked by the first scope.
        allowed, violation = guard.evaluate_message(
            user_id="u1",
            payload_text="c",
            scope_key="user:u1|ip:2.2.2.2",
        )
        self.assertTrue(allowed)
        self.assertIsNone(violation)

    def test_apply_runtime_limits_updates_guard_parameters(self) -> None:
        fake_clock = _FakeClock()
        guard = WsAbuseGuard(
            limit_count=5,
            window_seconds=60,
            backoff_seconds=30,
            max_payload_bytes=1024,
            clock=fake_clock.now,
        )

        guard.apply_runtime_limits(
            limit_count=1,
            window_seconds=10,
            backoff_seconds=2,
            max_payload_bytes=5,
        )
        self.assertEqual(guard.limit_count, 1)
        self.assertEqual(guard.window_seconds, 10)
        self.assertEqual(guard.backoff_seconds, 2)
        self.assertEqual(guard.max_payload_bytes, 5)

        allowed, _ = guard.evaluate_message(user_id="u1", payload_text="ok")
        self.assertTrue(allowed)
        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="again")
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "message_rate_limited")

        allowed, violation = guard.evaluate_message(user_id="u1", payload_text="payload-too-long")
        self.assertFalse(allowed)
        self.assertEqual(violation["reason"], "payload_too_large")


if __name__ == "__main__":
    unittest.main()
