from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
import uuid
from typing import Generator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.journals import router as journals_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_read_session, get_session  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.pagination import PageCursor  # noqa: E402


class JournalCursorPaginationTests(unittest.TestCase):
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
        app.dependency_overrides[get_read_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.user_a = User(email="cursor-a@example.com", full_name="A", hashed_password="hashed")
            self.user_b = User(email="cursor-b@example.com", full_name="B", hashed_password="hashed")
            self.user_a.partner_id = self.user_b.id
            self.user_b.partner_id = self.user_a.id
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
        self.current_user_id = self.user_a.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def _create_journal(self, content: str) -> None:
        with patch("app.api.journals.analyze_journal", AsyncMock(return_value={})), patch(
            "app.api.journals.resolve_quota_limit",
            return_value=999,
        ), patch(
            "app.api.journals.consume_daily_quota",
            return_value=(True, 998),
        ):
            response = self.client.post("/api/journals/", json={"content": content})
        self.assertEqual(response.status_code, 200, response.text)

    def test_cursor_pagination_returns_next_cursor_header(self) -> None:
        for idx in range(5):
            self._create_journal(f"journal-{idx}")

        first_page = self.client.get("/api/journals/?limit=2")
        self.assertEqual(first_page.status_code, 200)
        first_items = first_page.json()
        self.assertEqual(len(first_items), 2)
        first_cursor = first_page.headers.get("X-Next-Cursor")
        self.assertIsNotNone(first_cursor)

        last_item = first_items[-1]
        cursor = first_cursor or PageCursor(
            last_timestamp=datetime.fromisoformat(str(last_item["created_at"])),
            last_id=uuid.UUID(str(last_item["id"])),
        ).encode()
        self.assertIsNotNone(cursor)

        second_page = self.client.get(f"/api/journals/?limit=2&cursor={cursor}")
        self.assertEqual(second_page.status_code, 200)
        second_items = second_page.json()
        self.assertEqual(len(second_items), 2)
        next_cursor = second_page.headers.get("X-Next-Cursor")
        self.assertIsNotNone(next_cursor)

        third_page = self.client.get(f"/api/journals/?limit=2&cursor={next_cursor}")
        self.assertEqual(third_page.status_code, 200)
        third_items = third_page.json()
        self.assertEqual(len(third_items), 1)
        self.assertIsNone(third_page.headers.get("X-Next-Cursor"))

    def test_cursor_and_offset_cannot_be_combined(self) -> None:
        response = self.client.get("/api/journals/?cursor=abc&offset=1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("offset cannot be combined with cursor", response.text)

    def test_invalid_cursor_returns_400(self) -> None:
        response = self.client.get("/api/journals/?cursor=not-a-valid-cursor")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid journal cursor", response.text)

    def test_journal_list_exposes_query_budget_headers_and_clamp(self) -> None:
        for idx in range(3):
            self._create_journal(f"journal-budget-{idx}")

        original_budget = settings.TIMELINE_CURSOR_QUERY_BUDGET
        settings.TIMELINE_CURSOR_QUERY_BUDGET = 5  # max_fetch=(5-1)//2=2
        try:
            response = self.client.get("/api/journals/?limit=50")
        finally:
            settings.TIMELINE_CURSOR_QUERY_BUDGET = original_budget

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.headers.get("X-Query-Limit-Clamped"), "2")
        self.assertEqual(response.headers.get("X-Query-Budget-Units"), "5")


if __name__ == "__main__":
    unittest.main()
