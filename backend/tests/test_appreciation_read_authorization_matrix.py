# READ_AUTHZ_MATRIX: GET /api/appreciations/{appreciation_id}

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
from app.api.routers import appreciations  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.appreciation import Appreciation  # noqa: E402
from app.models.user import User  # noqa: E402


class AppreciationReadAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(appreciations.router, prefix="/api/appreciations")

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
            user_a = User(email="appreciation-a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="appreciation-b@example.com", full_name="B", hashed_password="hashed")
            user_c = User(email="appreciation-c@example.com", full_name="C", hashed_password="hashed")
            user_d = User(email="appreciation-d@example.com", full_name="D", hashed_password="hashed")
            user_e = User(email="appreciation-e@example.com", full_name="E", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.add(user_e)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)
            session.refresh(user_d)
            session.refresh(user_e)

            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            user_c.partner_id = user_d.id
            user_d.partner_id = user_c.id
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.commit()

            appreciation_ab = Appreciation(
                user_id=user_a.id,
                partner_id=user_b.id,
                body_text="thanks-ab",
            )
            appreciation_cd = Appreciation(
                user_id=user_c.id,
                partner_id=user_d.id,
                body_text="thanks-cd",
            )
            session.add(appreciation_ab)
            session.add(appreciation_cd)
            session.commit()
            session.refresh(appreciation_ab)
            session.refresh(appreciation_cd)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id
            self.user_d_id = user_d.id
            self.user_e_id = user_e.id
            self.appreciation_ab_id = appreciation_ab.id
            self.appreciation_cd_id = appreciation_cd.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_detail_allows_sender(self) -> None:
        response = self.client.get(f"/api/appreciations/{self.appreciation_ab_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], self.appreciation_ab_id)
        self.assertEqual(payload["body_text"], "thanks-ab")
        self.assertTrue(payload["is_mine"])

    def test_detail_allows_recipient(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.get(f"/api/appreciations/{self.appreciation_ab_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], self.appreciation_ab_id)
        self.assertEqual(payload["body_text"], "thanks-ab")
        self.assertFalse(payload["is_mine"])

    def test_detail_rejects_foreign_pair(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get(f"/api/appreciations/{self.appreciation_ab_id}")
        self.assertEqual(response.status_code, 404)

    def test_detail_rejects_unpaired_user(self) -> None:
        self.current_user_id = self.user_e_id
        response = self.client.get(f"/api/appreciations/{self.appreciation_ab_id}")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
