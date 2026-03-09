import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.notification_dedupe_store import (  # noqa: E402
    InMemoryNotificationDedupeStore,
    RedisNotificationDedupeStore,
)


class _FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def now(self) -> float:
        return self.current


class _FakeRedisClient:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.set_calls: list[dict[str, object]] = []

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        self.set_calls.append({"key": key, "value": value, "nx": nx, "ex": ex})
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def delete(self, key: str) -> None:
        self.data.pop(key, None)

    def scan_iter(self, *, match: str):
        prefix = match[:-1] if match.endswith("*") else match
        for key in list(self.data.keys()):
            if key.startswith(prefix):
                yield key


class NotificationDedupeStoreTests(unittest.TestCase):
    def test_inmemory_reserve_release_and_cooldown(self) -> None:
        fake_clock = _FakeClock()
        store = InMemoryNotificationDedupeStore(clock=fake_clock.now)

        self.assertTrue(store.reserve(dedupe_key="k1", cooldown_seconds=5))
        self.assertFalse(store.reserve(dedupe_key="k1", cooldown_seconds=5))

        fake_clock.current = 6.0
        self.assertTrue(store.reserve(dedupe_key="k1", cooldown_seconds=5))

        store.release(dedupe_key="k1")
        self.assertTrue(store.reserve(dedupe_key="k1", cooldown_seconds=5))

    def test_redis_reserve_uses_nx_and_ttl(self) -> None:
        fake_client = _FakeRedisClient()
        store = RedisNotificationDedupeStore(
            redis_url="redis://unused",
            key_prefix="test:dedupe",
            client=fake_client,
        )

        self.assertTrue(store.reserve(dedupe_key="k1", cooldown_seconds=2.3))
        self.assertFalse(store.reserve(dedupe_key="k1", cooldown_seconds=2.3))

        first_call = fake_client.set_calls[0]
        self.assertEqual(first_call["key"], "test:dedupe:k1")
        self.assertEqual(first_call["nx"], True)
        self.assertEqual(first_call["ex"], 3)

        store.release(dedupe_key="k1")
        self.assertTrue(store.reserve(dedupe_key="k1", cooldown_seconds=1.1))

    def test_redis_reset_clears_prefixed_keys_only(self) -> None:
        fake_client = _FakeRedisClient()
        store = RedisNotificationDedupeStore(
            redis_url="redis://unused",
            key_prefix="test:dedupe",
            client=fake_client,
        )
        fake_client.data["test:dedupe:k1"] = "1"
        fake_client.data["test:dedupe:k2"] = "1"
        fake_client.data["other:scope:k3"] = "1"

        store.reset()

        self.assertNotIn("test:dedupe:k1", fake_client.data)
        self.assertNotIn("test:dedupe:k2", fake_client.data)
        self.assertIn("other:scope:k3", fake_client.data)


if __name__ == "__main__":
    unittest.main()
