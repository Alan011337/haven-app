# AUTHZ_MATRIX: POST /api/users/

import json
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

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class UserFieldLevelAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        self.current_user_id = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id is not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            self.user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
            self.user_b.invite_code = "PAIR01"
            self.user_b.invite_code_created_at = utcnow()
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_create_user_rejects_sensitive_overposting_fields(self) -> None:
        response = self.client.post(
            "/api/users/",
            json={
                "email": "new@example.com",
                "password": "test-password",
                "full_name": "New User",
                "is_active": False,
                "partner_id": str(self.user_b_id),
                "savings_score": 999,
                "invite_code": "HACKED",
            },
        )

        self.assertEqual(response.status_code, 422)
        detail = response.json().get("detail", [])
        serialized = json.dumps(detail, ensure_ascii=False)
        self.assertIn("is_active", serialized)
        self.assertIn("partner_id", serialized)
        self.assertIn("savings_score", serialized)
        self.assertIn("invite_code", serialized)

    def test_pair_rejects_sensitive_overposting_fields(self) -> None:
        response = self.client.post(
            "/api/users/pair",
            json={
                "invite_code": "PAIR01",
                "partner_id": str(self.user_b_id),
                "savings_score": 1000,
            },
        )

        self.assertEqual(response.status_code, 422)
        detail = response.json().get("detail", [])
        serialized = json.dumps(detail, ensure_ascii=False)
        self.assertIn("partner_id", serialized)
        self.assertIn("savings_score", serialized)

        with Session(self.engine) as session:
            user_a = session.get(User, self.user_a_id)
            user_b = session.get(User, self.user_b_id)
            self.assertIsNotNone(user_a)
            self.assertIsNotNone(user_b)
            self.assertIsNone(user_a.partner_id)
            self.assertIsNone(user_b.partner_id)


if __name__ == "__main__":
    unittest.main()
