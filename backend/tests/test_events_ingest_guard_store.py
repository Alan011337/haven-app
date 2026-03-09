from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services import events_log  # noqa: E402


class _FakeRedisGuardStore:
    def __init__(self, *, allowed: bool = True, retry_after: int = 0) -> None:
        self.allowed = allowed
        self.retry_after = retry_after
        self.calls: list[dict[str, int | str]] = []

    def allow_and_record_sliding_window(
        self,
        *,
        key: str,
        limit_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        self.calls.append(
            {
                "key": key,
                "limit_count": limit_count,
                "window_seconds": window_seconds,
            }
        )
        return self.allowed, self.retry_after


class EventsIngestGuardStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        events_log.reset_core_loop_ingest_guard_for_tests()
        self.user_id = uuid.uuid4()
        self.original_backend = settings.EVENTS_LOG_INGEST_STORE_BACKEND
        self.original_limit = settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT
        self.original_window = settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS

    def tearDown(self) -> None:
        settings.EVENTS_LOG_INGEST_STORE_BACKEND = self.original_backend
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT = self.original_limit
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS = self.original_window
        events_log.reset_core_loop_ingest_guard_for_tests()

    def test_memory_backend_enforces_user_rate_limit(self) -> None:
        settings.EVENTS_LOG_INGEST_STORE_BACKEND = "memory"
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT = 1
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS = 60

        first_allowed, first_retry_after = events_log.allow_core_loop_event_ingest(
            user_id=self.user_id,
            event_name="daily_sync_submitted",
        )
        second_allowed, second_retry_after = events_log.allow_core_loop_event_ingest(
            user_id=self.user_id,
            event_name="daily_card_revealed",
        )

        state = events_log.get_core_loop_ingest_guard_state()
        self.assertTrue(first_allowed)
        self.assertEqual(first_retry_after, 0)
        self.assertFalse(second_allowed)
        self.assertGreaterEqual(second_retry_after, 1)
        self.assertEqual(state.get("configured_backend"), "memory")
        self.assertEqual(state.get("active_backend"), "memory")
        self.assertEqual(state.get("redis_degraded_mode"), False)

    def test_redis_backend_uses_shared_store_when_available(self) -> None:
        settings.EVENTS_LOG_INGEST_STORE_BACKEND = "redis"
        fake_store = _FakeRedisGuardStore(allowed=True, retry_after=0)

        with patch.object(events_log, "_get_redis_ingest_guard_store", return_value=fake_store):
            allowed, retry_after = events_log.allow_core_loop_event_ingest(
                user_id=self.user_id,
                event_name="daily_sync_submitted",
            )

        state = events_log.get_core_loop_ingest_guard_state()
        self.assertTrue(allowed)
        self.assertEqual(retry_after, 0)
        self.assertEqual(len(fake_store.calls), 1)
        self.assertEqual(state.get("configured_backend"), "redis")
        self.assertEqual(state.get("active_backend"), "redis")
        self.assertEqual(state.get("redis_degraded_mode"), False)

    def test_redis_backend_falls_back_to_memory_when_store_unavailable(self) -> None:
        settings.EVENTS_LOG_INGEST_STORE_BACKEND = "redis"
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT = 1
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS = 60

        with patch.object(
            events_log,
            "_get_redis_ingest_guard_store",
            side_effect=RuntimeError("redis unavailable"),
        ):
            first_allowed, _ = events_log.allow_core_loop_event_ingest(
                user_id=self.user_id,
                event_name="daily_sync_submitted",
            )
            second_allowed, _ = events_log.allow_core_loop_event_ingest(
                user_id=self.user_id,
                event_name="daily_card_revealed",
            )

        state = events_log.get_core_loop_ingest_guard_state()
        self.assertTrue(first_allowed)
        self.assertFalse(second_allowed)
        self.assertEqual(state.get("configured_backend"), "redis")
        self.assertEqual(state.get("active_backend"), "memory")
        self.assertEqual(state.get("redis_degraded_mode"), True)


if __name__ == "__main__":
    unittest.main()
