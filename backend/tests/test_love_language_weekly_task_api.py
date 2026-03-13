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
from app.api.routers import love_language  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class LoveLanguageWeeklyTaskApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(love_language.router, prefix="/api/love-languages")

        self.current_user_id = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            paired_a = User(email="weekly-task-a@example.com", full_name="Weekly Task A", hashed_password="x")
            paired_b = User(email="weekly-task-b@example.com", full_name="Weekly Task B", hashed_password="x")
            unpaired = User(email="weekly-task-c@example.com", full_name="Weekly Task C", hashed_password="x")
            session.add(paired_a)
            session.add(paired_b)
            session.add(unpaired)
            session.commit()
            session.refresh(paired_a)
            session.refresh(paired_b)
            session.refresh(unpaired)

            paired_a.partner_id = paired_b.id
            paired_b.partner_id = paired_a.id
            session.add(paired_a)
            session.add(paired_b)
            session.commit()

            self.paired_a_id = paired_a.id
            self.paired_b_id = paired_b.id
            self.unpaired_id = unpaired.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_paired_user_can_fetch_weekly_task(self) -> None:
        self.current_user_id = self.paired_a_id

        response = self.client.get("/api/love-languages/weekly-task")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("task_slug", payload)
        self.assertIn("task_label", payload)

    def test_unpaired_user_gets_null_weekly_task(self) -> None:
        self.current_user_id = self.unpaired_id

        response = self.client.get("/api/love-languages/weekly-task")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json())

    def test_unpaired_user_cannot_complete_weekly_task(self) -> None:
        self.current_user_id = self.unpaired_id

        response = self.client.post("/api/love-languages/weekly-task/complete")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "需要先完成雙向綁定")


if __name__ == "__main__":
    unittest.main()
