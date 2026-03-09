from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_session import CardSession, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services import memory_archive  # noqa: E402
from app.services.pagination import InvalidPageCursorError, PageCursor  # noqa: E402


class MemoryTimelineCursorPaginationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.ts = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

        self.journal_id_30 = uuid.UUID("00000000-0000-0000-0000-000000000030")
        self.journal_id_20 = uuid.UUID("00000000-0000-0000-0000-000000000020")
        self.journal_id_10 = uuid.UUID("00000000-0000-0000-0000-000000000010")
        self.session_id_25 = uuid.UUID("00000000-0000-0000-0000-000000000025")

        with Session(self.engine) as session:
            user = User(
                id=self.user_id,
                email="cursor-user@example.com",
                full_name="Cursor User",
                hashed_password="hashed",
            )
            card = Card(
                id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
                category=CardCategory.DAILY_VIBE,
                title="T",
                description="D",
                question="Q",
                difficulty_level=1,
                depth_level=1,
                tags=[],
            )
            session.add(user)
            session.add(card)

            session.add(
                Journal(
                    id=self.journal_id_30,
                    user_id=self.user_id,
                    title="J30",
                    content="J30",
                    created_at=self.ts,
                    updated_at=self.ts,
                )
            )
            session.add(
                Journal(
                    id=self.journal_id_20,
                    user_id=self.user_id,
                    title="J20",
                    content="J20",
                    created_at=self.ts,
                    updated_at=self.ts,
                )
            )
            session.add(
                Journal(
                    id=self.journal_id_10,
                    user_id=self.user_id,
                    title="J10",
                    content="J10",
                    created_at=self.ts,
                    updated_at=self.ts,
                )
            )
            session.add(
                CardSession(
                    id=self.session_id_25,
                    card_id=card.id,
                    category=CardCategory.DAILY_VIBE.value,
                    creator_id=self.user_id,
                    partner_id=None,
                    status=CardSessionStatus.COMPLETED,
                    created_at=self.ts,
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_cursor_pagination_uses_timestamp_and_id_tiebreak(self) -> None:
        all_item_ids: list[uuid.UUID] = []
        cursor: str | None = None

        with Session(self.engine) as session:
            while True:
                items, has_more, next_cursor = memory_archive.get_unified_timeline(
                    session=session,
                    user_id=self.user_id,
                    partner_id=None,
                    limit=2,
                    cursor=cursor,
                )
                self.assertLessEqual(len(items), 2)
                for item in items:
                    raw_id = item.get("id") or item.get("session_id")
                    self.assertIsNotNone(raw_id)
                    all_item_ids.append(uuid.UUID(str(raw_id)))

                if not has_more:
                    break
                self.assertIsNotNone(next_cursor)
                cursor = next_cursor

        self.assertEqual(
            all_item_ids,
            [
                self.journal_id_30,
                self.session_id_25,
                self.journal_id_20,
                self.journal_id_10,
            ],
        )
        self.assertEqual(len(set(all_item_ids)), 4)

    def test_cursor_pagination_limit_is_clamped_by_settings(self) -> None:
        with Session(self.engine) as session, patch.object(
            settings,
            "TIMELINE_CURSOR_MAX_LIMIT",
            2,
        ), patch.object(
            settings,
            "TIMELINE_CURSOR_QUERY_BUDGET",
            100,
        ):
            items, has_more, next_cursor = memory_archive.get_unified_timeline(
                session=session,
                user_id=self.user_id,
                partner_id=None,
                limit=999,
                cursor=None,
            )

        self.assertEqual(len(items), 2)
        self.assertTrue(has_more)
        self.assertIsNotNone(next_cursor)

    def test_cursor_signature_tampering_is_rejected(self) -> None:
        cursor = PageCursor(last_timestamp=self.ts, last_id=self.journal_id_20).encode()
        self.assertIsNotNone(cursor)
        import base64
        import json

        payload = json.loads(base64.b64decode(str(cursor).encode("utf-8")).decode("utf-8"))
        payload["sig"] = "0" * 64
        tampered = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        with self.assertRaises(InvalidPageCursorError):
            PageCursor.from_encoded(tampered)


if __name__ == "__main__":
    unittest.main()
