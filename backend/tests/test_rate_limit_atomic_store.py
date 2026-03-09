import unittest

from app.services.abuse_state_store import InMemoryAbuseStateStore
from app.services.rate_limit import (
    _SlidingWindowScopeLimiter,
    _journal_ip_scope_limiter,
    logger as rate_limit_logger,
    reset_rate_limit_state_for_tests,
)


class _AtomicStore:
    supports_global_cleanup_scan = False

    def __init__(self) -> None:
        self.calls = 0

    def allow_and_record_sliding_window(
        self,
        *,
        key: str,
        limit_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        self.calls += 1
        return False, 11

    def load(self, key: str):
        raise AssertionError("load should not be used when atomic path is available")

    def save(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:
        raise AssertionError("save should not be used when atomic path is available")

    def delete(self, key: str) -> None:
        return None

    def iter_keys(self):
        return []


class _FailingAtomicStore:
    supports_global_cleanup_scan = False

    def allow_and_record_sliding_window(
        self,
        *,
        key: str,
        limit_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        raise RuntimeError("redis://:secret-token@redis.internal:6379/0 atomic failure")

    def load(self, key: str):
        return None

    def save(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:
        return None

    def delete(self, key: str) -> None:
        return None

    def iter_keys(self):
        return []


class RateLimitAtomicStoreTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_rate_limit_state_for_tests()

    def test_atomic_store_path_is_used_when_available(self) -> None:
        store = _AtomicStore()
        limiter = _SlidingWindowScopeLimiter(state_store=store)
        allowed, retry_after = limiter.allow_and_record(
            key="k1",
            limit_count=1,
            window_seconds=60,
        )
        self.assertFalse(allowed)
        self.assertEqual(retry_after, 11)
        self.assertEqual(store.calls, 1)

    def test_atomic_store_failure_downgrades_to_memory_and_masks_secret(self) -> None:
        limiter = _SlidingWindowScopeLimiter(state_store=_FailingAtomicStore())
        with self.assertLogs(rate_limit_logger, level="WARNING") as captured:
            allowed_first, _ = limiter.allow_and_record(
                key="k2",
                limit_count=1,
                window_seconds=60,
            )
            allowed_second, retry_after = limiter.allow_and_record(
                key="k2",
                limit_count=1,
                window_seconds=60,
            )

        self.assertTrue(allowed_first)
        self.assertFalse(allowed_second)
        self.assertGreaterEqual(retry_after, 1)
        merged = "\n".join(captured.output)
        self.assertIn("Rate limit atomic store failed", merged)
        self.assertNotIn("secret-token", merged)
        self.assertNotIn("redis://", merged)

    def test_reset_rate_limit_state_replaces_shared_limiter_store(self) -> None:
        allowed_first, _ = _journal_ip_scope_limiter.allow_and_record(
            key="journal:ip:unit-test",
            limit_count=1,
            window_seconds=60,
        )
        allowed_second, retry_after = _journal_ip_scope_limiter.allow_and_record(
            key="journal:ip:unit-test",
            limit_count=1,
            window_seconds=60,
        )

        self.assertTrue(allowed_first)
        self.assertFalse(allowed_second)
        self.assertGreaterEqual(retry_after, 1)

        reset_rate_limit_state_for_tests()

        self.assertIsInstance(_journal_ip_scope_limiter._state_store, InMemoryAbuseStateStore)
        allowed_after_reset, retry_after_after_reset = _journal_ip_scope_limiter.allow_and_record(
            key="journal:ip:unit-test",
            limit_count=1,
            window_seconds=60,
        )
        self.assertTrue(allowed_after_reset)
        self.assertEqual(retry_after_after_reset, 0)


if __name__ == "__main__":
    unittest.main()
