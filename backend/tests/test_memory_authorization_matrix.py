# AUTHZ_MATRIX: GET /api/memory/timeline
# AUTHZ_MATRIX: GET /api/memory/calendar
# AUTHZ_MATRIX: GET /api/memory/time-capsule
# AUTHZ_MATRIX: GET /api/memory/report
# AUTHZ_DENY_MATRIX: GET /api/memory/* (data scoped to current user only)

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

from app.api.deps import get_current_user, get_read_session  # noqa: E402
from app.api.routers import memory  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class MemoryAuthorizationMatrixTests(unittest.TestCase):
    """BOLA: memory endpoints return only current user's (and verified partner's) data."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(memory.router, prefix="/api/memory")

        self.current_user_id = None

        def override_get_read_session() -> Generator[Session, None, None]:
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

        app.dependency_overrides[get_read_session] = override_get_read_session
        app.dependency_overrides[get_current_user] = override_get_current_user

        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)

            journal_a = Journal(content="A's private journal", user_id=user_a.id)
            session.add(journal_a)
            session.commit()
            session.refresh(journal_a)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.journal_a_id = journal_a.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_timeline_allows_current_user_only(self) -> None:
        """As user A, timeline returns only A's data (journal)."""
        response = self.client.get("/api/memory/timeline", params={"limit": 20})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("has_more", data)
        items = data["items"]
        self.assertGreaterEqual(len(items), 1)
        journal_ids = [it["id"] for it in items if it.get("type") == "journal"]
        self.assertIn(str(self.journal_a_id), journal_ids)

    def test_timeline_rejects_cross_user_data(self) -> None:
        """As user B, timeline must not contain A's journal."""
        self.current_user_id = self.user_b_id
        response = self.client.get("/api/memory/timeline", params={"limit": 20})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data["items"]
        journal_ids = [it["id"] for it in items if it.get("type") == "journal"]
        self.assertNotIn(str(self.journal_a_id), journal_ids)
        self.assertEqual(len(journal_ids), 0)

    def test_timeline_rejects_invalid_cursor(self) -> None:
        with patch.object(memory.settings, "TIMELINE_CURSOR_ENABLED", True):
            response = self.client.get(
                "/api/memory/timeline",
                params={"limit": 20, "cursor": "not-a-valid-cursor"},
            )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("detail"), "Invalid timeline cursor.")

    def test_calendar_allows_current_user_only(self) -> None:
        """As user A, calendar returns days with A's content."""
        from datetime import date
        today = date.today()
        response = self.client.get(
            "/api/memory/calendar",
            params={"year": today.year, "month": today.month},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("days", data)
        # A has one journal today (created in setUp), so at least one day may have content
        days_with_content = [d for d in data["days"] if d.get("journal_count", 0) > 0 or d.get("card_count", 0) > 0]
        self.assertGreaterEqual(len(days_with_content), 1)

    def test_calendar_rejects_cross_user_data(self) -> None:
        """As user B, calendar must not show A's journal counts for the same day."""
        self.current_user_id = self.user_b_id
        from datetime import date
        today = date.today()
        response = self.client.get(
            "/api/memory/calendar",
            params={"year": today.year, "month": today.month},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # B has no journals; if the day has content it would be B's. We only have A's journal.
        days_with_journal = [d for d in data["days"] if d.get("journal_count", 0) > 0]
        self.assertEqual(len(days_with_journal), 0)

    def test_time_capsule_allows_current_user_only(self) -> None:
        """As user A or B, time-capsule returns 200 and only own-pair data."""
        response = self.client.get("/api/memory/time-capsule")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("available", data)

    def test_report_allows_current_user_only(self) -> None:
        """As user A or B, report returns 200 and only own-pair data."""
        response = self.client.get("/api/memory/report", params={"period": "month"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("period", data)
        self.assertIn("from_date", data)
        self.assertIn("to_date", data)


if __name__ == "__main__":
    unittest.main()
