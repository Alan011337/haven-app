from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core import socket_manager as socket_manager_module  # noqa: E402


class _SlowWebSocket:
    def __init__(self, delay_seconds: float = 0.2) -> None:
        self.delay_seconds = delay_seconds

    async def send_json(self, _message):
        await asyncio.sleep(self.delay_seconds)


class _CaptureWebSocket:
    def __init__(self) -> None:
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class SocketManagerBackpressureTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_timeout_disconnects_slow_consumer(self) -> None:
        manager = socket_manager_module.ConnectionManager()
        manager._refresh_send_limits = lambda: None  # type: ignore[assignment]
        manager._send_timeout_seconds = 0.01
        manager._send_lock_wait_seconds = 0.01
        manager._max_pending_sends_per_user = 1

        await manager.connect("user-1", _SlowWebSocket(delay_seconds=0.1))
        await manager.send_personal_message({"event": "TEST"}, "user-1")
        self.assertNotIn("user-1", manager.active_connections)

    async def test_pending_send_limit_disconnects_when_lock_saturated(self) -> None:
        manager = socket_manager_module.ConnectionManager()
        manager._refresh_send_limits = lambda: None  # type: ignore[assignment]
        manager._send_timeout_seconds = 1.0
        manager._send_lock_wait_seconds = 0.01
        manager._max_pending_sends_per_user = 1

        await manager.connect("user-2", _SlowWebSocket(delay_seconds=0.2))
        first_send = asyncio.create_task(manager.send_personal_message({"event": "A"}, "user-2"))
        await asyncio.sleep(0.01)
        second_send = asyncio.create_task(manager.send_personal_message({"event": "B"}, "user-2"))
        third_send = asyncio.create_task(manager.send_personal_message({"event": "C"}, "user-2"))
        await asyncio.gather(first_send, second_send, third_send)

        self.assertNotIn("user-2", manager.active_connections)

    async def test_send_personal_message_attaches_monotonic_sequence(self) -> None:
        manager = socket_manager_module.ConnectionManager()
        manager._refresh_send_limits = lambda: None  # type: ignore[assignment]
        capture = _CaptureWebSocket()

        await manager.connect("user-seq", capture)
        await manager.send_personal_message({"event": "A"}, "user-seq")
        await manager.send_personal_message({"event": "B"}, "user-seq")

        self.assertEqual(len(capture.messages), 2)
        self.assertEqual(capture.messages[0].get("_ws_seq"), 1)
        self.assertEqual(capture.messages[1].get("_ws_seq"), 2)

    async def test_send_personal_message_keeps_existing_sequence(self) -> None:
        manager = socket_manager_module.ConnectionManager()
        manager._refresh_send_limits = lambda: None  # type: ignore[assignment]
        capture = _CaptureWebSocket()

        await manager.connect("user-seq-fixed", capture)
        await manager.send_personal_message({"event": "A", "_ws_seq": 77}, "user-seq-fixed")

        self.assertEqual(capture.messages[0].get("_ws_seq"), 77)

    def test_masked_user_id_redacts_raw_identifier(self) -> None:
        masked = socket_manager_module.ConnectionManager._masked_user_id("user-sensitive")
        self.assertEqual(len(masked), 10)
        self.assertNotIn("user-sensitive", masked)


if __name__ == "__main__":
    unittest.main()
