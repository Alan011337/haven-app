# AUTHZ_MATRIX: POST /api/users/notifications/mark-read
# AUTHZ_MATRIX: POST /api/users/notifications/{notification_id}/read
# AUTHZ_MATRIX: POST /api/users/notifications/{notification_id}/retry
# AUTHZ_DENY_MATRIX: POST /api/users/notifications/{notification_id}/read
# AUTHZ_DENY_MATRIX: POST /api/users/notifications/{notification_id}/retry
# READ_AUTHZ_MATRIX: GET /api/users/notifications
# READ_AUTHZ_MATRIX: GET /api/users/notifications/stats

import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.notification_event import (  # noqa: E402
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from app.models.user import User  # noqa: E402


class NotificationAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        self.current_user_id = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id is not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(email="notify-a@example.com", full_name="Notify A", hashed_password="hashed")
            user_b = User(email="notify-b@example.com", full_name="Notify B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)

            event_a = NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.FAILED,
                receiver_user_id=user_a.id,
                sender_user_id=user_b.id,
                receiver_email=user_a.email,
                dedupe_key="notify-a-failed",
                is_read=False,
                error_message="send_failed",
            )
            event_b = NotificationEvent(
                action_type=NotificationActionType.JOURNAL,
                status=NotificationDeliveryStatus.FAILED,
                receiver_user_id=user_b.id,
                sender_user_id=user_a.id,
                receiver_email=user_b.email,
                dedupe_key="notify-b-failed",
                is_read=False,
                error_message="send_failed",
            )
            session.add(event_a)
            session.add(event_b)
            session.commit()
            session.refresh(event_a)
            session.refresh(event_b)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.event_a_id = event_a.id
            self.event_b_id = event_b.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_list_notifications_only_returns_current_user_events(self) -> None:
        response = self.client.get("/api/users/notifications")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], str(self.event_a_id))

    def test_stats_only_count_current_user_events(self) -> None:
        response = self.client.get("/api/users/notifications/stats")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["failed_count"], 1)
        self.assertEqual(payload["journal_count"], 0)
        self.assertEqual(payload["card_count"], 1)

    def test_mark_read_updates_only_current_user_rows(self) -> None:
        response = self.client.post("/api/users/notifications/mark-read")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)

        with Session(self.engine) as session:
            my_event = session.get(NotificationEvent, self.event_a_id)
            other_event = session.get(NotificationEvent, self.event_b_id)
            self.assertIsNotNone(my_event)
            self.assertIsNotNone(other_event)
            assert my_event is not None
            assert other_event is not None
            self.assertTrue(my_event.is_read)
            self.assertFalse(other_event.is_read)

    def test_mark_single_read_rejects_other_user_event(self) -> None:
        response = self.client.post(f"/api/users/notifications/{self.event_b_id}/read")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Notification not found")

    def test_mark_single_read_updates_owner_event_only(self) -> None:
        response = self.client.post(f"/api/users/notifications/{self.event_a_id}/read")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)

        with Session(self.engine) as session:
            my_event = session.get(NotificationEvent, self.event_a_id)
            other_event = session.get(NotificationEvent, self.event_b_id)
            self.assertIsNotNone(my_event)
            self.assertIsNotNone(other_event)
            assert my_event is not None
            assert other_event is not None
            self.assertTrue(my_event.is_read)
            self.assertFalse(other_event.is_read)

    def test_retry_rejects_other_user_event_before_provider_check(self) -> None:
        with patch("app.api.routers.users.is_email_notification_enabled", return_value=False):
            response = self.client.post(f"/api/users/notifications/{self.event_b_id}/retry")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Notification not found")

    def test_retry_owner_event_returns_503_when_provider_missing(self) -> None:
        with patch("app.api.routers.users.is_email_notification_enabled", return_value=False):
            response = self.client.post(f"/api/users/notifications/{self.event_a_id}/retry")
        self.assertEqual(response.status_code, 503)

    def test_retry_owner_event_rejects_non_retryable_status(self) -> None:
        with Session(self.engine) as session:
            owner_event = session.get(NotificationEvent, self.event_a_id)
            self.assertIsNotNone(owner_event)
            assert owner_event is not None
            owner_event.status = NotificationDeliveryStatus.SENT
            session.add(owner_event)
            session.commit()

        with patch("app.api.routers.users.is_email_notification_enabled", return_value=True):
            response = self.client.post(f"/api/users/notifications/{self.event_a_id}/retry")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Only FAILED or THROTTLED", response.json()["detail"])

    def test_notification_list_emits_observability_log(self) -> None:
        with patch("app.api.routers.users.logger.info") as mock_info:
            response = self.client.get("/api/users/notifications", params={"limit": 20, "offset": 0})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_info.call_count, 1)
        args = mock_info.call_args.args
        self.assertIn("notification_metrics", args[0])
        self.assertEqual(args[1], "notifications_list")
        self.assertEqual(args[2], self.user_a_id)
        self.assertFalse(args[3])  # unread_only
        self.assertIsNone(args[4])  # action_type
        self.assertIsNone(args[5])  # status
        self.assertIsNone(args[6])  # error_reason
        self.assertEqual(args[7], 20)  # limit
        self.assertEqual(args[8], 0)  # offset
        self.assertIsNone(args[9])  # window_days
        self.assertEqual(args[10], 1)  # result_count
        self.assertIsNone(args[11])  # updated
        self.assertIsInstance(args[12], int)  # duration_ms

    def test_notification_stats_emits_observability_log(self) -> None:
        with patch("app.api.routers.users.logger.info") as mock_info:
            response = self.client.get("/api/users/notifications/stats", params={"window_days": 7})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_info.call_count, 1)
        args = mock_info.call_args.args
        self.assertIn("notification_metrics", args[0])
        self.assertEqual(args[1], "notifications_stats")
        self.assertEqual(args[2], self.user_a_id)
        self.assertFalse(args[3])  # unread_only
        self.assertIsNone(args[4])  # action_type
        self.assertIsNone(args[5])  # status
        self.assertIsNone(args[6])  # error_reason
        self.assertIsNone(args[7])  # limit
        self.assertIsNone(args[8])  # offset
        self.assertEqual(args[9], 7)  # window_days
        self.assertEqual(args[10], 1)  # result_count
        self.assertIsNone(args[11])  # updated
        self.assertIsInstance(args[12], int)  # duration_ms

    def test_notification_mark_read_emits_observability_log(self) -> None:
        with patch("app.api.routers.users.logger.info") as mock_info:
            response = self.client.post("/api/users/notifications/mark-read")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_info.call_count, 1)
        args = mock_info.call_args.args
        self.assertIn("notification_metrics", args[0])
        self.assertEqual(args[1], "notifications_mark_read")
        self.assertEqual(args[2], self.user_a_id)
        self.assertFalse(args[3])  # unread_only
        self.assertIsNone(args[4])  # action_type
        self.assertIsNone(args[5])  # status
        self.assertIsNone(args[6])  # error_reason
        self.assertIsNone(args[7])  # limit
        self.assertIsNone(args[8])  # offset
        self.assertIsNone(args[9])  # window_days
        self.assertIsNone(args[10])  # result_count
        self.assertEqual(args[11], 1)  # updated
        self.assertIsInstance(args[12], int)  # duration_ms


if __name__ == "__main__":
    unittest.main()
