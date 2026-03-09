from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core import socket_manager as socket_manager_module  # noqa: E402


class _FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))


class _CaptureWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)


class RedisSocketManagerFastPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_connection_uses_fast_path_without_publish(self) -> None:
        manager = socket_manager_module.RedisBackedConnectionManager("redis://unit-test")
        fake_redis = _FakeRedis()
        manager._redis = fake_redis  # type: ignore[assignment]
        manager._refresh_send_limits = lambda: None  # type: ignore[assignment]

        ws = _CaptureWebSocket()
        await manager.connect("user-local", ws)
        await manager.send_personal_message({"event": "LOCAL"}, "user-local")

        self.assertEqual(len(ws.messages), 1)
        self.assertEqual(ws.messages[0].get("event"), "LOCAL")
        self.assertEqual(ws.messages[0].get("_ws_seq"), 1)
        self.assertEqual(fake_redis.published, [])

    async def test_remote_connection_publishes_to_redis(self) -> None:
        manager = socket_manager_module.RedisBackedConnectionManager("redis://unit-test")
        fake_redis = _FakeRedis()
        manager._redis = fake_redis  # type: ignore[assignment]
        manager._refresh_send_limits = lambda: None  # type: ignore[assignment]

        await manager.send_personal_message({"event": "REMOTE"}, "user-remote")

        self.assertEqual(len(fake_redis.published), 1)
        channel, payload = fake_redis.published[0]
        self.assertEqual(channel, socket_manager_module.WS_REDIS_CHANNEL)
        self.assertIn("user-remote", payload)


if __name__ == "__main__":
    unittest.main()
