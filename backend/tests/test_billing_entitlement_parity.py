import hashlib
import hmac
import json
import sys
import time
import unittest
import uuid
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
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.billing import BillingCustomerBinding, BillingEntitlementState  # noqa: E402
from app.models.user import User  # noqa: E402


def _stripe_signature(secret: str, payload_text: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload_text}"
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


class BillingEntitlementParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(billing.router, prefix="/api/billing")

        self.current_user_id: uuid.UUID | None = None

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
            web_user = User(email="parity-web@example.com", full_name="Parity Web", hashed_password="hashed")
            ios_user = User(email="parity-ios@example.com", full_name="Parity iOS", hashed_password="hashed")
            android_user = User(
                email="parity-android@example.com",
                full_name="Parity Android",
                hashed_password="hashed",
            )
            cross_user = User(
                email="parity-cross@example.com",
                full_name="Parity Cross Platform",
                hashed_password="hashed",
            )
            session.add(web_user)
            session.add(ios_user)
            session.add(android_user)
            session.add(cross_user)
            session.commit()
            session.refresh(web_user)
            session.refresh(ios_user)
            session.refresh(android_user)
            session.refresh(cross_user)
            self.users_by_platform = {
                "web": web_user.id,
                "ios": ios_user.id,
                "android": android_user.id,
            }
            self.cross_platform_user_id = cross_user.id

        self.original_secret = settings.BILLING_STRIPE_WEBHOOK_SECRET
        self.original_tolerance = settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS
        self.original_async_mode = settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE
        settings.BILLING_STRIPE_WEBHOOK_SECRET = "whsec_test"
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = False

    def tearDown(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_SECRET = self.original_secret
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = self.original_tolerance
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = self.original_async_mode
        self.client.close()
        self.engine.dispose()

    def _state_change(self, *, user_id: uuid.UUID, key: str, action: str, target_plan: str | None = None) -> None:
        self.current_user_id = user_id
        payload: dict[str, str] = {"action": action}
        if target_plan is not None:
            payload["target_plan"] = target_plan
        response = self.client.post(
            "/api/billing/state-change",
            headers={"Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(response.status_code, 200, response.text)

    def _signed_webhook(self, *, payload: dict, timestamp: int) -> None:
        payload_text = json.dumps(payload, separators=(",", ":"))
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def _get_entitlement(self, *, user_id: uuid.UUID) -> BillingEntitlementState:
        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == user_id)
            ).first()
        self.assertIsNotNone(entitlement)
        assert entitlement is not None
        return entitlement

    def test_state_change_sequence_has_platform_entitlement_parity(self) -> None:
        for platform, user_id in self.users_by_platform.items():
            self._state_change(
                user_id=user_id,
                key=f"parity-{platform}-trial",
                action="START_TRIAL",
            )
            self._state_change(
                user_id=user_id,
                key=f"parity-{platform}-activate",
                action="ACTIVATE",
                target_plan="PREMIUM",
            )
            self._state_change(
                user_id=user_id,
                key=f"parity-{platform}-downgrade",
                action="DOWNGRADE",
                target_plan="FREE",
            )
            self._state_change(
                user_id=user_id,
                key=f"parity-{platform}-grace",
                action="ENTER_GRACE_PERIOD",
            )
            self._state_change(
                user_id=user_id,
                key=f"parity-{platform}-reactivate",
                action="ACTIVATE",
                target_plan="PREMIUM",
            )

        entitlements = {
            platform: self._get_entitlement(user_id=user_id)
            for platform, user_id in self.users_by_platform.items()
        }

        revisions = set()
        for entitlement in entitlements.values():
            self.assertEqual(entitlement.lifecycle_state, "ACTIVE")
            self.assertEqual(entitlement.current_plan, "PREMIUM")
            revisions.add(entitlement.revision)
        self.assertEqual(len(revisions), 1)

    def test_webhook_sequence_has_platform_entitlement_parity(self) -> None:
        timestamp = int(time.time())
        for platform, user_id in self.users_by_platform.items():
            customer_id = f"cus-parity-{platform}"
            base_metadata = {
                "user_id": str(user_id),
                "platform": platform,
            }

            self._signed_webhook(
                payload={
                    "id": f"evt-{platform}-paid",
                    "type": "invoice.paid",
                    "data": {"object": {"customer": customer_id, "metadata": base_metadata}},
                },
                timestamp=timestamp,
            )
            self._signed_webhook(
                payload={
                    "id": f"evt-{platform}-failed",
                    "type": "invoice.payment_failed",
                    "data": {"object": {"customer": customer_id}},
                },
                timestamp=timestamp,
            )
            self._signed_webhook(
                payload={
                    "id": f"evt-{platform}-refund",
                    "type": "charge.refunded",
                    "data": {"object": {"customer": customer_id}},
                },
                timestamp=timestamp,
            )

        entitlements = {
            platform: self._get_entitlement(user_id=user_id)
            for platform, user_id in self.users_by_platform.items()
        }

        revisions = set()
        for entitlement in entitlements.values():
            self.assertEqual(entitlement.lifecycle_state, "CANCELED")
            revisions.add(entitlement.revision)
        self.assertEqual(len(revisions), 1)

    def test_same_user_entitlement_is_consistent_across_web_ios_android_sources(self) -> None:
        user_id = self.cross_platform_user_id
        self._state_change(user_id=user_id, key="same-user-bootstrap-trial", action="START_TRIAL")
        self._state_change(
            user_id=user_id,
            key="same-user-bootstrap-activate",
            action="ACTIVATE",
            target_plan="PREMIUM",
        )

        for platform in ("web", "ios", "android"):
            self._state_change(
                user_id=user_id,
                key=f"same-user-{platform}-past-due",
                action="MARK_PAST_DUE",
            )
            self._state_change(
                user_id=user_id,
                key=f"same-user-{platform}-grace",
                action="ENTER_GRACE_PERIOD",
            )
            self._state_change(
                user_id=user_id,
                key=f"same-user-{platform}-reactivate",
                action="ACTIVATE",
                target_plan="PREMIUM",
            )

            customer_id = f"cus-same-user-{platform}"
            subscription_id = f"sub-same-user-{platform}"
            timestamp = int(time.time())
            self._signed_webhook(
                payload={
                    "id": f"evt-same-user-{platform}-failed",
                    "type": "invoice.payment_failed",
                    "data": {
                        "object": {
                            "customer": customer_id,
                            "subscription": subscription_id,
                            "metadata": {
                                "user_id": str(user_id),
                                "platform": platform,
                            },
                        }
                    },
                },
                timestamp=timestamp,
            )
            self._signed_webhook(
                payload={
                    "id": f"evt-same-user-{platform}-paid",
                    "type": "invoice.paid",
                    "data": {
                        "object": {
                            "customer": customer_id,
                            "subscription": subscription_id,
                        }
                    },
                },
                timestamp=timestamp,
            )

            entitlement = self._get_entitlement(user_id=user_id)
            self.assertEqual(entitlement.lifecycle_state, "ACTIVE")
            self.assertEqual(entitlement.current_plan, "PREMIUM")

        with Session(self.engine) as session:
            bindings = session.exec(
                select(BillingCustomerBinding).where(
                    BillingCustomerBinding.provider == "STRIPE",
                    BillingCustomerBinding.user_id == user_id,
                )
            ).all()
        self.assertEqual(len(bindings), 1)


if __name__ == "__main__":
    unittest.main()
