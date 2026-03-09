import unittest

from app.services.rate_limit import _SlidingWindowScopeLimiter, logger as rate_limit_logger


class _ReadFailingStore:
    supports_global_cleanup_scan = False

    def load(self, key: str):
        raise RuntimeError("redis://:super-secret@redis.internal:6379/0 read failed")

    def save(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:
        return None

    def delete(self, key: str) -> None:
        return None

    def iter_keys(self):
        return []


class _WriteFailingStore:
    supports_global_cleanup_scan = False

    def load(self, key: str):
        return None

    def save(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:
        raise RuntimeError("redis://:super-secret@redis.internal:6379/0 write failed")

    def delete(self, key: str) -> None:
        return None

    def iter_keys(self):
        return []


class RateLimitStoreFailureLogRedactionTests(unittest.TestCase):
    def test_read_failure_log_masks_secret_url(self) -> None:
        limiter = _SlidingWindowScopeLimiter(state_store=_ReadFailingStore())

        with self.assertLogs(rate_limit_logger, level="WARNING") as captured:
            allowed, _retry_after = limiter.allow_and_record(
                key="test-key",
                limit_count=1,
                window_seconds=60,
            )

        self.assertTrue(allowed)
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)

    def test_write_failure_log_masks_secret_url(self) -> None:
        limiter = _SlidingWindowScopeLimiter(state_store=_WriteFailingStore())

        with self.assertLogs(rate_limit_logger, level="WARNING") as captured:
            allowed, _retry_after = limiter.allow_and_record(
                key="test-key",
                limit_count=1,
                window_seconds=60,
            )

        self.assertTrue(allowed)
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)


if __name__ == "__main__":
    unittest.main()
