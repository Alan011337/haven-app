import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel import select

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


class NotificationApiTests(unittest.TestCase):
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
            self.user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            self.user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
            self.user_a_email = self.user_a.email

            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.JOURNAL,
                    status=NotificationDeliveryStatus.SENT,
                    receiver_user_id=self.user_a_id,
                    sender_user_id=self.user_b_id,
                    receiver_email=self.user_a_email,
                    dedupe_key="journal-1",
                    is_read=False,
                )
            )
            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.CARD,
                    status=NotificationDeliveryStatus.QUEUED,
                    receiver_user_id=self.user_a_id,
                    sender_user_id=self.user_b_id,
                    receiver_email=self.user_a_email,
                    dedupe_key="card-1",
                    is_read=False,
                )
            )
            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.CARD,
                    status=NotificationDeliveryStatus.FAILED,
                    receiver_user_id=self.user_a_id,
                    sender_user_id=self.user_b_id,
                    receiver_email=self.user_a_email,
                    dedupe_key="card-2",
                    is_read=False,
                    error_message="retry_exhausted",
                )
            )
            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.CARD,
                    status=NotificationDeliveryStatus.THROTTLED,
                    receiver_user_id=self.user_a_id,
                    sender_user_id=self.user_b_id,
                    receiver_email=self.user_a_email,
                    dedupe_key="card-3",
                    is_read=True,
                )
            )
            user_b_failed_notification = NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.FAILED,
                receiver_user_id=self.user_b_id,
                sender_user_id=self.user_a_id,
                receiver_email=self.user_b.email,
                dedupe_key="card-b-1",
                is_read=False,
                error_message="retry_exhausted",
            )
            session.add(user_b_failed_notification)
            session.commit()
            session.refresh(user_b_failed_notification)
            self.user_b_failed_notification_id = user_b_failed_notification.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_partner_status_includes_unread_count(self) -> None:
        response = self.client.get("/api/users/partner-status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["unread_notification_count"], 3)

    def test_mark_read_by_action_type(self) -> None:
        response = self.client.post(
            "/api/users/notifications/mark-read",
            params={"action_type": "journal"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)

        with Session(self.engine) as session:
            rows = session.exec(select(NotificationEvent)).all()
            journal_row = next(item for item in rows if item.action_type == NotificationActionType.JOURNAL)
            card_row = next(item for item in rows if item.action_type == NotificationActionType.CARD)
            self.assertTrue(journal_row.is_read)
            self.assertIsNotNone(journal_row.read_at)
            self.assertFalse(card_row.is_read)

    def test_list_unread_only(self) -> None:
        response = self.client.get("/api/users/notifications", params={"unread_only": True})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 3)

    def test_list_notifications_filter_action_type(self) -> None:
        response = self.client.get("/api/users/notifications", params={"action_type": "CARD"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 3)
        self.assertTrue(all(item["action_type"] == "CARD" for item in payload))

    def test_list_notifications_filter_status(self) -> None:
        response = self.client.get("/api/users/notifications", params={"status": "FAILED"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["status"], "FAILED")

    def test_list_notifications_filter_error_reason(self) -> None:
        response = self.client.get(
            "/api/users/notifications",
            params={"status": "FAILED", "error_reason": "retry_exhaust"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["error_message"], "retry_exhausted")

    def test_notification_stats_summary(self) -> None:
        response = self.client.get("/api/users/notifications/stats")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 4)
        self.assertEqual(payload["unread_count"], 3)
        self.assertEqual(payload["queued_count"], 1)
        self.assertEqual(payload["sent_count"], 1)
        self.assertEqual(payload["failed_count"], 1)
        self.assertEqual(payload["throttled_count"], 1)
        self.assertEqual(payload["journal_count"], 1)
        self.assertEqual(payload["card_count"], 3)
        self.assertEqual(payload["recent_24h_count"], 4)
        self.assertEqual(payload["recent_24h_failed_count"], 1)
        self.assertEqual(payload["window_days"], 7)
        self.assertEqual(payload["window_total_count"], 4)
        self.assertEqual(payload["window_sent_count"], 1)
        self.assertEqual(payload["window_failed_count"], 1)
        self.assertEqual(payload["window_throttled_count"], 1)
        self.assertEqual(payload["window_queued_count"], 1)
        self.assertEqual(len(payload["window_daily"]), 7)
        self.assertEqual(sum(item["total_count"] for item in payload["window_daily"]), 4)
        self.assertEqual(payload["window_top_failure_reasons"][0]["reason"], "retry_exhausted")
        self.assertEqual(payload["window_top_failure_reasons"][0]["count"], 1)
        self.assertIsNotNone(payload["last_event_at"])

    def test_notification_stats_filter_action_type(self) -> None:
        response = self.client.get("/api/users/notifications/stats", params={"action_type": "CARD"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 3)
        self.assertEqual(payload["unread_count"], 2)
        self.assertEqual(payload["journal_count"], 0)
        self.assertEqual(payload["card_count"], 3)
        self.assertEqual(payload["window_total_count"], 3)

    def test_notification_stats_filter_unread_only(self) -> None:
        response = self.client.get("/api/users/notifications/stats", params={"unread_only": True})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 3)
        self.assertEqual(payload["unread_count"], 3)
        self.assertEqual(payload["throttled_count"], 0)
        self.assertEqual(payload["window_total_count"], 3)

    def test_notification_stats_filter_status_and_error_reason(self) -> None:
        response = self.client.get(
            "/api/users/notifications/stats",
            params={"status": "FAILED", "error_reason": "retry_exhaust"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["failed_count"], 1)
        self.assertEqual(payload["window_total_count"], 1)
        self.assertEqual(len(payload["window_top_failure_reasons"]), 1)
        self.assertEqual(payload["window_top_failure_reasons"][0]["reason"], "retry_exhausted")

    def test_notification_stats_supports_window_days_query(self) -> None:
        response = self.client.get("/api/users/notifications/stats", params={"window_days": 1})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["window_days"], 1)
        self.assertEqual(len(payload["window_daily"]), 1)
        self.assertEqual(payload["window_total_count"], 4)

    def test_notification_stats_rejects_invalid_window_days(self) -> None:
        response = self.client.get("/api/users/notifications/stats", params={"window_days": 0})
        self.assertEqual(response.status_code, 422)

    def test_notification_stats_rejects_invalid_status(self) -> None:
        response = self.client.get("/api/users/notifications/stats", params={"status": "BROKEN"})
        self.assertEqual(response.status_code, 400)

    def test_notification_stats_uses_unknown_for_empty_failure_reason(self) -> None:
        with Session(self.engine) as session:
            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.CARD,
                    status=NotificationDeliveryStatus.FAILED,
                    receiver_user_id=self.user_a_id,
                    sender_user_id=self.user_b_id,
                    receiver_email=self.user_a_email,
                    dedupe_key="card-4",
                    is_read=False,
                    error_message=None,
                )
            )
            session.commit()

        response = self.client.get("/api/users/notifications/stats", params={"window_days": 7})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        reasons = {item["reason"]: item["count"] for item in payload["window_top_failure_reasons"]}
        self.assertEqual(reasons.get("unknown"), 1)

    def test_mark_single_notification_read(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(NotificationEvent).where(NotificationEvent.action_type == NotificationActionType.CARD)
            ).first()
            self.assertIsNotNone(target)
            target_uuid = target.id
            target_id = str(target.id)

        response = self.client.post(f"/api/users/notifications/{target_id}/read")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)

        with Session(self.engine) as session:
            updated = session.get(NotificationEvent, target_uuid)
            self.assertIsNotNone(updated)
            self.assertTrue(updated.is_read)
            self.assertIsNotNone(updated.read_at)

    def test_mark_single_notification_read_rejects_other_users_notification(self) -> None:
        response = self.client.post(f"/api/users/notifications/{self.user_b_failed_notification_id}/read")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Notification not found")

    def test_retry_failed_notification(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(NotificationEvent).where(
                    NotificationEvent.status == NotificationDeliveryStatus.FAILED,
                    NotificationEvent.receiver_user_id == self.user_a_id,
                )
            ).first()
            self.assertIsNotNone(target)
            target_id = str(target.id)

        with patch("app.api.routers.users.queue_partner_notification") as mock_queue:
            with patch("app.api.routers.users.is_email_notification_enabled", return_value=True):
                response = self.client.post(f"/api/users/notifications/{target_id}/retry")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["queued"])
            self.assertEqual(mock_queue.call_count, 1)
            kwargs = mock_queue.call_args.kwargs
            self.assertEqual(kwargs["action_type"], "card")
            self.assertEqual(kwargs["dedupe_key"], "card-2")
            self.assertTrue(kwargs["bypass_dedupe_cooldown"])

    def test_retry_rejects_other_users_notification(self) -> None:
        with patch("app.api.routers.users.is_email_notification_enabled", return_value=True):
            response = self.client.post(f"/api/users/notifications/{self.user_b_failed_notification_id}/retry")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Notification not found")

    def test_retry_throttled_notification_bypasses_dedupe_cooldown(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(NotificationEvent).where(
                    NotificationEvent.status == NotificationDeliveryStatus.THROTTLED
                )
            ).first()
            self.assertIsNotNone(target)
            target_id = str(target.id)

        with patch("app.api.routers.users.queue_partner_notification") as mock_queue:
            with patch("app.api.routers.users.is_email_notification_enabled", return_value=True):
                response = self.client.post(f"/api/users/notifications/{target_id}/retry")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["queued"])
            kwargs = mock_queue.call_args.kwargs
            self.assertEqual(kwargs["dedupe_key"], "card-3")
            self.assertTrue(kwargs["bypass_dedupe_cooldown"])

    def test_retry_rejects_when_email_provider_unavailable(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(NotificationEvent).where(
                    NotificationEvent.status == NotificationDeliveryStatus.FAILED,
                    NotificationEvent.receiver_user_id == self.user_a_id,
                )
            ).first()
            self.assertIsNotNone(target)
            target_id = str(target.id)

        with patch("app.api.routers.users.is_email_notification_enabled", return_value=False):
            response = self.client.post(f"/api/users/notifications/{target_id}/retry")
        self.assertEqual(response.status_code, 503)

    def test_retry_rejects_sent_notification(self) -> None:
        with Session(self.engine) as session:
            target = session.exec(
                select(NotificationEvent).where(
                    NotificationEvent.status == NotificationDeliveryStatus.SENT
                )
            ).first()
            self.assertIsNotNone(target)
            target_id = str(target.id)

        with patch("app.api.routers.users.is_email_notification_enabled", return_value=True):
            response = self.client.post(f"/api/users/notifications/{target_id}/retry")
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
