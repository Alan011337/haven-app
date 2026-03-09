# READ_AUTHZ_MATRIX: GET /api/users/gamification-summary

import sys
import unittest
from datetime import timedelta
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
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class GamificationSummaryApiTests(unittest.TestCase):
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
            user_a = User(email="gami-a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="gami-b@example.com", full_name="B", hashed_password="hashed")
            user_c = User(email="gami-c@example.com", full_name="C", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)

            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            user_a.savings_score = 250
            user_b.savings_score = 80
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)

            now = utcnow()
            session.add(
                Journal(
                    content="today-a",
                    user_id=user_a.id,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                Journal(
                    content="today-b",
                    user_id=user_b.id,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                Journal(
                    content="yesterday-a",
                    user_id=user_a.id,
                    created_at=now - timedelta(days=1),
                    updated_at=now - timedelta(days=1),
                )
            )
            session.add(
                Journal(
                    content="yesterday-b",
                    user_id=user_b.id,
                    created_at=now - timedelta(days=1),
                    updated_at=now - timedelta(days=1),
                )
            )
            session.add(
                Journal(
                    content="older-a-only",
                    user_id=user_a.id,
                    created_at=now - timedelta(days=2),
                    updated_at=now - timedelta(days=2),
                )
            )
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_summary_returns_pair_based_streak_and_level_fields(self) -> None:
        response = self.client.get("/api/users/gamification-summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_partner_context"])
        self.assertEqual(payload["streak_days"], 2)
        self.assertEqual(payload["best_streak_days"], 2)
        self.assertTrue(payload["streak_eligible_today"])
        self.assertEqual(payload["level"], 3)
        self.assertEqual(payload["level_points_total"], 250)
        self.assertEqual(payload["level_points_current"], 50)
        self.assertEqual(payload["level_points_target"], 100)
        self.assertEqual(payload["love_bar_percent"], 50.0)
        self.assertTrue(payload["anti_cheat_enabled"])

    def test_summary_ignores_overposted_user_id_query(self) -> None:
        baseline = self.client.get("/api/users/gamification-summary")
        self.assertEqual(baseline.status_code, 200)

        overposted = self.client.get(
            "/api/users/gamification-summary",
            params={"user_id": str(self.user_b_id)},
        )
        self.assertEqual(overposted.status_code, 200)
        self.assertEqual(overposted.json(), baseline.json())

    def test_summary_when_user_has_no_partner_returns_zero_streak(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.get("/api/users/gamification-summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["has_partner_context"])
        self.assertEqual(payload["streak_days"], 0)
        self.assertEqual(payload["best_streak_days"], 0)
        self.assertFalse(payload["streak_eligible_today"])

    def test_summary_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            response = client.get("/api/users/gamification-summary")
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
