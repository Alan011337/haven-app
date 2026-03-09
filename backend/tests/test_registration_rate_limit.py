# Registration rate limit: POST /api/users/ returns 429 when same IP exceeds limit.

import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routers import users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.services.rate_limit import reset_rate_limit_state_for_tests  # noqa: E402


def _valid_payload(email: str) -> dict:
    return {
        "email": email,
        "password": "pw123456",
        "full_name": "Rate Limit User",
        "age_confirmed": True,
        "agreed_to_terms": True,
        "terms_version": "v1.0",
        "privacy_version": "v1.0",
    }


class RegistrationRateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limit_state_for_tests()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    @patch.object(settings, "REGISTRATION_RATE_LIMIT_IP_COUNT", 2)
    @patch.object(settings, "REGISTRATION_RATE_LIMIT_IP_WINDOW_SECONDS", 300)
    def test_registration_rate_limit_returns_429_when_exceeded(self) -> None:
        # Same client (same IP) can register up to 2 times in the window; 3rd returns 429.
        r1 = self.client.post("/api/users/", json=_valid_payload("r1@example.com"))
        self.assertEqual(r1.status_code, 200, r1.text)

        r2 = self.client.post("/api/users/", json=_valid_payload("r2@example.com"))
        self.assertEqual(r2.status_code, 200, r2.text)

        r3 = self.client.post("/api/users/", json=_valid_payload("r3@example.com"))
        self.assertEqual(r3.status_code, 429, r3.text)
        self.assertIn("Retry-After", r3.headers)
        self.assertIn("註冊嘗試次數過多", r3.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main()
