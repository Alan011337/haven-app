# AUTHZ_MATRIX: POST /api/billing/create-checkout-session
# AUTHZ_MATRIX: POST /api/billing/create-portal-session
# AUTHZ_MATRIX: POST /api/billing/state-change
# READ_AUTHZ_MATRIX: GET /api/billing/reconciliation

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

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import billing  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.billing import BillingCommandLog, BillingLedgerEntry  # noqa: E402
from app.models.user import User  # noqa: E402


class BillingAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
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
            user_a = User(email="billing-a@example.com", full_name="Billing A", hashed_password="hashed")
            user_b = User(email="billing-b@example.com", full_name="Billing B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_state_change_idempotency_key_isolated_per_user(self) -> None:
        shared_key = {"Idempotency-Key": "shared-key-1"}

        self.current_user_id = self.user_a_id
        user_a_first = self.client.post(
            "/api/billing/state-change",
            headers=shared_key,
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(user_a_first.status_code, 200)
        user_a_first_payload = user_a_first.json()
        self.assertFalse(user_a_first_payload["idempotency_replayed"])

        self.current_user_id = self.user_b_id
        user_b_first = self.client.post(
            "/api/billing/state-change",
            headers=shared_key,
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(user_b_first.status_code, 200)
        user_b_first_payload = user_b_first.json()
        self.assertFalse(user_b_first_payload["idempotency_replayed"])
        self.assertNotEqual(user_b_first_payload["command_id"], user_a_first_payload["command_id"])

        user_b_replay = self.client.post(
            "/api/billing/state-change",
            headers=shared_key,
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(user_b_replay.status_code, 200)
        user_b_replay_payload = user_b_replay.json()
        self.assertTrue(user_b_replay_payload["idempotency_replayed"])
        self.assertEqual(user_b_replay_payload["command_id"], user_b_first_payload["command_id"])

        with Session(self.engine) as session:
            shared_key_rows = session.exec(
                select(BillingCommandLog).where(BillingCommandLog.idempotency_key == "shared-key-1")
            ).all()
            self.assertEqual(len(shared_key_rows), 2)
            self.assertEqual({row.user_id for row in shared_key_rows}, {self.user_a_id, self.user_b_id})

    def test_reconciliation_is_scoped_to_current_user(self) -> None:
        self.current_user_id = self.user_a_id
        user_a_change = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "recon-a-1"},
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(user_a_change.status_code, 200)
        user_a_command_id = user_a_change.json()["command_id"]

        self.current_user_id = self.user_b_id
        user_b_change = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "recon-b-1"},
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(user_b_change.status_code, 200)
        user_b_command_id = user_b_change.json()["command_id"]

        with Session(self.engine) as session:
            user_b_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.user_id == self.user_b_id,
                    BillingLedgerEntry.source_type == "COMMAND",
                    BillingLedgerEntry.source_key == f"cmd:{user_b_command_id}",
                )
            ).first()
            self.assertIsNotNone(user_b_ledger)
            assert user_b_ledger is not None
            session.delete(user_b_ledger)
            session.commit()

        self.current_user_id = self.user_a_id
        user_a_recon = self.client.get("/api/billing/reconciliation")
        self.assertEqual(user_a_recon.status_code, 200)
        user_a_payload = user_a_recon.json()
        self.assertEqual(user_a_payload["user_id"], str(self.user_a_id))
        self.assertTrue(user_a_payload["healthy"])
        self.assertEqual(user_a_payload["command_count"], 1)
        self.assertEqual(user_a_payload["missing_command_ledger_count"], 0)
        self.assertEqual(user_a_payload["missing_command_ids"], [])

        self.current_user_id = self.user_b_id
        user_b_recon = self.client.get("/api/billing/reconciliation")
        self.assertEqual(user_b_recon.status_code, 200)
        user_b_payload = user_b_recon.json()
        self.assertEqual(user_b_payload["user_id"], str(self.user_b_id))
        self.assertFalse(user_b_payload["healthy"])
        self.assertEqual(user_b_payload["command_count"], 1)
        self.assertEqual(user_b_payload["missing_command_ledger_count"], 1)
        self.assertEqual(user_b_payload["missing_command_ids"], [user_b_command_id])
        self.assertNotIn(user_a_command_id, user_b_payload["missing_command_ids"])


if __name__ == "__main__":
    unittest.main()
