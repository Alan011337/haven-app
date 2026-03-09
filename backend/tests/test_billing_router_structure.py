from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = BACKEND_ROOT / "app" / "api" / "routers" / "billing.py"


class BillingRouterStructureTests(unittest.TestCase):
    def test_billing_router_uses_split_handler_modules(self) -> None:
        source = ROUTER_PATH.read_text(encoding="utf-8")
        self.assertIn("from app.api.routers.billing_checkout_routes import router as checkout_router", source)
        self.assertIn("router.include_router(checkout_router)", source)
        self.assertIn("from app.api.routers.billing_state_change_handlers import handle_billing_state_change", source)
        self.assertIn("from app.api.routers.billing_webhook_handlers import handle_stripe_webhook_request", source)
        self.assertIn("return handle_billing_state_change(", source)
        self.assertIn("return await handle_stripe_webhook_request(", source)


if __name__ == "__main__":
    unittest.main()
