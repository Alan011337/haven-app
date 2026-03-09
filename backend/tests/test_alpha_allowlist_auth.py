# AUTHZ_MATRIX: POST /api/auth/token
# AUTHZ_MATRIX: POST /api/users/

import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import login  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class AlphaAllowlistAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(login.router, prefix="/api/auth")
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

        self._old_env = settings.ENV
        self._old_allowlist_enforced = settings.ALLOWLIST_ENFORCED
        self._old_allowlist_envs = settings.ALLOWLIST_ENFORCED_ENVS
        self._old_allowlist_csv = settings.ALLOWED_TEST_EMAILS
        self._old_allowlist_json = settings.ALLOWED_TEST_EMAILS_JSON
        self._old_login_limit = settings.LOGIN_RATE_LIMIT_IP_COUNT
        self._old_register_limit = settings.REGISTRATION_RATE_LIMIT_IP_COUNT

        settings.ENV = "alpha"
        settings.ALLOWLIST_ENFORCED = True
        settings.ALLOWLIST_ENFORCED_ENVS = "alpha"
        settings.ALLOWED_TEST_EMAILS = "allowed@example.com,allowed+new@example.com"
        settings.ALLOWED_TEST_EMAILS_JSON = ""
        settings.LOGIN_RATE_LIMIT_IP_COUNT = 100000
        settings.REGISTRATION_RATE_LIMIT_IP_COUNT = 100000

        with Session(self.engine) as session:
            user_allowed = User(
                email="allowed@example.com",
                full_name="Allowed User",
                hashed_password=get_password_hash("password123"),
            )
            user_denied = User(
                email="denied@example.com",
                full_name="Denied User",
                hashed_password=get_password_hash("password123"),
            )
            session.add(user_allowed)
            session.add(user_denied)
            session.commit()

    def tearDown(self) -> None:
        settings.ENV = self._old_env
        settings.ALLOWLIST_ENFORCED = self._old_allowlist_enforced
        settings.ALLOWLIST_ENFORCED_ENVS = self._old_allowlist_envs
        settings.ALLOWED_TEST_EMAILS = self._old_allowlist_csv
        settings.ALLOWED_TEST_EMAILS_JSON = self._old_allowlist_json
        settings.LOGIN_RATE_LIMIT_IP_COUNT = self._old_login_limit
        settings.REGISTRATION_RATE_LIMIT_IP_COUNT = self._old_register_limit
        self.client.close()
        self.engine.dispose()

    def _register_payload(self, email: str) -> dict:
        return {
            "email": email,
            "password": "password123",
            "full_name": "Tester",
            "age_confirmed": True,
            "agreed_to_terms": True,
            "terms_version": "v1.0",
            "privacy_version": "v1.0",
            "birth_year": 1995,
        }

    def test_register_allowed_email_succeeds(self) -> None:
        response = self.client.post("/api/users/", json=self._register_payload("allowed+new@example.com"))
        self.assertNotEqual(response.status_code, 403)

    def test_register_denied_email_returns_generic_message(self) -> None:
        response = self.client.post("/api/users/", json=self._register_payload("outsider@example.com"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "邀請制內測：目前僅開放受邀測試者。")

    def test_login_denied_message_does_not_leak_user_existence(self) -> None:
        existing = self.client.post(
            "/api/auth/token",
            data={"username": "denied@example.com", "password": "password123"},
        )
        missing = self.client.post(
            "/api/auth/token",
            data={"username": "missing-denied@example.com", "password": "password123"},
        )
        self.assertEqual(existing.status_code, 403)
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(existing.json()["detail"], missing.json()["detail"])

    def test_login_allowed_email_still_works(self) -> None:
        response = self.client.post(
            "/api/auth/token",
            data={"username": "allowed@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())


if __name__ == "__main__":
    unittest.main()
