import sys
import unittest
import uuid
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.user import User  # noqa: E402
from app.services import socket_event_guard as socket_event_guard_module  # noqa: E402


class SocketEventGuardLogRedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            user_a = User(email="guard-a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="guard-b@example.com", full_name="B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_invalid_session_id_log_does_not_include_raw_value(self) -> None:
        secret_like_payload = "session=raw-super-secret"
        with Session(self.engine) as session:
            with self.assertLogs(socket_event_guard_module.logger.name, level="DEBUG") as captured:
                result = socket_event_guard_module.resolve_typing_session_id(
                    session=session,
                    sender_user_id=self.user_a_id,
                    partner_user_id=self.user_b_id,
                    raw_session_id=secret_like_payload,
                )

        self.assertIsNone(result)
        merged = "\n".join(captured.output)
        self.assertIn("invalid_session_id_format", merged)
        self.assertNotIn("raw-super-secret", merged)
        self.assertNotIn(secret_like_payload, merged)

    def test_missing_session_log_does_not_include_target_uuid(self) -> None:
        missing_session_id = uuid.uuid4()
        with Session(self.engine) as session:
            with self.assertLogs(socket_event_guard_module.logger.name, level="DEBUG") as captured:
                result = socket_event_guard_module.resolve_typing_session_id(
                    session=session,
                    sender_user_id=self.user_a_id,
                    partner_user_id=self.user_b_id,
                    raw_session_id=str(missing_session_id),
                )

        self.assertIsNone(result)
        merged = "\n".join(captured.output)
        self.assertIn("session_not_found", merged)
        self.assertNotIn(str(missing_session_id), merged)


if __name__ == "__main__":
    unittest.main()
