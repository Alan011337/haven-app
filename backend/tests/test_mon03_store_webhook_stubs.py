"""MON-03: Store provider webhook stub routes return 501 until adapters are implemented."""
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


class Mon03StoreWebhookStubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_webhook_appstore_returns_501(self) -> None:
        response = self.client.post("/api/billing/webhooks/appstore", json={})
        self.assertEqual(response.status_code, 501)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("MON_03_STUB", data.get("code", ""))

    def test_webhook_googleplay_returns_501(self) -> None:
        response = self.client.post("/api/billing/webhooks/googleplay", json={})
        self.assertEqual(response.status_code, 501)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("MON_03_STUB", data.get("code", ""))
