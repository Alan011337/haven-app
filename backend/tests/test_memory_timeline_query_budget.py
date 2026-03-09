from __future__ import annotations

import sys
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.services import memory_archive  # noqa: E402
from app.services.pagination import (  # noqa: E402
    enforce_timeline_query_budget,
    estimate_timeline_query_budget,
)
from app.services.timeline_runtime_metrics import timeline_runtime_metrics  # noqa: E402


class MemoryTimelineQueryBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000111")
        self.before = datetime(2026, 3, 1, tzinfo=timezone.utc)

        with Session(self.engine) as session:
            session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_journals_user_created_id "
                    "ON journals (user_id, created_at DESC, id DESC)"
                )
            )
            session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_card_sessions_creator_created_id "
                    "ON card_sessions (creator_id, created_at DESC, id DESC)"
                )
            )
            session.commit()
        timeline_runtime_metrics.reset()

    def tearDown(self) -> None:
        timeline_runtime_metrics.reset()
        self.engine.dispose()

    def test_query_budget_estimation_and_enforcement(self) -> None:
        estimated = estimate_timeline_query_budget(fetch_limit=120, query_fanout=2, detail_query_count=2)
        self.assertEqual(estimated, 242)

        clamped = enforce_timeline_query_budget(
            fetch_limit=500,
            budget_units=200,
            query_fanout=2,
            detail_query_count=2,
        )
        # budget=200, formula=(fetch*2)+2 => max fetch by budget is 99
        self.assertEqual(clamped, 99)

    def test_timeline_statements_explain_plan_has_index_usage(self) -> None:
        journal_stmt = memory_archive._build_journal_timeline_stmt(
            user_ids=[self.user_id],
            before=self.before,
            cursor_last_id=None,
            from_date=date(2026, 2, 1),
            to_date=date(2026, 3, 2),
            fetch_n=20,
        )
        card_stmt = memory_archive._build_card_session_timeline_stmt(
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

        journal_sql = str(
            journal_stmt.compile(
                dialect=self.engine.dialect,
                compile_kwargs={"literal_binds": True},
            )
        )
        card_sql = str(
            card_stmt.compile(
                dialect=self.engine.dialect,
                compile_kwargs={"literal_binds": True},
            )
        )

        with Session(self.engine) as session:
            journal_plan = list(session.exec(text(f"EXPLAIN QUERY PLAN {journal_sql}")).all())
            card_plan = list(session.exec(text(f"EXPLAIN QUERY PLAN {card_sql}")).all())

        self.assertGreater(len(journal_plan), 0)
        self.assertGreater(len(card_plan), 0)

        journal_details = " ".join(str(row[-1]).upper() for row in journal_plan)
        card_details = " ".join(str(row[-1]).upper() for row in card_plan)
        self.assertIn("INDEX", journal_details)
        self.assertIn("INDEX", card_details)

    def test_unified_timeline_records_runtime_budget_metrics(self) -> None:
        fake_settings = SimpleNamespace(max_limit=500, query_budget=40)
        with patch.object(memory_archive, "get_timeline_cursor_settings", return_value=fake_settings):
            with Session(self.engine) as session:
                items, has_more, next_cursor = memory_archive.get_unified_timeline(
                    session=session,
                    user_id=self.user_id,
                    partner_id=None,
                    limit=400,
                )
        self.assertEqual(items, [])
        self.assertFalse(has_more)
        self.assertIsNone(next_cursor)
        snapshot = timeline_runtime_metrics.snapshot()
        self.assertEqual(snapshot.get("timeline_query_total"), 1)
        self.assertEqual(snapshot.get("timeline_budget_clamped_total"), 1)


if __name__ == "__main__":
    unittest.main()
