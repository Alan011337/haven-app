# AUTHZ_MATRIX: POST /api/journals/
# AUTHZ_MATRIX: DELETE /api/journals/{journal_id}
# AUTHZ_DENY_MATRIX: DELETE /api/journals/{journal_id}

import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.journals import router as journals_router  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class JournalAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(journals_router, prefix="/api/journals")

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
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)

            journal = Journal(content="owner-only", user_id=self.user_a.id)
            session.add(journal)
            session.commit()
            session.refresh(journal)

            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id
            self.journal_id = journal.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_delete_journal_allows_owner(self) -> None:
        response = self.client.delete(f"/api/journals/{self.journal_id}")
        self.assertEqual(response.status_code, 204)

        with Session(self.engine) as session:
            deleted = session.get(Journal, self.journal_id)
            self.assertIsNotNone(deleted)
            assert deleted is not None
            self.assertIsNotNone(deleted.deleted_at)

    def test_delete_journal_rejects_non_owner(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.delete(f"/api/journals/{self.journal_id}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "你沒有權限刪除這篇日記")

    def test_create_journal_rejects_overposted_sensitive_fields(self) -> None:
        response = self.client.post(
            "/api/journals/",
            json={
                "content": "this should fail",
                "user_id": str(self.user_b_id),
                "safety_tier": 3,
            },
        )

        self.assertEqual(response.status_code, 422)
        serialized = str(response.json())
        self.assertIn("user_id", serialized)
        self.assertIn("safety_tier", serialized)

        with Session(self.engine) as session:
            journals = session.exec(select(Journal)).all()
            self.assertEqual(len(journals), 1)


if __name__ == "__main__":
    unittest.main()
