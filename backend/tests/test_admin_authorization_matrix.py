# READ_AUTHZ_MATRIX: GET /api/admin/users/{user_id}/status
# READ_AUTHZ_MATRIX: GET /api/admin/audit-events
# READ_AUTHZ_MATRIX: GET /api/admin/moderation/queue
# AUTHZ_MATRIX: POST /api/admin/users/{user_id}/unbind
# AUTHZ_MATRIX: POST /api/admin/moderation/{report_id}/resolve
# AUTHZ_DENY_MATRIX: POST /api/admin/users/{user_id}/unbind
# AUTHZ_DENY_MATRIX: POST /api/admin/moderation/{report_id}/resolve

import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import admin  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.content_report import ContentReport  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.notification_event import NotificationActionType, NotificationDeliveryStatus, NotificationEvent  # noqa: E402
from app.models.user import User  # noqa: E402


class AdminAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(admin.router, prefix="/api/admin")

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

        self._old_admin_enabled = settings.CS_ADMIN_ENABLED
        self._old_admin_allowlist = settings.CS_ADMIN_ALLOWED_EMAILS
        self._old_admin_write_emails = getattr(settings, "CS_ADMIN_WRITE_EMAILS", "")
        settings.CS_ADMIN_ENABLED = True

        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.admin_user = User(email="admin@example.com", full_name="Admin", hashed_password="hashed")
            self.normal_user = User(email="normal@example.com", full_name="Normal", hashed_password="hashed")
            self.target_user = User(email="target@example.com", full_name="Target", hashed_password="hashed")
            self.partner_user = User(email="partner@example.com", full_name="Partner", hashed_password="hashed")
            session.add(self.admin_user)
            session.add(self.normal_user)
            session.add(self.target_user)
            session.add(self.partner_user)
            session.commit()
            session.refresh(self.admin_user)
            session.refresh(self.normal_user)
            session.refresh(self.target_user)
            session.refresh(self.partner_user)

            self.target_user.partner_id = self.partner_user.id
            self.partner_user.partner_id = self.target_user.id
            session.add(self.target_user)
            session.add(self.partner_user)

            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="admin-test-card",
                description="desc",
                question="q",
                difficulty_level=1,
            )
            session.add(card)
            session.commit()
            session.refresh(card)

            session.add(Journal(content="secret-journal", user_id=self.target_user.id))
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=self.target_user.id,
                    content="secret-response",
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.add(
                NotificationEvent(
                    action_type=NotificationActionType.JOURNAL,
                    status=NotificationDeliveryStatus.SENT,
                    receiver_user_id=self.target_user.id,
                    sender_user_id=self.partner_user.id,
                    receiver_email=self.target_user.email,
                    dedupe_key="admin-authz-test",
                )
            )
            session.add(
                AuditEvent(
                    actor_user_id=self.normal_user.id,
                    target_user_id=self.target_user.id,
                    action="USER_READ_DENIED",
                    resource_type="user",
                    resource_id=self.target_user.id,
                    metadata_json='{"secret":"should_not_expose"}',
                )
            )
            self.report_pending = ContentReport(
                resource_type="whisper_wall",
                resource_id="item-1",
                reporter_user_id=self.normal_user.id,
                reason="spam",
                status="pending",
            )
            self.report_pending_2 = ContentReport(
                resource_type="deck_marketplace",
                resource_id="item-2",
                reporter_user_id=self.normal_user.id,
                reason="offensive",
                status="pending",
            )
            session.add(self.report_pending)
            session.add(self.report_pending_2)
            session.commit()
            session.refresh(self.report_pending)
            session.refresh(self.report_pending_2)

            self.admin_user_id = self.admin_user.id
            self.normal_user_id = self.normal_user.id
            self.target_user_id = self.target_user.id
            self.partner_user_id = self.partner_user.id

        settings.CS_ADMIN_ALLOWED_EMAILS = self.admin_user.email
        settings.CS_ADMIN_WRITE_EMAILS = self.admin_user.email
        self.current_user_id = self.admin_user_id

    def tearDown(self) -> None:
        settings.CS_ADMIN_ENABLED = self._old_admin_enabled
        settings.CS_ADMIN_ALLOWED_EMAILS = self._old_admin_allowlist
        if hasattr(settings, "CS_ADMIN_WRITE_EMAILS"):
            settings.CS_ADMIN_WRITE_EMAILS = self._old_admin_write_emails
        self.client.close()
        self.engine.dispose()

    def test_admin_can_read_user_status_without_sensitive_content(self) -> None:
        response = self.client.get(f"/api/admin/users/{self.target_user_id}/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.target_user_id))
        self.assertEqual(payload["partner_id"], str(self.partner_user_id))
        self.assertEqual(payload["journals_count"], 1)
        self.assertEqual(payload["card_responses_count"], 1)
        self.assertNotIn("content", payload)
        self.assertNotIn("metadata_json", payload)

    def test_admin_can_list_audit_events_without_metadata_body(self) -> None:
        response = self.client.get("/api/admin/audit-events?limit=20")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        for row in payload:
            self.assertIn("action", row)
            self.assertIn("resource_type", row)
            self.assertNotIn("metadata_json", row)

    def test_admin_can_unbind_user_pair(self) -> None:
        response = self.client.post(f"/api/admin/users/{self.target_user_id}/unbind")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user_id"], str(self.target_user_id))
        self.assertEqual(payload["previous_partner_id"], str(self.partner_user_id))
        self.assertTrue(payload["unbound_bidirectional"])

        with Session(self.engine) as session:
            target = session.get(User, self.target_user_id)
            partner = session.get(User, self.partner_user_id)
            self.assertIsNotNone(target)
            self.assertIsNotNone(partner)
            assert target is not None
            assert partner is not None
            self.assertIsNone(target.partner_id)
            self.assertIsNone(partner.partner_id)

    def test_non_admin_user_is_denied_admin_endpoints(self) -> None:
        self.current_user_id = self.normal_user_id

        status_response = self.client.get(f"/api/admin/users/{self.target_user_id}/status")
        self.assertEqual(status_response.status_code, 403)
        self.assertEqual(status_response.json()["detail"], "Admin privileges required.")

        unbind_response = self.client.post(f"/api/admin/users/{self.target_user_id}/unbind")
        self.assertEqual(unbind_response.status_code, 403)
        self.assertEqual(unbind_response.json()["detail"], "Admin privileges required.")

        events_response = self.client.get("/api/admin/audit-events")
        self.assertEqual(events_response.status_code, 403)
        self.assertEqual(events_response.json()["detail"], "Admin privileges required.")

    def test_disabled_admin_panel_rejects_even_allowlisted_admin(self) -> None:
        settings.CS_ADMIN_ENABLED = False
        response = self.client.get(f"/api/admin/users/{self.target_user_id}/status")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin panel is disabled.")

    def test_admin_can_resolve_moderation_report(self) -> None:
        response = self.client.post(
            f"/api/admin/moderation/{self.report_pending.id}/resolve",
            json={"status": "dismissed", "resolution_note": "no violation"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.report_pending.id))
        self.assertEqual(payload["status"], "dismissed")

    def test_non_admin_write_user_denied_resolve(self) -> None:
        settings.CS_ADMIN_WRITE_EMAILS = ""
        response = self.client.post(
            f"/api/admin/moderation/{self.report_pending_2.id}/resolve",
            json={"status": "dismissed"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin write privileges required.")
        settings.CS_ADMIN_WRITE_EMAILS = self.admin_user.email


if __name__ == "__main__":
    unittest.main()
