import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import SECURITY_RESPONSE_HEADERS, app  # noqa: E402


class SecurityHeadersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_root_response_includes_security_headers(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for header_name, expected_value in SECURITY_RESPONSE_HEADERS.items():
            self.assertEqual(response.headers.get(header_name), expected_value)

    def test_openapi_snapshot_route_skips_custom_security_headers(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        for header_name in SECURITY_RESPONSE_HEADERS:
            self.assertIsNone(response.headers.get(header_name))


if __name__ == "__main__":
    unittest.main()
