import json
import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from starlette.websockets import WebSocketDisconnect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import main as main_module  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402
from app.services.ws_abuse_guard import WsAbuseGuard  # noqa: E402
from app.services.ws_runtime_metrics import WsRuntimeMetrics  # noqa: E402


class WebSocketAuthGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            self.user = User(
                email="ws-auth@example.com",
                full_name="WS Auth",
                hashed_password="hashed",
            )
            session.add(self.user)
            session.commit()
            session.refresh(self.user)
            self.user_id = self.user.id

        self.metrics = WsRuntimeMetrics()
        self.ws_guard = WsAbuseGuard(
            limit_count=settings.WS_MESSAGE_RATE_LIMIT_COUNT,
            window_seconds=settings.WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS,
            backoff_seconds=settings.WS_MESSAGE_BACKOFF_SECONDS,
            max_payload_bytes=settings.WS_MAX_PAYLOAD_BYTES,
        )

        self.engine_patch = patch.object(main_module, "engine", self.engine)
        self.metrics_patch = patch.object(main_module, "ws_runtime_metrics", self.metrics)
        self.guard_patch = patch.object(main_module, "ws_abuse_guard", self.ws_guard)
        self.engine_patch.start()
        self.metrics_patch.start()
        self.guard_patch.start()
        reset_rate_limit_state_for_tests()

        main_module.manager.active_connections.clear()
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.client.close()
        main_module.manager.active_connections.clear()
        self.guard_patch.stop()
        self.metrics_patch.stop()
        self.engine_patch.stop()
        self.engine.dispose()

    def _token(self, *, sub: str, expires_delta: timedelta, secret: str | None = None) -> str:
        payload = {
            "sub": sub,
            "exp": utcnow() + expires_delta,
        }
        return jwt.encode(
            payload,
            secret or settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    def _expect_disconnect_code(self, path: str) -> int:
        with self.client.websocket_connect(path) as ws:
            with self.assertRaises(WebSocketDisconnect) as ctx:
                ws.receive_text()
        return int(ctx.exception.code)

    # ----------------------------------------------------------
    # Helper: send first-message auth and expect disconnection
    # ----------------------------------------------------------
    def _auth_and_expect_disconnect(self, user_id, token: str) -> int:
        """Connect, send first-message auth, expect server to close."""
        with self.assertRaises(WebSocketDisconnect) as ctx:
            with self.client.websocket_connect(f"/ws/{user_id}") as ws:
                ws.send_text(json.dumps({"type": "auth", "token": token}))
                ws.receive_text()  # should raise WebSocketDisconnect
        return int(ctx.exception.code)

    # ----------------------------------------------------------
    # First-message auth tests (new secure path)
    # ----------------------------------------------------------
    def test_rejects_no_auth_message(self) -> None:
        """Client connects and sends non-auth first message."""
        with self.client.websocket_connect(f"/ws/{self.user_id}") as ws:
            ws.send_text("ping")
            with self.assertRaises(WebSocketDisconnect) as ctx:
                ws.receive_text()
        self.assertEqual(int(ctx.exception.code), 1008)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_missing_token"), 1)

    def test_invalid_user_id_log_does_not_include_raw_value(self) -> None:
        raw_user_id = "not-a-uuid-super-secret"
        with self.assertLogs(main_module.logger.name, level="WARNING") as captured:
            with self.assertRaises(WebSocketDisconnect) as ctx:
                with self.client.websocket_connect(f"/ws/{raw_user_id}"):
                    pass
        self.assertEqual(int(ctx.exception.code), 1008)
        merged = "\n".join(captured.output)
        self.assertIn("invalid_user_id", merged)
        self.assertNotIn(raw_user_id, merged)

    def test_rejects_expired_token_first_msg(self) -> None:
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=-1))
        code = self._auth_and_expect_disconnect(self.user_id, token)
        self.assertEqual(code, 1008)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_invalid_token"), 1)

    def test_rejects_forged_token_first_msg(self) -> None:
        token = self._token(
            sub=str(self.user_id),
            expires_delta=timedelta(minutes=5),
            secret="wrong-secret",
        )
        code = self._auth_and_expect_disconnect(self.user_id, token)
        self.assertEqual(code, 1008)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_invalid_token"), 1)

    def test_rejects_subject_mismatch_first_msg(self) -> None:
        other_user_id = uuid.uuid4()
        token = self._token(sub=str(other_user_id), expires_delta=timedelta(minutes=5))
        code = self._auth_and_expect_disconnect(self.user_id, token)
        self.assertEqual(code, 1008)

    def test_rejects_nonexistent_user_first_msg(self) -> None:
        missing_user_id = uuid.uuid4()
        token = self._token(sub=str(missing_user_id), expires_delta=timedelta(minutes=5))
        code = self._auth_and_expect_disconnect(missing_user_id, token)
        self.assertEqual(code, 1008)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_user_not_found"), 1)

    def test_accepts_first_msg_auth_and_ping(self) -> None:
        """New path: token sent as first message, then ping/pong works."""
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=5))
        with self.client.websocket_connect(f"/ws/{self.user_id}") as ws:
            ws.send_text(json.dumps({"type": "auth", "token": token}))
            ws.send_text("ping")
            self.assertEqual(ws.receive_text(), "pong")

        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_accepted"), 1)
        self.assertEqual(main_module.manager.connection_count(str(self.user_id)), 0)

    # ----------------------------------------------------------
    # Legacy query-string token tests (backward compatibility)
    # ----------------------------------------------------------
    def test_legacy_rejects_expired_token(self) -> None:
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=-1))
        code = self._expect_disconnect_code(f"/ws/{self.user_id}?token={token}")
        self.assertEqual(code, 1008)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_invalid_token"), 1)

    def test_legacy_rejects_forged_token_signature(self) -> None:
        token = self._token(
            sub=str(self.user_id),
            expires_delta=timedelta(minutes=5),
            secret="wrong-secret",
        )
        code = self._expect_disconnect_code(f"/ws/{self.user_id}?token={token}")
        self.assertEqual(code, 1008)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_invalid_token"), 1)

    def test_legacy_rejects_subject_mismatch(self) -> None:
        other_user_id = uuid.uuid4()
        token = self._token(sub=str(other_user_id), expires_delta=timedelta(minutes=5))
        code = self._expect_disconnect_code(f"/ws/{self.user_id}?token={token}")
        self.assertEqual(code, 1008)

    def test_legacy_accepts_valid_token_and_ping(self) -> None:
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=5))
        with self.client.websocket_connect(f"/ws/{self.user_id}?token={token}") as websocket:
            websocket.send_text("ping")
            self.assertEqual(websocket.receive_text(), "pong")

        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_accepted"), 1)
        self.assertEqual(main_module.manager.connection_count(str(self.user_id)), 0)

    def test_logs_websocket_runtime_error_without_exception_message(self) -> None:
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=5))
        secret_fragment = "ws-secret-should-not-log"

        with patch.object(
            main_module.ws_abuse_guard,
            "evaluate_message",
            side_effect=RuntimeError(secret_fragment),
        ):
            with self.assertLogs(main_module.logger.name, level="ERROR") as captured:
                with self.assertRaises(WebSocketDisconnect):
                    with self.client.websocket_connect(f"/ws/{self.user_id}?token={token}") as websocket:
                        websocket.send_text("ping")
                        websocket.receive_text()

        logs = "\n".join(captured.output)
        self.assertIn("WebSocket error: reason=RuntimeError", logs)
        self.assertIn("reason=RuntimeError", logs)
        self.assertNotIn(secret_fragment, logs)
        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_error"), 1)

    def test_rejects_when_connection_attempt_rate_limit_exceeded(self) -> None:
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=5))

        with patch.object(main_module.config.settings, "WS_CONNECTION_RATE_LIMIT_COUNT", 1), patch.object(
            main_module.config.settings,
            "WS_CONNECTION_RATE_LIMIT_WINDOW_SECONDS",
            60,
        ):
            with self.client.websocket_connect(f"/ws/{self.user_id}?token={token}") as websocket:
                websocket.send_text("ping")
                self.assertEqual(websocket.receive_text(), "pong")

            with self.client.websocket_connect(f"/ws/{self.user_id}?token={token}") as websocket:
                rate_limit_payload = websocket.receive_json()
                self.assertEqual(rate_limit_payload.get("event"), "WS_CONNECTION_RATE_LIMITED")
                with self.assertRaises(WebSocketDisconnect) as ctx:
                    websocket.receive_text()
                self.assertEqual(int(ctx.exception.code), 1013)

        snapshot = self.metrics.snapshot()
        self.assertEqual(snapshot["counters"].get("connections_rejected_rate_limited"), 1)

    def test_applies_runtime_message_limit_settings_without_restart(self) -> None:
        token = self._token(sub=str(self.user_id), expires_delta=timedelta(minutes=5))
        with patch.object(main_module.config.settings, "WS_MESSAGE_RATE_LIMIT_COUNT", 1), patch.object(
            main_module.config.settings,
            "WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS",
            60,
        ), patch.object(
            main_module.config.settings,
            "WS_MESSAGE_BACKOFF_SECONDS",
            5,
        ):
            with self.client.websocket_connect(f"/ws/{self.user_id}?token={token}") as websocket:
                websocket.send_text("ping")
                self.assertEqual(websocket.receive_text(), "pong")
                websocket.send_text("ping")
                throttled_payload = websocket.receive_json()
                self.assertEqual(throttled_payload.get("event"), "WS_RATE_LIMITED")
                self.assertEqual(throttled_payload.get("reason"), "message_rate_limited")


if __name__ == "__main__":
    unittest.main()
