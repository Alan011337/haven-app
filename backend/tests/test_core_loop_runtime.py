from __future__ import annotations

import unittest
from datetime import timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.core.datetime_utils import utcnow
from app.models.events_log import EventsLog
from app.models.user import User
from app.services.core_loop_runtime import (
    build_core_loop_snapshot,
    evaluate_core_loop_snapshot,
)


class CoreLoopRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            self.user_a = User(
                email="core-loop-runtime-a@example.com",
                full_name="Core Loop Runtime A",
                hashed_password="hashed",
            )
            self.user_b = User(
                email="core-loop-runtime-b@example.com",
                full_name="Core Loop Runtime B",
                hashed_password="hashed",
            )
            self.user_c = User(
                email="core-loop-runtime-c@example.com",
                full_name="Core Loop Runtime C",
                hashed_password="hashed",
            )
            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)

            now = utcnow()
            rows = [
                EventsLog(
                    user_id=self.user_a.id,
                    partner_user_id=self.user_b.id,
                    event_name="daily_sync_submitted",
                    event_id="evt-sync-a",
                    source="test",
                    ts=now,
                    dedupe_key="dedupe-sync-a",
                ),
                EventsLog(
                    user_id=self.user_a.id,
                    partner_user_id=self.user_b.id,
                    event_name="daily_card_revealed",
                    event_id="evt-reveal-a",
                    source="test",
                    ts=now,
                    dedupe_key="dedupe-reveal-a",
                ),
                EventsLog(
                    user_id=self.user_a.id,
                    partner_user_id=self.user_b.id,
                    event_name="card_answer_submitted",
                    event_id="evt-answer-a",
                    source="test",
                    ts=now,
                    dedupe_key="dedupe-answer-a",
                ),
                EventsLog(
                    user_id=self.user_a.id,
                    partner_user_id=self.user_b.id,
                    event_name="appreciation_sent",
                    event_id="evt-app-a",
                    source="test",
                    ts=now,
                    dedupe_key="dedupe-app-a",
                ),
                EventsLog(
                    user_id=self.user_a.id,
                    partner_user_id=self.user_b.id,
                    event_name="daily_loop_completed",
                    event_id="evt-loop-a",
                    source="test",
                    ts=now,
                    dedupe_key="dedupe-loop-a",
                ),
                EventsLog(
                    user_id=self.user_b.id,
                    partner_user_id=self.user_a.id,
                    event_name="daily_card_revealed",
                    event_id="evt-reveal-b",
                    source="test",
                    ts=now,
                    dedupe_key="dedupe-reveal-b",
                ),
                EventsLog(
                    user_id=self.user_c.id,
                    partner_user_id=None,
                    event_name="daily_sync_submitted",
                    event_id="evt-sync-c",
                    source="test",
                    ts=now - timedelta(minutes=1),
                    dedupe_key="dedupe-sync-c",
                ),
            ]
            session.add_all(rows)
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_build_snapshot_computes_completion_and_dual_reveal_rates(self) -> None:
        with Session(self.engine) as session:
            snapshot = build_core_loop_snapshot(session=session, window_days=1)

        self.assertEqual(snapshot["status"], "ok")
        counts = snapshot["counts"]
        metrics = snapshot["metrics"]

        self.assertEqual(counts["active_users_total"], 3)
        self.assertEqual(counts["loop_completed_users_total"], 1)
        self.assertEqual(counts["derived_loop_completed_users_total"], 1)
        self.assertEqual(counts["reveal_pairs_total"], 1)
        self.assertEqual(counts["reveal_pairs_dual_total"], 1)

        self.assertAlmostEqual(metrics["daily_loop_completion_rate"], 0.333333, places=6)
        self.assertAlmostEqual(metrics["derived_loop_completion_rate"], 0.333333, places=6)
        self.assertEqual(metrics["dual_reveal_pair_rate"], 1.0)

    def test_evaluate_snapshot_reports_degraded_below_targets(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "active_users_total": 10,
                "loop_completed_users_total": 2,
                "reveal_pairs_total": 5,
                "reveal_pairs_dual_total": 1,
            },
            "metrics": {
                "daily_loop_completion_rate": 0.2,
                "dual_reveal_pair_rate": 0.2,
            },
        }

        evaluation = evaluate_core_loop_snapshot(
            snapshot,
            min_active_users=5,
            target_daily_loop_completion_rate=0.35,
            target_dual_reveal_pair_rate=0.4,
        )

        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("daily_loop_completion_rate_below_target", evaluation["reasons"])
        self.assertIn("dual_reveal_pair_rate_below_target", evaluation["reasons"])

    def test_evaluate_snapshot_reports_insufficient_data_when_sample_too_small(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "active_users_total": 1,
                "loop_completed_users_total": 1,
                "reveal_pairs_total": 0,
                "reveal_pairs_dual_total": 0,
            },
            "metrics": {
                "daily_loop_completion_rate": 1.0,
                "dual_reveal_pair_rate": None,
            },
        }

        evaluation = evaluate_core_loop_snapshot(snapshot, min_active_users=3)
        self.assertEqual(evaluation["status"], "insufficient_data")
        self.assertEqual(evaluation["reasons"], [])


if __name__ == "__main__":
    unittest.main()
