import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


class CorsPreflightAlphaGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.allowed_origin = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_preflight_allows_configured_origin(self) -> None:
        response = self.client.options(
            "/api/users/me",
            headers={
                "Origin": self.allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), self.allowed_origin)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_preflight_rejects_unknown_origin(self) -> None:
        response = self.client.options(
            "/api/users/me",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertIn(response.status_code, {400, 403})
        self.assertIsNone(response.headers.get("access-control-allow-origin"))


if __name__ == "__main__":
    unittest.main()
