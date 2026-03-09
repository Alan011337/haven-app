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
from app.models.billing import (  # noqa: E402
    BillingCommandLog,
    BillingEntitlementState,
    BillingLedgerEntry,
)
from app.models.user import User  # noqa: E402


class BillingIdempotencyApiTests(unittest.TestCase):
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
            user = User(email="billing@example.com", full_name="Billing", hashed_password="hashed")
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id

        self.current_user_id = self.user_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_state_change_requires_idempotency_key(self) -> None:
        response = self.client.post(
            "/api/billing/state-change",
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Idempotency-Key", response.json()["detail"])

    def test_state_change_rejects_blank_action(self) -> None:
        response = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-key-blank"},
            json={"action": "   ", "target_plan": "PREMIUM"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be blank", response.json()["detail"])

    def test_state_change_rejects_overposted_sensitive_fields(self) -> None:
        response = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-key-overpost"},
            json={
                "action": "UPGRADE",
                "target_plan": "PREMIUM",
                "status": "ACTIVE",
                "idempotency_replayed": True,
            },
        )

        self.assertEqual(response.status_code, 422)
        serialized = str(response.json())
        self.assertIn("status", serialized)
        self.assertIn("idempotency_replayed", serialized)

        with Session(self.engine) as session:
            rows = session.exec(select(BillingCommandLog)).all()
            self.assertEqual(len(rows), 0)

    def test_state_change_replays_same_payload_with_same_key(self) -> None:
        headers = {"Idempotency-Key": "billing-key-1"}
        first = self.client.post(
            "/api/billing/state-change",
            headers=headers,
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertFalse(first_payload["idempotency_replayed"])

        second = self.client.post(
            "/api/billing/state-change",
            headers=headers,
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertTrue(second_payload["idempotency_replayed"])
        self.assertEqual(second_payload["command_id"], first_payload["command_id"])

        with Session(self.engine) as session:
            rows = session.exec(select(BillingCommandLog)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].idempotency_key, "billing-key-1")
            ledgers = session.exec(select(BillingLedgerEntry)).all()
            self.assertEqual(len(ledgers), 1)

    def test_state_change_rejects_key_reuse_with_different_payload(self) -> None:
        headers = {"Idempotency-Key": "billing-key-2"}
        first = self.client.post(
            "/api/billing/state-change",
            headers=headers,
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/billing/state-change",
            headers=headers,
            json={"action": "DOWNGRADE", "target_plan": "FREE"},
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("different payload", second.json()["detail"])

    def test_state_change_updates_entitlement_state_machine(self) -> None:
        trial_response = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-sm-1"},
            json={"action": "START_TRIAL"},
        )
        self.assertEqual(trial_response.status_code, 200)
        self.assertEqual(trial_response.json()["lifecycle_state"], "TRIAL")
        self.assertEqual(trial_response.json()["current_plan"], "FREE")

        active_response = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-sm-2"},
            json={"action": "ACTIVATE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.json()["lifecycle_state"], "ACTIVE")
        self.assertEqual(active_response.json()["current_plan"], "PREMIUM")

        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_id)
            ).first()
            self.assertIsNotNone(entitlement)
            self.assertEqual(entitlement.lifecycle_state, "ACTIVE")
            self.assertEqual(entitlement.current_plan, "PREMIUM")

    def test_state_change_rejects_invalid_transition(self) -> None:
        response = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-sm-invalid"},
            json={"action": "MARK_PAST_DUE"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid transition", response.json()["detail"])

    def test_state_change_supports_account_hold_alias(self) -> None:
        activated = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-hold-activate"},
            json={"action": "ACTIVATE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(activated.json()["lifecycle_state"], "ACTIVE")

        held = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-hold-enter"},
            json={"action": "ENTER_ACCOUNT_HOLD"},
        )
        self.assertEqual(held.status_code, 200)
        payload = held.json()
        self.assertEqual(payload["lifecycle_state"], "GRACE_PERIOD")
        self.assertEqual(payload["current_plan"], "PREMIUM")

    def test_reconciliation_reports_healthy_state(self) -> None:
        created = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-recon-ok"},
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(created.status_code, 200)

        response = self.client.get("/api/billing/reconciliation")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["healthy"])
        self.assertEqual(payload["command_count"], 1)
        self.assertEqual(payload["command_ledger_count"], 1)
        self.assertEqual(payload["missing_command_ledger_count"], 0)
        self.assertEqual(payload["entitlement_state"], "ACTIVE")
        self.assertEqual(payload["entitlement_plan"], "PREMIUM")

    def test_reconciliation_detects_missing_ledger_entry(self) -> None:
        created = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": "billing-recon-missing"},
            json={"action": "UPGRADE", "target_plan": "PREMIUM"},
        )
        self.assertEqual(created.status_code, 200)
        command_id = created.json()["command_id"]

        with Session(self.engine) as session:
            entry = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "COMMAND",
                    BillingLedgerEntry.source_key == f"cmd:{command_id}",
                )
            ).first()
            self.assertIsNotNone(entry)
            session.delete(entry)
            session.commit()

        response = self.client.get("/api/billing/reconciliation")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["healthy"])
        self.assertEqual(payload["command_count"], 1)
        self.assertEqual(payload["command_ledger_count"], 0)
        self.assertEqual(payload["missing_command_ledger_count"], 1)
        self.assertEqual(payload["missing_command_ids"], [command_id])


if __name__ == "__main__":
    unittest.main()
