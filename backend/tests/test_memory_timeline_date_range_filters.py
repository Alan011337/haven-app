from __future__ import annotations

import sys
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.services import memory_archive  # noqa: E402


class MemoryTimelineDateRangeFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000111")
        self.before = datetime(2026, 3, 1, tzinfo=timezone.utc).replace(tzinfo=None)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_journal_timeline_stmt_uses_datetime_range_not_func_date(self) -> None:
        stmt = memory_archive._build_journal_timeline_stmt(
            user_ids=[self.user_id],
            before=self.before,
            cursor_last_id=None,
            from_date=date(2026, 2, 1),
            to_date=date(2026, 3, 2),
            fetch_n=20,
        )
        sql = str(
            stmt.compile(
                dialect=self.engine.dialect,
                compile_kwargs={"literal_binds": True},
            )
        ).upper()
        self.assertNotIn("DATE(", sql)
        self.assertIn("CREATED_AT >=", sql)
        self.assertIn("CREATED_AT <", sql)

    def test_card_timeline_stmt_uses_datetime_range_not_func_date(self) -> None:
        stmt = memory_archive._build_card_session_timeline_stmt(
            clauses=[
                CardSession.mode == CardSessionMode.DECK,
                CardSession.status == CardSessionStatus.COMPLETED,
                CardSession.deleted_at.is_(None),
                CardSession.creator_id == self.user_id,
            ],
            before=self.before,
            cursor_last_id=None,
            from_date=date(2026, 2, 1),
            to_date=date(2026, 3, 2),
            fetch_n=20,
        )
        sql = str(
            stmt.compile(
                dialect=self.engine.dialect,
                compile_kwargs={"literal_binds": True},
            )
        ).upper()
        self.assertNotIn("DATE(", sql)
        self.assertIn("CREATED_AT >=", sql)
        self.assertIn("CREATED_AT <", sql)


if __name__ == "__main__":
    unittest.main()
