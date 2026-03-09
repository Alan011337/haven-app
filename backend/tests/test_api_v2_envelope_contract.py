import sys
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import main as main_module  # noqa: E402
from app.api.v2_contract import build_success_envelope  # noqa: E402


class ApiV2EnvelopeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.client.close()

    def _new_user_payload(self) -> dict:
        token = uuid.uuid4().hex[:8]
        return {
            "email": f"v2-{token}@example.com",
            "full_name": "V2 Contract",
            "password": "VeryStrongPass123!",
            "age_confirmed": True,
            "agreed_to_terms": True,
            "birth_year": 1996,
            "terms_version": "2026-03-01",
            "privacy_version": "2026-03-01",
        }

    def test_api_write_requires_idempotency_key(self) -> None:
        response = self.client.post("/api/users/", json=self._new_user_payload())
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], "missing_idempotency_key")
        self.assertIn("meta", payload)
        self.assertIn("request_id", payload["meta"])

    def test_auth_token_path_is_exempt_from_global_idempotency_guard(self) -> None:
        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("message"), "Successfully logged out")

    def test_build_success_envelope_shape(self) -> None:
        payload = build_success_envelope(
            request_id="req-test-v2",
            data={"ok": True, "message": "success"},
        )
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertIn("request_id", payload["meta"])
        self.assertEqual(payload["meta"]["request_id"], "req-test-v2")
        self.assertIn("error", payload)
        self.assertIsNone(payload["error"])
        self.assertIsInstance(payload["data"], dict)
        self.assertTrue(payload["data"]["ok"])

    def test_api_not_found_uses_error_envelope(self) -> None:
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertIn("meta", payload)
        self.assertEqual(payload["error"]["code"], "http_404")
        self.assertIn("detail", payload)


if __name__ == "__main__":
    unittest.main()
