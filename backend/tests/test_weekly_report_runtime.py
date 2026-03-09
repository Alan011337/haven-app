from __future__ import annotations

import unittest
from datetime import timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.core.datetime_utils import utcnow
from app.models.appreciation import Appreciation
from app.models.daily_sync import DailySync
from app.models.user import User
from app.services.weekly_report_runtime import DAYS_IN_WEEK, get_weekly_report


class WeeklyReportRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            self.user_a = User(
                email="weekly-report-a@example.com",
                full_name="Weekly Report A",
                hashed_password="hashed",
            )
            self.user_b = User(
                email="weekly-report-b@example.com",
                full_name="Weekly Report B",
                hashed_password="hashed",
            )
            session.add(self.user_a)
            session.add(self.user_b)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            self.user_a_id = self.user_a.id
            self.user_b_id = self.user_b.id

            today = utcnow().date()
            # user A: 4 days filled
            for offset in (0, 1, 2, 4):
                session.add(
                    DailySync(
                        user_id=self.user_a_id,
                        sync_date=today - timedelta(days=offset),
                        mood_score=4,
                        question_id=f"q-a-{offset}",
                        answer_text="ok",
                    )
                )
            # duplicate same day should not inflate count
            session.add(
                DailySync(
                    user_id=self.user_a_id,
                    sync_date=today,
                    mood_score=5,
                    question_id="q-a-dup",
                    answer_text="dup",
                )
            )
            # user B: 3 days filled, overlap with A on offsets 0 and 2
            for offset in (0, 2, 6):
                session.add(
                    DailySync(
                        user_id=self.user_b_id,
                        sync_date=today - timedelta(days=offset),
                        mood_score=3,
                        question_id=f"q-b-{offset}",
                        answer_text="ok",
                    )
                )

            session.add(
                Appreciation(
                    user_id=self.user_a_id,
                    partner_id=self.user_b_id,
                    body_text="Thanks",
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_weekly_report_includes_pair_alignment_metrics(self) -> None:
        with Session(self.engine) as session:
            payload = get_weekly_report(session, self.user_a_id, self.user_b_id)

        self.assertEqual(payload["daily_sync_days_filled"], 4)
        self.assertEqual(payload["partner_daily_sync_days_filled"], 3)
        self.assertEqual(payload["pair_sync_overlap_days"], 2)
        self.assertEqual(payload["daily_sync_completion_rate"], round(4 / DAYS_IN_WEEK, 2))
        self.assertEqual(payload["pair_sync_alignment_rate"], round(2 / DAYS_IN_WEEK, 2))
        self.assertEqual(payload["appreciation_count"], 1)

    def test_weekly_report_without_partner_keeps_pair_metrics_zero_or_none(self) -> None:
        with Session(self.engine) as session:
            payload = get_weekly_report(session, self.user_a_id, None)

        self.assertEqual(payload["partner_daily_sync_days_filled"], 0)
        self.assertEqual(payload["pair_sync_overlap_days"], 0)
        self.assertIsNone(payload["pair_sync_alignment_rate"])


if __name__ == "__main__":
    unittest.main()
