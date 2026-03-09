from __future__ import annotations

import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.events_log import EventsLog  # noqa: E402
from app.models.user import User  # noqa: F401,E402
from app.services import events_log_retention  # noqa: E402


class EventsLogRetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        now = utcnow()
        with Session(self.engine) as session:
            user = User(
                email="events-retention@example.com",
                full_name="Events Retention",
                hashed_password="hashed",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            old_ts = now - timedelta(days=120)
            recent_ts = now - timedelta(days=2)
            session.add(
                EventsLog(
                    user_id=user.id,
                    partner_user_id=None,
                    event_name="daily_loop_completed",
                    event_id="old-1",
                    source="test",
                    ts=old_ts,
                    dedupe_key=f"{uuid.uuid4().hex}-old",
                )
            )
            session.add(
                EventsLog(
                    user_id=user.id,
                    partner_user_id=None,
                    event_name="daily_card_revealed",
                    event_id="new-1",
                    source="test",
                    ts=recent_ts,
                    dedupe_key=f"{uuid.uuid4().hex}-new",
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_cleanup_events_log_dry_run_only_reports_matches(self) -> None:
        with patch.object(events_log_retention, "engine", self.engine):
            summary = events_log_retention.cleanup_events_log(
                retention_days=30,
                batch_size=100,
                apply=False,
            )

        self.assertFalse(summary["apply"])
        self.assertEqual(summary["matched"], 1)
        self.assertEqual(summary["purged"], 0)
        with Session(self.engine) as session:
            rows = session.exec(select(EventsLog)).all()
            self.assertEqual(len(rows), 2)

    def test_cleanup_events_log_apply_respects_batch_size(self) -> None:
        with Session(self.engine) as session:
            user = session.exec(select(User)).first()
            assert user is not None
            old_ts = utcnow() - timedelta(days=90)
            session.add(
                EventsLog(
                    user_id=user.id,
                    partner_user_id=None,
                    event_name="appreciation_sent",
                    event_id="old-2",
                    source="test",
                    ts=old_ts,
                    dedupe_key=f"{uuid.uuid4().hex}-old-2",
                )
            )
            session.commit()

        with patch.object(events_log_retention, "engine", self.engine):
            first = events_log_retention.cleanup_events_log(
                retention_days=30,
                batch_size=1,
                apply=True,
            )
            second = events_log_retention.cleanup_events_log(
                retention_days=30,
                batch_size=10,
                apply=True,
            )

        self.assertEqual(first["purged"], 1)
        self.assertEqual(second["purged"], 1)
        with Session(self.engine) as session:
            remaining = session.exec(select(EventsLog)).all()
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0].event_id, "new-1")


if __name__ == "__main__":
    unittest.main()
