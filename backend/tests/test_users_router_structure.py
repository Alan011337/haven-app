from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = BACKEND_ROOT / "app" / "api" / "routers" / "users" / "routes.py"


class UsersRouterStructureTests(unittest.TestCase):
    def test_users_router_uses_split_subrouters(self) -> None:
        source = ROUTER_PATH.read_text(encoding="utf-8")
        self.assertIn("from app.api.routers.users.growth_routes import router as growth_router", source)
        self.assertIn("from app.api.routers.users.events_routes import router as events_router", source)
        self.assertIn("from app.api.routers.users.notification_routes import router as notification_router", source)
        self.assertIn("router.include_router(growth_router)", source)
        self.assertIn("router.include_router(events_router)", source)
        self.assertIn("router.include_router(notification_router)", source)


if __name__ == "__main__":
    unittest.main()
