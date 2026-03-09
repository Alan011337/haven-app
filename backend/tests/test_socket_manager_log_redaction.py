import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core import socket_manager as socket_manager_module  # noqa: E402


class _FailingWebSocket:
    async def send_json(self, _message):
        raise RuntimeError("wss://token:super-secret@ws.internal/send failed")


class SocketManagerLogRedactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_personal_message_masks_exception_details(self) -> None:
        manager = socket_manager_module.ConnectionManager()
        manager.active_connections["user-1"] = _FailingWebSocket()

        with self.assertLogs(socket_manager_module.logger, level="WARNING") as captured:
            await manager.send_personal_message({"event": "TEST"}, "user-1")

        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("wss://", merged)
        self.assertNotIn("user-1", manager.active_connections)


if __name__ == "__main__":
    unittest.main()
