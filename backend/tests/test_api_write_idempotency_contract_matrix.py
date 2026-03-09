from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import main as main_module  # noqa: E402


class ApiWriteIdempotencyContractMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.client.close()

    def _assert_missing_idempotency(self, response) -> None:
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload.get("error", {}).get("code"), "missing_idempotency_key")

    def test_write_routes_require_idempotency_key_before_business_logic(self) -> None:
        matrix = [
            ("post", "/api/users/", {"email": "idem-matrix@example.com"}),
            ("post", "/api/journals/", {"content": "idempotency contract"}),
            ("post", "/api/users/events/core-loop", {"event_name": "daily_loop_completed", "event_id": "e1"}),
            ("post", "/api/cards/respond", {"card_id": 1, "response_text": "ok"}),
            ("post", "/api/card-decks/draw", {"category": "daily_vibe"}),
        ]
        for method, path, body in matrix:
            with self.subTest(path=path):
                response = getattr(self.client, method)(path, json=body)
                self._assert_missing_idempotency(response)

    def test_exempt_routes_do_not_return_missing_idempotency_key(self) -> None:
        exempt_paths = [
            "/api/auth/token",
            "/api/auth/refresh",
            "/api/auth/logout",
            "/api/billing/webhooks/stripe",
        ]
        for path in exempt_paths:
            with self.subTest(path=path):
                response = self.client.post(path, json={})
                payload = response.json() if "application/json" in (response.headers.get("content-type") or "") else {}
                code = payload.get("error", {}).get("code")
                self.assertNotEqual(code, "missing_idempotency_key")


if __name__ == "__main__":
    unittest.main()
