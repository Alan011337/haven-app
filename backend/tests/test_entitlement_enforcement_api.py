import sys
import uuid
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api import journals  # noqa: E402
from app.api.routers import billing, users  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.billing import BillingEntitlementState  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.entitlement_runtime import resolve_user_plan  # noqa: E402


class EntitlementEnforcementApiTests(unittest.TestCase):
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
        app.include_router(journals.router, prefix="/api/journals")

        self.current_user_id: uuid.UUID | None = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            free_user = User(email="free@example.com", hashed_password="hashed")
            paid_user = User(email="paid@example.com", hashed_password="hashed")
            session.add(free_user)
            session.add(paid_user)
            session.commit()
            session.refresh(free_user)
            session.refresh(paid_user)

            session.add(
                BillingEntitlementState(
                    user_id=paid_user.id,
                    lifecycle_state="ACTIVE",
                    current_plan="premium",
                )
            )
            session.commit()

            self.free_user_id = free_user.id
            self.paid_user_id = paid_user.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_resolve_user_plan_uses_billing_entitlement_state_fields(self) -> None:
        with Session(self.engine) as session:
            plan = resolve_user_plan(session=session, user_id=self.paid_user_id)
        self.assertEqual(plan, "premium")

    def test_billing_entitlements_me_endpoint_returns_snapshot(self) -> None:
        self.current_user_id = self.paid_user_id
        response = self.client.get("/api/billing/entitlements/me")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan"], "premium")
        self.assertIn("journals_per_day", payload["quotas"])
        self.assertIn("card_draws_per_day", payload["quotas"])

    def test_data_export_forbidden_for_free_plan(self) -> None:
        self.current_user_id = self.free_user_id
        response = self.client.get("/api/users/me/data-export")
        self.assertEqual(response.status_code, 403)
        self.assertIn("not available", response.json()["detail"].lower())

    def test_data_export_allowed_for_premium_plan(self) -> None:
        self.current_user_id = self.paid_user_id
        response = self.client.get("/api/users/me/data-export")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["id"], str(self.paid_user_id))
        self.assertIn("exported_at", payload)

    def test_journal_create_403_when_quota_exceeded_free_plan(self) -> None:
        """BILL-03: Free plan user receives 403 when journal daily quota exceeded."""
        from unittest.mock import patch

        self.current_user_id = self.free_user_id
        with patch("app.api.journals.consume_daily_quota", return_value=(False, 3)):
            response = self.client.post(
                "/api/journals/",
                json={"content": "超過配額時應被拒絕"},
            )
        self.assertEqual(response.status_code, 403)
        self.assertIn("quota", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
