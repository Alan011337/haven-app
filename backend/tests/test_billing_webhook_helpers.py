from __future__ import annotations

import hmac
import hashlib
import time
import unittest

from fastapi import HTTPException

from app.api.routers.billing_webhook_helpers import (
    extract_customer_identifier_from_webhook_payload,
    extract_subscription_identifier_from_webhook_payload,
    extract_user_id_from_webhook_payload,
    parse_stripe_signature_header,
    verify_stripe_signature_or_raise,
    webhook_retry_backoff_seconds,
)


class BillingWebhookHelpersTests(unittest.TestCase):
    def test_parse_stripe_signature_header(self) -> None:
        timestamp, signatures = parse_stripe_signature_header("t=123,v1=abc,v1=def")
        self.assertEqual(timestamp, 123)
        self.assertEqual(signatures, ["abc", "def"])

    def test_verify_stripe_signature_or_raise_accepts_valid_payload(self) -> None:
        payload = b'{"event":"ok"}'
        secret = "whsec_test"
        timestamp = int(time.time())
        signed = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode("utf-8"),
            signed.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signature_header = f"t={timestamp},v1={expected}"

        verify_stripe_signature_or_raise(
            payload=payload,
            signature_header=signature_header,
            secret=secret,
            tolerance_seconds=300,
        )

    def test_verify_stripe_signature_or_raise_rejects_invalid_signature(self) -> None:
        with self.assertRaises(HTTPException):
            verify_stripe_signature_or_raise(
                payload=b'{"event":"ok"}',
                signature_header="t=123,v1=bad",
                secret="whsec_test",
                tolerance_seconds=300,
            )

    def test_extract_helpers(self) -> None:
        payload = {
            "data": {
                "object": {
                    "customer": "cus_123",
                    "subscription": "sub_123",
                    "metadata": {"user_id": "00000000-0000-0000-0000-000000000123"},
                }
            }
        }
        user_id = extract_user_id_from_webhook_payload(payload)
        self.assertIsNotNone(user_id)
        self.assertEqual(str(user_id), "00000000-0000-0000-0000-000000000123")
        self.assertEqual(extract_customer_identifier_from_webhook_payload(payload), "cus_123")
        self.assertEqual(
            extract_subscription_identifier_from_webhook_payload(
                payload,
                event_type="customer.subscription.updated",
            ),
            "sub_123",
        )

    def test_webhook_retry_backoff_seconds_caps_value(self) -> None:
        self.assertEqual(webhook_retry_backoff_seconds(base_seconds=10, attempt_count=1), 10)
        self.assertEqual(webhook_retry_backoff_seconds(base_seconds=10, attempt_count=2), 20)
        self.assertEqual(webhook_retry_backoff_seconds(base_seconds=1000, attempt_count=10), 3600)


if __name__ == "__main__":
    unittest.main()
