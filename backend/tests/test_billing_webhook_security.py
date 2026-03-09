# AUTHZ_MATRIX: POST /api/billing/webhooks/appstore
# AUTHZ_MATRIX: POST /api/billing/webhooks/googleplay
# AUTHZ_MATRIX: POST /api/billing/webhooks/stripe

import hashlib
import hmac
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
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routers import billing  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.billing import (  # noqa: E402
    BillingCustomerBinding,
    BillingEntitlementState,
    BillingLedgerEntry,
    BillingWebhookReceipt,
)
from app.models.user import User  # noqa: E402


def _stripe_signature(secret: str, payload_text: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload_text}"
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


class BillingWebhookSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(billing.router, prefix="/api/billing")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(email="billing-webhook-a@example.com", full_name="Webhook A", hashed_password="hashed")
            user_b = User(email="billing-webhook-b@example.com", full_name="Webhook B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

        self.original_secret = settings.BILLING_STRIPE_WEBHOOK_SECRET
        self.original_tolerance = settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS
        self.original_async_mode = settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE
        self.original_retry_max_attempts = settings.BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS
        self.original_retry_base_seconds = settings.BILLING_WEBHOOK_RETRY_BASE_SECONDS
        settings.BILLING_STRIPE_WEBHOOK_SECRET = "whsec_test"
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = False
        settings.BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS = 3
        settings.BILLING_WEBHOOK_RETRY_BASE_SECONDS = 30

    def tearDown(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_SECRET = self.original_secret
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = self.original_tolerance
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = self.original_async_mode
        settings.BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS = self.original_retry_max_attempts
        settings.BILLING_WEBHOOK_RETRY_BASE_SECONDS = self.original_retry_base_seconds
        self.client.close()
        self.engine.dispose()

    def test_rejects_missing_signature_header(self) -> None:
        payload = {"id": "evt_missing_sig", "type": "invoice.paid"}
        response = self.client.post("/api/billing/webhooks/stripe", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Stripe-Signature", response.json()["detail"])

    def test_rejects_invalid_signature(self) -> None:
        payload = {"id": "evt_invalid_sig", "type": "invoice.paid"}
        now_timestamp = int(time.time())
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            json=payload,
            headers={"Stripe-Signature": f"t={now_timestamp},v1=bad"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid webhook signature", response.json()["detail"])

    def test_rejects_old_timestamp_signature(self) -> None:
        payload = {"id": "evt_old_ts", "type": "invoice.paid"}
        payload_text = json.dumps(payload)
        old_timestamp = int(time.time()) - 10_000
        signature = _stripe_signature("whsec_test", payload_text, old_timestamp)
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("outside tolerance", response.json()["detail"])

    def test_rejects_webhook_when_secret_not_configured(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_SECRET = ""
        payload = {"id": "evt_secret_missing", "type": "invoice.paid"}
        payload_text = json.dumps(payload, separators=(",", ":"))
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.json()["detail"])

    def test_rejects_signature_with_invalid_timestamp_format(self) -> None:
        payload = {"id": "evt_bad_ts", "type": "invoice.paid"}
        payload_text = json.dumps(payload, separators=(",", ":"))
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers={
                "Stripe-Signature": "t=not-a-number,v1=abc123",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("timestamp", response.json()["detail"])

    def test_rejects_payload_with_invalid_utf8_bytes(self) -> None:
        timestamp = int(time.time())
        payload_bytes = b"\xff\xfe\x00"
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_bytes,
            headers={
                "Stripe-Signature": f"t={timestamp},v1=abc123",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("valid UTF-8", response.json()["detail"])

    def test_rejects_invalid_json_even_when_signature_is_valid(self) -> None:
        payload_text = "not-json"
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid webhook JSON payload", response.json()["detail"])

    def test_accepts_valid_signature_and_replay_safe(self) -> None:
        payload = {"id": "evt_valid_1", "type": "invoice.paid"}
        payload_text = json.dumps(payload, separators=(",", ":"))
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        headers = {"Stripe-Signature": signature, "Content-Type": "application/json"}

        first = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers=headers,
        )
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertFalse(first_payload["replayed"])
        self.assertEqual(first_payload["event_id"], "evt_valid_1")

        second = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers=headers,
        )
        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertTrue(second_payload["replayed"])

        with Session(self.engine) as session:
            rows = session.exec(select(BillingWebhookReceipt)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].provider_event_id, "evt_valid_1")
            ledger_rows = session.exec(select(BillingLedgerEntry)).all()
            self.assertEqual(len(ledger_rows), 1)
            self.assertEqual(ledger_rows[0].source_key, "wh:stripe:evt_valid_1")

    def test_rejects_replay_payload_mismatch_for_same_event_id(self) -> None:
        payload_1 = {"id": "evt_same_id", "type": "invoice.paid"}
        payload_1_text = json.dumps(payload_1, separators=(",", ":"))
        timestamp = int(time.time())
        sig_1 = _stripe_signature("whsec_test", payload_1_text, timestamp)
        headers_1 = {"Stripe-Signature": sig_1, "Content-Type": "application/json"}

        first = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_1_text,
            headers=headers_1,
        )
        self.assertEqual(first.status_code, 200)

        payload_2 = {"id": "evt_same_id", "type": "invoice.payment_failed"}
        payload_2_text = json.dumps(payload_2, separators=(",", ":"))
        sig_2 = _stripe_signature("whsec_test", payload_2_text, timestamp)
        headers_2 = {"Stripe-Signature": sig_2, "Content-Type": "application/json"}

        second = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_2_text,
            headers=headers_2,
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("payload mismatch", second.json()["detail"])

    def test_customer_binding_maps_user_without_metadata_on_followup_webhook(self) -> None:
        bind_payload = {
            "id": "evt_bind_user_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_bound_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        bind_text = json.dumps(bind_payload, separators=(",", ":"))
        bind_ts = int(time.time())
        bind_sig = _stripe_signature("whsec_test", bind_text, bind_ts)
        bind_headers = {"Stripe-Signature": bind_sig, "Content-Type": "application/json"}

        bind_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=bind_text,
            headers=bind_headers,
        )
        self.assertEqual(bind_response.status_code, 200)

        follow_payload = {
            "id": "evt_bind_user_2",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_bound_1"}},
        }
        follow_text = json.dumps(follow_payload, separators=(",", ":"))
        follow_sig = _stripe_signature("whsec_test", follow_text, bind_ts)
        follow_headers = {"Stripe-Signature": follow_sig, "Content-Type": "application/json"}
        follow_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=follow_text,
            headers=follow_headers,
        )
        self.assertEqual(follow_response.status_code, 200)

        with Session(self.engine) as session:
            binding = session.exec(
                select(BillingCustomerBinding).where(
                    BillingCustomerBinding.provider == "STRIPE",
                    BillingCustomerBinding.provider_customer_id == "cus_bound_1",
                )
            ).first()
            self.assertIsNotNone(binding)
            self.assertEqual(binding.user_id, self.user_a_id)
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            self.assertEqual(entitlement.lifecycle_state, "PAST_DUE")

    def test_rejects_webhook_when_binding_user_mismatches_metadata_user(self) -> None:
        bind_payload = {
            "id": "evt_bind_conflict_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_conflict_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        bind_text = json.dumps(bind_payload, separators=(",", ":"))
        timestamp = int(time.time())
        bind_sig = _stripe_signature("whsec_test", bind_text, timestamp)
        bind_headers = {"Stripe-Signature": bind_sig, "Content-Type": "application/json"}
        bind_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=bind_text,
            headers=bind_headers,
        )
        self.assertEqual(bind_response.status_code, 200)

        conflict_payload = {
            "id": "evt_bind_conflict_2",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_conflict_1",
                    "metadata": {"user_id": str(self.user_b_id)},
                }
            },
        }
        conflict_text = json.dumps(conflict_payload, separators=(",", ":"))
        conflict_sig = _stripe_signature("whsec_test", conflict_text, timestamp)
        conflict_headers = {"Stripe-Signature": conflict_sig, "Content-Type": "application/json"}
        conflict_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=conflict_text,
            headers=conflict_headers,
        )
        self.assertEqual(conflict_response.status_code, 409)
        self.assertIn("identity does not match", conflict_response.json()["detail"])

    def test_rejects_webhook_when_customer_and_subscription_map_to_different_users(self) -> None:
        timestamp = int(time.time())

        customer_bind_payload = {
            "id": "evt_dual_bind_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_dual_a",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        customer_bind_text = json.dumps(customer_bind_payload, separators=(",", ":"))
        customer_bind_sig = _stripe_signature("whsec_test", customer_bind_text, timestamp)
        customer_bind_headers = {
            "Stripe-Signature": customer_bind_sig,
            "Content-Type": "application/json",
        }
        customer_bind_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=customer_bind_text,
            headers=customer_bind_headers,
        )
        self.assertEqual(customer_bind_response.status_code, 200)

        subscription_bind_payload = {
            "id": "evt_dual_bind_2",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_dual_b",
                    "metadata": {"user_id": str(self.user_b_id)},
                }
            },
        }
        subscription_bind_text = json.dumps(subscription_bind_payload, separators=(",", ":"))
        subscription_bind_sig = _stripe_signature("whsec_test", subscription_bind_text, timestamp)
        subscription_bind_headers = {
            "Stripe-Signature": subscription_bind_sig,
            "Content-Type": "application/json",
        }
        subscription_bind_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=subscription_bind_text,
            headers=subscription_bind_headers,
        )
        self.assertEqual(subscription_bind_response.status_code, 200)

        conflict_payload = {
            "id": "evt_dual_bind_3",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_dual_a",
                    "subscription": "sub_dual_b",
                }
            },
        }
        conflict_text = json.dumps(conflict_payload, separators=(",", ":"))
        conflict_sig = _stripe_signature("whsec_test", conflict_text, timestamp)
        conflict_headers = {
            "Stripe-Signature": conflict_sig,
            "Content-Type": "application/json",
        }
        conflict_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=conflict_text,
            headers=conflict_headers,
        )
        self.assertEqual(conflict_response.status_code, 409)
        self.assertIn("map to different users", conflict_response.json()["detail"])

    def test_rejects_invoice_paid_transition_from_canceled_state(self) -> None:
        timestamp = int(time.time())
        canceled_payload = {
            "id": "evt_transition_guard_1",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "customer": "cus_transition_guard_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        canceled_text = json.dumps(canceled_payload, separators=(",", ":"))
        canceled_sig = _stripe_signature("whsec_test", canceled_text, timestamp)
        canceled_headers = {
            "Stripe-Signature": canceled_sig,
            "Content-Type": "application/json",
        }
        canceled_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=canceled_text,
            headers=canceled_headers,
        )
        self.assertEqual(canceled_response.status_code, 200)

        invalid_reactivate_payload = {
            "id": "evt_transition_guard_2",
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_transition_guard_1"}},
        }
        invalid_reactivate_text = json.dumps(invalid_reactivate_payload, separators=(",", ":"))
        invalid_reactivate_sig = _stripe_signature(
            "whsec_test", invalid_reactivate_text, timestamp
        )
        invalid_reactivate_headers = {
            "Stripe-Signature": invalid_reactivate_sig,
            "Content-Type": "application/json",
        }
        invalid_reactivate_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=invalid_reactivate_text,
            headers=invalid_reactivate_headers,
        )
        self.assertEqual(invalid_reactivate_response.status_code, 409)
        self.assertIn(
            "Invalid webhook transition",
            invalid_reactivate_response.json()["detail"],
        )

        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            self.assertEqual(entitlement.lifecycle_state, "CANCELED")
            invalid_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_transition_guard_2",
                )
            ).first()
            self.assertIsNone(invalid_ledger)

    def test_allows_invoice_paid_transition_from_past_due_state(self) -> None:
        timestamp = int(time.time())
        failed_payload = {
            "id": "evt_transition_ok_1",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_transition_ok_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        failed_text = json.dumps(failed_payload, separators=(",", ":"))
        failed_sig = _stripe_signature("whsec_test", failed_text, timestamp)
        failed_headers = {
            "Stripe-Signature": failed_sig,
            "Content-Type": "application/json",
        }
        failed_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=failed_text,
            headers=failed_headers,
        )
        self.assertEqual(failed_response.status_code, 200)

        paid_payload = {
            "id": "evt_transition_ok_2",
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_transition_ok_1"}},
        }
        paid_text = json.dumps(paid_payload, separators=(",", ":"))
        paid_sig = _stripe_signature("whsec_test", paid_text, timestamp)
        paid_headers = {
            "Stripe-Signature": paid_sig,
            "Content-Type": "application/json",
        }
        paid_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=paid_text,
            headers=paid_headers,
        )
        self.assertEqual(paid_response.status_code, 200)

        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            self.assertEqual(entitlement.lifecycle_state, "ACTIVE")

    def test_charge_refunded_transitions_active_to_canceled(self) -> None:
        timestamp = int(time.time())
        activate_payload = {
            "id": "evt_refund_guard_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_refund_guard_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        activate_text = json.dumps(activate_payload, separators=(",", ":"))
        activate_sig = _stripe_signature("whsec_test", activate_text, timestamp)
        activate_headers = {
            "Stripe-Signature": activate_sig,
            "Content-Type": "application/json",
        }
        activate_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=activate_text,
            headers=activate_headers,
        )
        self.assertEqual(activate_response.status_code, 200)

        refund_payload = {
            "id": "evt_refund_guard_2",
            "type": "charge.refunded",
            "data": {"object": {"customer": "cus_refund_guard_1"}},
        }
        refund_text = json.dumps(refund_payload, separators=(",", ":"))
        refund_sig = _stripe_signature("whsec_test", refund_text, timestamp)
        refund_headers = {
            "Stripe-Signature": refund_sig,
            "Content-Type": "application/json",
        }
        refund_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=refund_text,
            headers=refund_headers,
        )
        self.assertEqual(refund_response.status_code, 200)

        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            assert entitlement is not None
            self.assertEqual(entitlement.lifecycle_state, "CANCELED")
            refund_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_refund_guard_2",
                )
            ).first()
            self.assertIsNotNone(refund_ledger)
            assert refund_ledger is not None
            self.assertEqual(refund_ledger.action, "charge.refunded")
            self.assertEqual(refund_ledger.next_state, "CANCELED")

    def test_googleplay_account_hold_and_recovered_events(self) -> None:
        timestamp = int(time.time())
        activate_payload = {
            "id": "evt_gp_hold_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_gp_hold_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        activate_text = json.dumps(activate_payload, separators=(",", ":"))
        activate_sig = _stripe_signature("whsec_test", activate_text, timestamp)
        activate_headers = {
            "Stripe-Signature": activate_sig,
            "Content-Type": "application/json",
        }
        activate_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=activate_text,
            headers=activate_headers,
        )
        self.assertEqual(activate_response.status_code, 200)

        on_hold_payload = {
            "id": "evt_gp_hold_2",
            "type": "googleplay.subscription.on_hold",
            "data": {"object": {"customer": "cus_gp_hold_1"}},
        }
        on_hold_text = json.dumps(on_hold_payload, separators=(",", ":"))
        on_hold_sig = _stripe_signature("whsec_test", on_hold_text, timestamp)
        on_hold_headers = {
            "Stripe-Signature": on_hold_sig,
            "Content-Type": "application/json",
        }
        on_hold_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=on_hold_text,
            headers=on_hold_headers,
        )
        self.assertEqual(on_hold_response.status_code, 200)

        recovered_payload = {
            "id": "evt_gp_hold_3",
            "type": "googleplay.subscription.recovered",
            "data": {"object": {"customer": "cus_gp_hold_1"}},
        }
        recovered_text = json.dumps(recovered_payload, separators=(",", ":"))
        recovered_sig = _stripe_signature("whsec_test", recovered_text, timestamp)
        recovered_headers = {
            "Stripe-Signature": recovered_sig,
            "Content-Type": "application/json",
        }
        recovered_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=recovered_text,
            headers=recovered_headers,
        )
        self.assertEqual(recovered_response.status_code, 200)

        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            assert entitlement is not None
            self.assertEqual(entitlement.lifecycle_state, "ACTIVE")
            hold_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_gp_hold_2",
                )
            ).first()
            recover_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_gp_hold_3",
                )
            ).first()
            self.assertIsNotNone(hold_ledger)
            self.assertIsNotNone(recover_ledger)
            assert hold_ledger is not None
            assert recover_ledger is not None
            self.assertEqual(hold_ledger.next_state, "GRACE_PERIOD")
            self.assertEqual(recover_ledger.next_state, "ACTIVE")

    def test_googleplay_account_hold_rejected_from_canceled_state(self) -> None:
        timestamp = int(time.time())
        cancel_payload = {
            "id": "evt_gp_hold_block_1",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "customer": "cus_gp_hold_block_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        cancel_text = json.dumps(cancel_payload, separators=(",", ":"))
        cancel_sig = _stripe_signature("whsec_test", cancel_text, timestamp)
        cancel_headers = {
            "Stripe-Signature": cancel_sig,
            "Content-Type": "application/json",
        }
        cancel_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=cancel_text,
            headers=cancel_headers,
        )
        self.assertEqual(cancel_response.status_code, 200)

        blocked_payload = {
            "id": "evt_gp_hold_block_2",
            "type": "googleplay.subscription.on_hold",
            "data": {"object": {"customer": "cus_gp_hold_block_1"}},
        }
        blocked_text = json.dumps(blocked_payload, separators=(",", ":"))
        blocked_sig = _stripe_signature("whsec_test", blocked_text, timestamp)
        blocked_headers = {
            "Stripe-Signature": blocked_sig,
            "Content-Type": "application/json",
        }
        blocked_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=blocked_text,
            headers=blocked_headers,
        )
        self.assertEqual(blocked_response.status_code, 409)
        self.assertIn("Invalid webhook transition", blocked_response.json()["detail"])

        with Session(self.engine) as session:
            blocked_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_gp_hold_block_2",
                )
            ).first()
            self.assertIsNone(blocked_ledger)

    def test_charge_dispute_created_transitions_active_to_canceled_and_replay_safe(self) -> None:
        timestamp = int(time.time())
        activate_payload = {
            "id": "evt_chargeback_guard_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_chargeback_guard_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        activate_text = json.dumps(activate_payload, separators=(",", ":"))
        activate_sig = _stripe_signature("whsec_test", activate_text, timestamp)
        activate_headers = {
            "Stripe-Signature": activate_sig,
            "Content-Type": "application/json",
        }
        activate_response = self.client.post(
            "/api/billing/webhooks/stripe",
            content=activate_text,
            headers=activate_headers,
        )
        self.assertEqual(activate_response.status_code, 200)

        chargeback_payload = {
            "id": "evt_chargeback_guard_2",
            "type": "charge.dispute.created",
            "data": {"object": {"customer": "cus_chargeback_guard_1"}},
        }
        chargeback_text = json.dumps(chargeback_payload, separators=(",", ":"))
        chargeback_sig = _stripe_signature("whsec_test", chargeback_text, timestamp)
        chargeback_headers = {
            "Stripe-Signature": chargeback_sig,
            "Content-Type": "application/json",
        }
        first_chargeback = self.client.post(
            "/api/billing/webhooks/stripe",
            content=chargeback_text,
            headers=chargeback_headers,
        )
        self.assertEqual(first_chargeback.status_code, 200)
        self.assertFalse(first_chargeback.json()["replayed"])

        replay_chargeback = self.client.post(
            "/api/billing/webhooks/stripe",
            content=chargeback_text,
            headers=chargeback_headers,
        )
        self.assertEqual(replay_chargeback.status_code, 200)
        self.assertTrue(replay_chargeback.json()["replayed"])

        with Session(self.engine) as session:
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            assert entitlement is not None
            self.assertEqual(entitlement.lifecycle_state, "CANCELED")
            chargeback_ledgers = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_chargeback_guard_2",
                )
            ).all()
            self.assertEqual(len(chargeback_ledgers), 1)

    def test_async_mode_enqueues_and_returns_queued_status(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = True
        payload = {
            "id": "evt_async_enqueued_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_async_enqueued_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        payload_text = json.dumps(payload, separators=(",", ":"))
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        headers = {"Stripe-Signature": signature, "Content-Type": "application/json"}

        with patch.object(billing, "_enqueue_stripe_webhook_processing") as enqueue_mock:
            response = self.client.post(
                "/api/billing/webhooks/stripe",
                content=payload_text,
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        payload_json = response.json()
        self.assertEqual(payload_json["status"], "QUEUED")
        self.assertEqual(payload_json["processing_mode"], "ASYNC")
        self.assertFalse(payload_json["replayed"])
        enqueue_mock.assert_called_once()

        with Session(self.engine) as session:
            receipts = session.exec(
                select(BillingWebhookReceipt).where(
                    BillingWebhookReceipt.provider_event_id == "evt_async_enqueued_1"
                )
            ).all()
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0].status, "QUEUED")
            self.assertIsNotNone(receipts[0].payload_json)
            self.assertEqual(receipts[0].provider_customer_id, "cus_async_enqueued_1")
            ledger_rows = session.exec(select(BillingLedgerEntry)).all()
            self.assertEqual(len(ledger_rows), 0)

    def test_async_worker_processes_queued_receipt_and_remains_replay_safe(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = True
        payload = {
            "id": "evt_async_worker_1",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_async_worker_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        payload_text = json.dumps(payload, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        headers = {"Stripe-Signature": signature, "Content-Type": "application/json"}

        with patch.object(billing, "_enqueue_stripe_webhook_processing") as enqueue_mock:
            queued = self.client.post(
                "/api/billing/webhooks/stripe",
                content=payload_text,
                headers=headers,
            )

        self.assertEqual(queued.status_code, 200)
        self.assertEqual(queued.json()["status"], "QUEUED")
        enqueue_mock.assert_called_once()

        with Session(self.engine) as session:
            receipt = session.exec(
                select(BillingWebhookReceipt).where(
                    BillingWebhookReceipt.provider_event_id == "evt_async_worker_1"
                )
            ).first()
            self.assertIsNotNone(receipt)
            receipt_id = receipt.id

        billing._process_stripe_webhook_background_job(
            receipt_id=receipt_id,
            provider_name="STRIPE",
            event_id="evt_async_worker_1",
            event_type="invoice.payment_failed",
            payload=payload,
            payload_hash=payload_hash,
            provider_customer_id="cus_async_worker_1",
            provider_subscription_id=None,
            session_factory=lambda: Session(self.engine),
        )
        billing._process_stripe_webhook_background_job(
            receipt_id=receipt_id,
            provider_name="STRIPE",
            event_id="evt_async_worker_1",
            event_type="invoice.payment_failed",
            payload=payload,
            payload_hash=payload_hash,
            provider_customer_id="cus_async_worker_1",
            provider_subscription_id=None,
            session_factory=lambda: Session(self.engine),
        )

        with Session(self.engine) as session:
            processed_receipt = session.get(BillingWebhookReceipt, receipt_id)
            self.assertIsNotNone(processed_receipt)
            self.assertEqual(processed_receipt.status, "PROCESSED")
            ledger_rows = session.exec(
                select(BillingLedgerEntry).where(BillingLedgerEntry.source_key == "wh:stripe:evt_async_worker_1")
            ).all()
            self.assertEqual(len(ledger_rows), 1)
            entitlement = session.exec(
                select(BillingEntitlementState).where(BillingEntitlementState.user_id == self.user_a_id)
            ).first()
            self.assertIsNotNone(entitlement)
            self.assertEqual(entitlement.lifecycle_state, "PAST_DUE")

        replay = self.client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers=headers,
        )
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["replayed"])

    def test_async_worker_schedules_retry_on_unexpected_error(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = True
        settings.BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS = 3
        settings.BILLING_WEBHOOK_RETRY_BASE_SECONDS = 5

        payload = {
            "id": "evt_async_retry_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_async_retry_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        payload_text = json.dumps(payload, separators=(",", ":"))
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        headers = {"Stripe-Signature": signature, "Content-Type": "application/json"}

        with patch.object(billing, "_enqueue_stripe_webhook_processing") as enqueue_mock:
            queued = self.client.post(
                "/api/billing/webhooks/stripe",
                content=payload_text,
                headers=headers,
            )

        enqueue_mock.assert_called_once()
        self.assertEqual(queued.status_code, 200)
        self.assertEqual(queued.json()["status"], "QUEUED")

        with Session(self.engine) as session:
            receipt = session.exec(
                select(BillingWebhookReceipt).where(
                    BillingWebhookReceipt.provider_event_id == "evt_async_retry_1"
                )
            ).first()
            self.assertIsNotNone(receipt)
            assert receipt is not None
            receipt_id = receipt.id

        with patch.object(
            billing,
            "_apply_stripe_webhook_effects",
            side_effect=RuntimeError("provider_down"),
        ):
            billing._process_stripe_webhook_background_job(
                receipt_id=receipt_id,
                event_type=None,
                session_factory=lambda: Session(self.engine),
            )

        with Session(self.engine) as session:
            updated = session.get(BillingWebhookReceipt, receipt_id)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "FAILED")
            self.assertEqual(updated.last_error_reason, "unexpected_error")
            self.assertEqual(updated.attempt_count, 1)
            self.assertIsNotNone(updated.next_attempt_at)
            assert updated.next_attempt_at is not None
            self.assertGreaterEqual(updated.next_attempt_at, updated.processed_at)

    def test_retry_worker_marks_dead_when_retry_exhausted(self) -> None:
        settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE = True
        settings.BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS = 2
        settings.BILLING_WEBHOOK_RETRY_BASE_SECONDS = 1

        payload = {
            "id": "evt_async_retry_dead_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_async_retry_dead_1",
                    "metadata": {"user_id": str(self.user_a_id)},
                }
            },
        }
        payload_text = json.dumps(payload, separators=(",", ":"))
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_test", payload_text, timestamp)
        headers = {"Stripe-Signature": signature, "Content-Type": "application/json"}

        with patch.object(billing, "_enqueue_stripe_webhook_processing") as enqueue_mock:
            queued = self.client.post(
                "/api/billing/webhooks/stripe",
                content=payload_text,
                headers=headers,
            )
        enqueue_mock.assert_called_once()
        self.assertEqual(queued.status_code, 200)

        with Session(self.engine) as session:
            receipt = session.exec(
                select(BillingWebhookReceipt).where(
                    BillingWebhookReceipt.provider_event_id == "evt_async_retry_dead_1"
                )
            ).first()
            self.assertIsNotNone(receipt)
            assert receipt is not None
            receipt_id = receipt.id

        with patch.object(
            billing,
            "_apply_stripe_webhook_effects",
            side_effect=RuntimeError("provider_down"),
        ):
            billing._process_stripe_webhook_background_job(
                receipt_id=receipt_id,
                event_type=None,
                session_factory=lambda: Session(self.engine),
            )
            with Session(self.engine) as session:
                first_attempt = session.get(BillingWebhookReceipt, receipt_id)
                self.assertIsNotNone(first_attempt)
                assert first_attempt is not None
                first_attempt.next_attempt_at = first_attempt.processed_at
                session.add(first_attempt)
                session.commit()

            billing.process_pending_stripe_webhook_receipts(
                limit=10,
                session_factory=lambda: Session(self.engine),
            )

        with Session(self.engine) as session:
            updated = session.get(BillingWebhookReceipt, receipt_id)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "DEAD")
            self.assertEqual(updated.attempt_count, 2)
            self.assertEqual(updated.last_error_reason, "retry_exhausted:unexpected_error")
            self.assertIsNone(updated.next_attempt_at)


if __name__ == "__main__":
    unittest.main()
