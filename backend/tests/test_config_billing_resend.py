"""Tests that Settings includes Billing/Stripe and Resend config (P0-1)."""
import unittest

from app.core.config import settings


class ConfigBillingResendTests(unittest.TestCase):
    """Verify config has Billing and Resend attributes (no AttributeError)."""

    def test_settings_has_billing_stripe_attributes(self) -> None:
        self.assertHasAttr(settings, "BILLING_STRIPE_SECRET_KEY")
        self.assertHasAttr(settings, "BILLING_STRIPE_PRICE_ID")
        self.assertHasAttr(settings, "BILLING_STRIPE_SUCCESS_URL")
        self.assertHasAttr(settings, "BILLING_STRIPE_CANCEL_URL")
        self.assertHasAttr(settings, "BILLING_STRIPE_PORTAL_RETURN_URL")
        self.assertHasAttr(settings, "BILLING_STRIPE_WEBHOOK_SECRET")

    def test_settings_has_resend_api_key(self) -> None:
        self.assertHasAttr(settings, "RESEND_API_KEY")
        self.assertHasAttr(settings, "RESEND_FROM_EMAIL")
        self.assertHasAttr(settings, "NOTIFICATION_COOLDOWN_SECONDS")

    def test_settings_has_log_and_pool_attributes(self) -> None:
        self.assertHasAttr(settings, "LOG_INCLUDE_STACKTRACE")
        self.assertHasAttr(settings, "DATABASE_POOL_SIZE")
        self.assertHasAttr(settings, "DATABASE_POOL_RECYCLE_SECONDS")

    def test_billing_stripe_and_resend_are_optional_types(self) -> None:
        # Optional billing/resend keys are None or str (no AttributeError)
        v = getattr(settings, "BILLING_STRIPE_SECRET_KEY", None)
        self.assertIsInstance(v, (type(None), str), msg="BILLING_STRIPE_SECRET_KEY")
        v = getattr(settings, "RESEND_API_KEY", None)
        self.assertIsInstance(v, (type(None), str), msg="RESEND_API_KEY")

    def assertHasAttr(self, obj: object, name: str) -> None:
        self.assertTrue(
            hasattr(obj, name),
            msg=f"Settings must have attribute {name!r}",
        )


if __name__ == "__main__":
    unittest.main()
