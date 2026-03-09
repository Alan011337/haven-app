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
from app.models.events_log_daily_rollup import EventsLogDailyRollup  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import events_log_rollup  # noqa: E402


class EventsLogRollupTests(unittest.TestCase):
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
                email=f"events-rollup-{uuid.uuid4().hex[:8]}@example.com",
                full_name="Events Rollup",
                hashed_password="hashed",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            old_ts = now - timedelta(days=60)
            new_ts = now - timedelta(days=2)
            session.add(
                EventsLog(
                    user_id=user.id,
                    partner_user_id=None,
                    event_name="daily_loop_completed",
                    event_id="rollup-old-1",
                    source="web",
                    ts=old_ts,
                    dedupe_key=f"{uuid.uuid4().hex}-rollup-old-1",
                )
            )
            session.add(
                EventsLog(
                    user_id=user.id,
                    partner_user_id=user.id,
                    event_name="daily_loop_completed",
                    event_id="rollup-old-2",
                    source="web",
                    ts=old_ts,
                    dedupe_key=f"{uuid.uuid4().hex}-rollup-old-2",
                )
            )
            session.add(
                EventsLog(
                    user_id=user.id,
                    partner_user_id=None,
                    event_name="daily_sync_submitted",
                    event_id="rollup-new-1",
                    source="web",
                    ts=new_ts,
                    dedupe_key=f"{uuid.uuid4().hex}-rollup-new-1",
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_rollup_dry_run_reports_selected_without_mutation(self) -> None:
        with patch.object(events_log_rollup, "engine", self.engine):
            summary = events_log_rollup.rollup_events_log_daily(
                retention_days=30,
                batch_size=100,
                apply=False,
            )

        self.assertFalse(summary["apply"])
        self.assertEqual(summary["selected"], 2)
        self.assertEqual(summary["rolled_up_rows"], 0)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(EventsLog)).all()), 3)
            self.assertEqual(len(session.exec(select(EventsLogDailyRollup)).all()), 0)

    def test_rollup_apply_aggregates_and_purges_batch(self) -> None:
        with patch.object(events_log_rollup, "engine", self.engine):
            summary = events_log_rollup.rollup_events_log_daily(
                retention_days=30,
                batch_size=100,
                apply=True,
            )

        self.assertTrue(summary["apply"])
        self.assertEqual(summary["selected"], 2)
        self.assertEqual(summary["purged"], 2)
        with Session(self.engine) as session:
            remaining = session.exec(select(EventsLog)).all()
            self.assertEqual(len(remaining), 1)
            rollups = session.exec(select(EventsLogDailyRollup)).all()
            self.assertEqual(len(rollups), 2)
            scopes = sorted(item.user_scope for item in rollups)
            self.assertEqual(scopes, ["paired", "solo"])


if __name__ == "__main__":
    unittest.main()
