import json
import sys
import time
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, col, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import billing, users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.models.audit_event import AuditEvent, AuditEventOutcome  # noqa: E402
from app.models.notification_event import (  # noqa: E402
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from app.models.user import User  # noqa: E402
from app.db.session import get_session  # noqa: E402


class AuditLogBillingNotificationControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")
        app.include_router(billing.router, prefix="/api/billing")

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
            user_a = User(email="audit-bn-a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="audit-bn-b@example.com", full_name="B", hashed_password="hashed")
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
                dedupe_key="audit-bn-a",
                is_read=False,
            )
            event_b = NotificationEvent(
                action_type=NotificationActionType.JOURNAL,
                status=NotificationDeliveryStatus.FAILED,
                receiver_user_id=user_b.id,
                sender_user_id=user_a.id,
                receiver_email=user_b.email,
                dedupe_key="audit-bn-b",
                is_read=False,
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

        self.original_secret = settings.BILLING_STRIPE_WEBHOOK_SECRET
        self.original_tolerance = settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS
        settings.BILLING_STRIPE_WEBHOOK_SECRET = "whsec_test"
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300

    def tearDown(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_SECRET = self.original_secret
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = self.original_tolerance
        self.client.close()
        self.engine.dispose()

    def _latest_audit_event(self, action: str) -> AuditEvent:
        with Session(self.engine) as session:
            row = session.exec(
                select(AuditEvent)
                .where(AuditEvent.action == action)
                .order_by(col(AuditEvent.created_at).desc())
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            return row

    def test_notification_read_denied_records_audit_event(self) -> None:
        response = self.client.post(f"/api/users/notifications/{self.event_b_id}/read")
        self.assertEqual(response.status_code, 404)

        row = self._latest_audit_event("NOTIFICATION_READ_DENIED")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.target_user_id, self.user_b_id)
        self.assertEqual(row.resource_id, self.event_b_id)
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "not_owner_or_missing")

    def test_notification_retry_status_denied_records_audit_event(self) -> None:
        with Session(self.engine) as session:
            event = session.get(NotificationEvent, self.event_a_id)
            self.assertIsNotNone(event)
            assert event is not None
            event.status = NotificationDeliveryStatus.SENT
            session.add(event)
            session.commit()

        with patch("app.api.routers.users.is_email_notification_enabled", return_value=True):
            response = self.client.post(f"/api/users/notifications/{self.event_a_id}/retry")
        self.assertEqual(response.status_code, 409)

        row = self._latest_audit_event("NOTIFICATION_RETRY_DENIED")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.target_user_id, self.user_a_id)
        self.assertEqual(row.resource_id, self.event_a_id)
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "status_not_retryable")
        self.assertIn('"status":"SENT"', row.metadata_json or "")

    def test_billing_state_change_idempotency_mismatch_records_audit_event(self) -> None:
        first = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "audit-bn-billing-1"},
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "audit-bn-billing-1"},
            json={"action": "DOWNGRADE", "target_plan": "FREE"},
        )
        self.assertEqual(second.status_code, 409)

        row = self._latest_audit_event("BILLING_STATE_CHANGE_DENIED")
        self.assertEqual(row.actor_user_id, self.user_a_id)
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "idempotency_payload_mismatch")
        self.assertIn("audit-bn-billing-1", row.metadata_json or "")

    def test_billing_webhook_invalid_signature_records_denied_audit_event(self) -> None:
        payload = {"id": "evt_audit_bn_invalid_sig", "type": "invoice.paid"}
        now_timestamp = int(time.time())
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            json=payload,
            headers={"Stripe-Signature": f"t={now_timestamp},v1=bad"},
        )
        self.assertEqual(response.status_code, 400)

        row = self._latest_audit_event("BILLING_WEBHOOK_DENIED")
        self.assertEqual(row.outcome, AuditEventOutcome.DENIED)
        self.assertEqual(row.reason, "signature_verification_failed")
        self.assertIn("Invalid webhook signature", row.metadata_json or "")

    def test_billing_webhook_missing_secret_records_error_audit_event(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_SECRET = None
        payload_text = json.dumps({"id": "evt_audit_bn_missing_secret", "type": "invoice.paid"})
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers={"Stripe-Signature": "t=1,v1=test", "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 503)

        row = self._latest_audit_event("BILLING_WEBHOOK_ERROR")
        self.assertEqual(row.outcome, AuditEventOutcome.ERROR)
        self.assertEqual(row.reason, "secret_not_configured")


if __name__ == "__main__":
    unittest.main()

