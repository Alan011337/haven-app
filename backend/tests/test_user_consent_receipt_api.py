import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routers import users  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402

# AUTHZ_MATRIX: POST /api/users/me/consents


class UserConsentReceiptApiTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limit_state_for_tests()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()
        reset_rate_limit_state_for_tests()

    def test_create_user_rejects_when_age_not_confirmed(self) -> None:
        response = self.client.post(
            "/api/users/",
            json={
                "email": "no-consent@example.com",
                "password": "pw123456",
                "full_name": "No Consent",
                "age_confirmed": False,
                "agreed_to_terms": True,
                "terms_version": "v1.0",
                "privacy_version": "v1.0",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Age confirmation is required.")

    def test_create_user_records_consent_receipt_audit_event(self) -> None:
        response = self.client.post(
            "/api/users/",
            json={
                "email": "consent@example.com",
                "password": "pw123456",
                "full_name": "Consent User",
                "age_confirmed": True,
                "agreed_to_terms": True,
                "terms_version": "v1.0",
                "privacy_version": "v1.0",
            },
        )
        self.assertEqual(response.status_code, 200)
        user_id = response.json()["id"]

        with Session(self.engine) as session:
            events = session.exec(
                select(AuditEvent).where(AuditEvent.action == "USER_CONSENT_ACK")
            ).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsNotNone(event.metadata_json)
        self.assertIn("terms_version", event.metadata_json or "")
        self.assertIn("privacy_version", event.metadata_json or "")
        self.assertEqual(str(event.actor_user_id), user_id)

    def test_create_my_consent_requires_authentication(self) -> None:
        response = self.client.post(
            "/api/users/me/consents",
            json={
                "consent_type": "privacy_policy",
                "policy_version": "1.0.0",
            },
        )
        self.assertIn(response.status_code, {401, 403})


if __name__ == "__main__":
    unittest.main()
