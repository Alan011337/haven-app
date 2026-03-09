from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.card_session import CardSession, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import memory_archive  # noqa: E402


class MemoryTimelineQueryCountGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        self.user_id = uuid.uuid4()
        self.partner_id = uuid.uuid4()
        base_ts = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

        with Session(self.engine) as session:
            session.add(
                User(
                    id=self.user_id,
                    email=f"timeline-count-a-{uuid.uuid4().hex[:8]}@example.com",
                    full_name="Timeline Counter A",
                    hashed_password="hashed",
                )
            )
            session.add(
                User(
                    id=self.partner_id,
                    email=f"timeline-count-b-{uuid.uuid4().hex[:8]}@example.com",
                    full_name="Timeline Counter B",
                    hashed_password="hashed",
                )
            )
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Count Card",
                description="D",
                question="Q",
                difficulty_level=1,
                depth_level=1,
                tags=[],
            )
            session.add(card)
            session.flush()

            for idx in range(6):
                ts = base_ts.replace(minute=idx)
                session.add(
                    Journal(
                        user_id=self.user_id,
                        title=f"J-{idx}",
                        content=f"content-{idx}",
                        created_at=ts,
                        updated_at=ts,
                    )
                )
            for idx in range(4):
                ts = base_ts.replace(minute=20 + idx)
                card_session = CardSession(
                    card_id=card.id,
                    category=CardCategory.DAILY_VIBE.value,
                    creator_id=self.user_id,
                    partner_id=self.partner_id,
                    status=CardSessionStatus.COMPLETED,
                    created_at=ts,
                )
                session.add(card_session)
                session.flush()
                session.add(
                    CardResponse(
                        session_id=card_session.id,
                        card_id=card.id,
                        user_id=self.user_id,
                        content=f"a-{idx}",
                    )
                )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def _measure_query_count(self, *, cursor: str | None) -> tuple[int, str | None]:
        counter = {"count": 0}

        def _before_cursor_execute(*args, **kwargs):
            counter["count"] += 1

        event.listen(self.engine, "before_cursor_execute", _before_cursor_execute)
        try:
            with Session(self.engine) as session:
                _, _, next_cursor = memory_archive.get_unified_timeline(
                    session=session,
                    user_id=self.user_id,
                    partner_id=self.partner_id,
                    limit=5,
                    cursor=cursor,
                )
            return counter["count"], next_cursor
        finally:
            event.remove(self.engine, "before_cursor_execute", _before_cursor_execute)

    def test_query_count_is_bounded_per_page(self) -> None:
        first_count, next_cursor = self._measure_query_count(cursor=None)
        self.assertLessEqual(first_count, 9, msg=f"first page query count too high: {first_count}")
        self.assertIsNotNone(next_cursor)
        second_count, _ = self._measure_query_count(cursor=next_cursor)
        self.assertLessEqual(second_count, 9, msg=f"second page query count too high: {second_count}")


if __name__ == "__main__":
    unittest.main()
