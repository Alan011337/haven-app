# AUTHZ_MATRIX: PATCH /api/users/me
# READ_AUTHZ_MATRIX: GET /api/users/{user_id}
# READ_AUTHZ_MATRIX: GET /api/users/me

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
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class UserAuthorizationMatrixTests(unittest.TestCase):
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
            self.user_c = User(email="c@example.com", full_name="C", hashed_password="hashed")
            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)

            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)

            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
            self.user_c_id = self.user_c.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_read_user_allows_self(self) -> None:
        response = self.client.get(f"/api/users/{self.user_a_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user_a_id))

    def test_patch_user_me_allows_self(self) -> None:
        response = self.client.patch(
            "/api/users/me",
            json={"full_name": "A Updated"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["full_name"], "A Updated")

    def test_read_user_me_returns_current_user(self) -> None:
        response = self.client.get("/api/users/me")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user_a_id))

    def test_read_user_allows_partner(self) -> None:
        response = self.client.get(f"/api/users/{self.user_b_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user_b_id))

    def test_read_user_rejects_non_partner(self) -> None:
        response = self.client.get(f"/api/users/{self.user_c_id}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Not allowed to access this user.")

    def test_unpaired_user_cannot_read_others(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get(f"/api/users/{self.user_a_id}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Not allowed to access this user.")


if __name__ == "__main__":
    unittest.main()
