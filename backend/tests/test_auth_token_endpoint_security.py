# AUTHZ_MATRIX: POST /api/auth/token
# AUTHZ_MATRIX: POST /api/auth/refresh

import sys
import unittest
from datetime import timedelta
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import login  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.auth_refresh_session import AuthRefreshSession  # noqa: E402
from app.models.user import User  # noqa: E402


class AuthTokenEndpointSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(login.router, prefix="/api/auth")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)
        self._orig_login_rate_limit_ip_count = settings.LOGIN_RATE_LIMIT_IP_COUNT
        settings.LOGIN_RATE_LIMIT_IP_COUNT = 100000

        with Session(self.engine) as session:
            user = User(
                email="auth-owner@example.com",
                full_name="Auth Owner",
                hashed_password=get_password_hash("valid-password"),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id

    def tearDown(self) -> None:
        settings.LOGIN_RATE_LIMIT_IP_COUNT = self._orig_login_rate_limit_ip_count
        self.client.close()
        self.engine.dispose()

    def test_token_issues_jwt_for_valid_credentials(self) -> None:
        response = self.client.post(
            "/api/auth/token",
            data={"username": "auth-owner@example.com", "password": "valid-password"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["token_type"], "bearer")
        token = payload["access_token"]

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        self.assertEqual(decoded.get("sub"), str(self.user_id))

        refresh_token = payload.get("refresh_token")
        self.assertIsInstance(refresh_token, str)
        self.assertGreater(int(payload.get("refresh_expires_in", 0)), 0)
        decoded_refresh = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        self.assertEqual(decoded_refresh.get("sub"), str(self.user_id))
        self.assertEqual(decoded_refresh.get("typ"), "refresh")
        self.assertIsNotNone(decoded_refresh.get("sid"))
        self.assertIsNotNone(decoded_refresh.get("jti"))

    def test_refresh_rotates_and_replay_is_rejected(self) -> None:
        login_response = self.client.post(
            "/api/auth/token",
            data={"username": "auth-owner@example.com", "password": "valid-password"},
            headers={"x-device-id": "device-auth-a"},
        )
        self.assertEqual(login_response.status_code, 200)
        login_payload = login_response.json()
        old_refresh = login_payload["refresh_token"]

        refresh_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": old_refresh},
            headers={"x-device-id": "device-auth-a"},
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_payload = refresh_response.json()
        self.assertIn("refresh_token", refresh_payload)
        self.assertNotEqual(refresh_payload["refresh_token"], old_refresh)

        replay_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": old_refresh},
            headers={"x-device-id": "device-auth-a"},
        )
        self.assertEqual(replay_response.status_code, 401)
        self.assertEqual(replay_response.json()["detail"], "Could not validate credentials")

        latest_replay_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_payload["refresh_token"]},
            headers={"x-device-id": "device-auth-a"},
        )
        self.assertEqual(latest_replay_response.status_code, 401)
        self.assertEqual(latest_replay_response.json()["detail"], "Could not validate credentials")

    def test_refresh_rejects_cross_subject_session_binding(self) -> None:
        with Session(self.engine) as session:
            other_user = User(
                email="auth-other@example.com",
                full_name="Auth Other",
                hashed_password=get_password_hash("other-password"),
            )
            session.add(other_user)
            session.commit()
            session.refresh(other_user)
            other_user_id = other_user.id

        owner_login_response = self.client.post(
            "/api/auth/token",
            data={"username": "auth-owner@example.com", "password": "valid-password"},
            headers={"x-device-id": "device-owner"},
        )
        self.assertEqual(owner_login_response.status_code, 200)
        owner_refresh_token = owner_login_response.json()["refresh_token"]
        owner_refresh_payload = jwt.decode(owner_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        with Session(self.engine) as session:
            other_session = session.exec(
                select(AuthRefreshSession).where(AuthRefreshSession.user_id == other_user_id)
            ).first()
            if other_session is None:
                bootstrap_refresh_token = self.client.post(
                    "/api/auth/token",
                    data={"username": "auth-other@example.com", "password": "other-password"},
                    headers={"x-device-id": "device-other"},
                ).json()["refresh_token"]
                bootstrap_payload = jwt.decode(
                    bootstrap_refresh_token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                )
                other_session_id = bootstrap_payload["sid"]
            else:
                other_session_id = str(other_session.id)

        forged_cross_subject_refresh = jwt.encode(
            {
                "sub": str(self.user_id),
                "sid": other_session_id,
                "jti": owner_refresh_payload["jti"],
                "typ": "refresh",
                "exp": utcnow() + timedelta(minutes=10),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": forged_cross_subject_refresh},
            headers={"x-device-id": "device-owner"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_token_rejects_unknown_email(self) -> None:
        response = self.client.post(
            "/api/auth/token",
            data={"username": "missing@example.com", "password": "valid-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Incorrect email or password")
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")

    def test_token_rejects_wrong_password(self) -> None:
        response = self.client.post(
            "/api/auth/token",
            data={"username": "auth-owner@example.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Incorrect email or password")
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")

    def test_token_rejects_inactive_user(self) -> None:
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            assert user is not None
            user.is_active = False
            session.add(user)
            session.commit()

        response = self.client.post(
            "/api/auth/token",
            data={"username": "auth-owner@example.com", "password": "valid-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Incorrect email or password")
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")

    def test_token_rejects_soft_deleted_user(self) -> None:
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            assert user is not None
            user.deleted_at = utcnow()
            session.add(user)
            session.commit()

        response = self.client.post(
            "/api/auth/token",
            data={"username": "auth-owner@example.com", "password": "valid-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Incorrect email or password")
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")


if __name__ == "__main__":
    unittest.main()
