import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.abuse_state_store import InMemoryAbuseStateStore
from app.services.abuse_state_store_factory import (
    create_abuse_state_store,
    logger as abuse_store_logger,
)
from app.services.notification_dedupe_store import (
    InMemoryNotificationDedupeStore,
    create_notification_dedupe_store,
    logger as notification_dedupe_logger,
)


class StateStoreFactoryLogRedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_backend = settings.ABUSE_GUARD_STORE_BACKEND
        self._original_redis_url = settings.ABUSE_GUARD_REDIS_URL
        settings.ABUSE_GUARD_STORE_BACKEND = "redis"
        settings.ABUSE_GUARD_REDIS_URL = "redis://:super-secret@redis.internal:6379/0"

    def tearDown(self) -> None:
        settings.ABUSE_GUARD_STORE_BACKEND = self._original_backend
        settings.ABUSE_GUARD_REDIS_URL = self._original_redis_url

    def test_abuse_state_store_factory_does_not_log_secret_redis_url(self) -> None:
        with patch(
            "app.services.abuse_state_store_factory.RedisAbuseStateStore",
            side_effect=RuntimeError("cannot connect redis://:super-secret@redis.internal:6379/0"),
        ):
            with self.assertLogs(abuse_store_logger, level="WARNING") as captured:
                store = create_abuse_state_store(scope="unit-test-scope")

        self.assertIsInstance(store, InMemoryAbuseStateStore)
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)

    def test_notification_dedupe_factory_does_not_log_secret_redis_url(self) -> None:
        with patch(
            "app.services.notification_dedupe_store.RedisNotificationDedupeStore",
            side_effect=RuntimeError("cannot connect redis://:super-secret@redis.internal:6379/0"),
        ):
            with self.assertLogs(notification_dedupe_logger, level="WARNING") as captured:
                store = create_notification_dedupe_store()

        self.assertIsInstance(store, InMemoryNotificationDedupeStore)
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)


if __name__ == "__main__":
    unittest.main()
