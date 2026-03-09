from __future__ import annotations

import unittest

from fastapi import FastAPI

from app.api.routers import billing, users


def _route_method_index(app: FastAPI) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not isinstance(path, str) or not methods:
            continue
        index[path] = {method.upper() for method in methods}
    return index


class RouterRegistrationContractTests(unittest.TestCase):
    def test_billing_router_registers_checkout_and_core_routes(self) -> None:
        app = FastAPI()
        app.include_router(billing.router, prefix="/api/billing")
        index = _route_method_index(app)

        self.assertIn("/api/billing/entitlements/me", index)
        self.assertIn("GET", index["/api/billing/entitlements/me"])
        self.assertIn("/api/billing/create-checkout-session", index)
        self.assertIn("POST", index["/api/billing/create-checkout-session"])
        self.assertIn("/api/billing/create-portal-session", index)
        self.assertIn("POST", index["/api/billing/create-portal-session"])
        self.assertIn("/api/billing/state-change", index)
        self.assertIn("POST", index["/api/billing/state-change"])
        self.assertIn("/api/billing/webhooks/stripe", index)
        self.assertIn("POST", index["/api/billing/webhooks/stripe"])
        self.assertIn("/api/billing/reconciliation", index)
        self.assertIn("GET", index["/api/billing/reconciliation"])

    def test_users_router_registers_split_subrouters(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")
        index = _route_method_index(app)

        self.assertIn("/api/users/feature-flags", index)
        self.assertIn("GET", index["/api/users/feature-flags"])
        self.assertIn("/api/users/events/core-loop", index)
        self.assertIn("POST", index["/api/users/events/core-loop"])
        self.assertIn("/api/users/notifications", index)
        self.assertIn("GET", index["/api/users/notifications"])
        self.assertIn("/api/users/push-subscriptions", index)
        self.assertIn("POST", index["/api/users/push-subscriptions"])
        self.assertIn("/api/users/{user_id}", index)
        self.assertIn("GET", index["/api/users/{user_id}"])


if __name__ == "__main__":
    unittest.main()
