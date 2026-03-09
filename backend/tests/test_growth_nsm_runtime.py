import sys
import unittest
import uuid
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.cuj_event import CujEvent  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.growth_nsm_runtime import (  # noqa: E402
    build_growth_nsm_snapshot,
    evaluate_growth_nsm_snapshot,
)


class GrowthNsmRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            self.user_a = User(
                email="growth-user-a@example.com",
                full_name="Growth User A",
                hashed_password="hashed",
            )
            self.user_b = User(
                email="growth-user-b@example.com",
                full_name="Growth User B",
                hashed_password="hashed",
            )
            self.user_c = User(
                email="growth-user-c@example.com",
                full_name="Growth User C",
                hashed_password="hashed",
            )
            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _add_event(
        self,
        *,
        session: Session,
        actor: User,
        partner: User,
        event_name: str,
        event_id: str,
        session_id: uuid.UUID | None = None,
    ) -> None:
        now = utcnow()
        session.add(
            CujEvent(
                user_id=actor.id,
                partner_user_id=partner.id,
                event_name=event_name,
                event_id=event_id,
                source="test",
                mode="DAILY_RITUAL",
                session_id=session_id,
                request_id="req-growth-nsm",
                dedupe_key=f"dedupe-{event_id}",
                metadata_json=None,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )

    def test_build_snapshot_counts_wrm_pair_when_both_partners_participate(self) -> None:
        with Session(self.engine) as session:
            self._add_event(
                session=session,
                actor=self.user_a,
                partner=self.user_b,
                event_name="RITUAL_RESPOND",
                event_id="evt-a-respond-1",
                session_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
            )
            self._add_event(
                session=session,
                actor=self.user_b,
                partner=self.user_a,
                event_name="RITUAL_UNLOCK",
                event_id="evt-b-unlock-1",
                session_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
            )
            session.commit()

            snapshot = build_growth_nsm_snapshot(session=session, window_days=7)

        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(snapshot["counts"]["active_pairs_observed_total"], 1)
        self.assertEqual(snapshot["counts"]["wrm_pairs_total"], 1)
        self.assertEqual(snapshot["metrics"]["wrm_active_pair_rate"], 1.0)
        self.assertEqual(snapshot["counts"]["events_by_name"]["RITUAL_RESPOND"], 1)
        self.assertEqual(snapshot["counts"]["events_by_name"]["RITUAL_UNLOCK"], 1)

    def test_build_snapshot_marks_one_sided_pair_as_not_wrm(self) -> None:
        with Session(self.engine) as session:
            self._add_event(
                session=session,
                actor=self.user_a,
                partner=self.user_c,
                event_name="JOURNAL_SUBMIT",
                event_id="evt-a-journal-1",
            )
            session.commit()
            snapshot = build_growth_nsm_snapshot(session=session, window_days=7)

        self.assertEqual(snapshot["counts"]["active_pairs_observed_total"], 1)
        self.assertEqual(snapshot["counts"]["wrm_pairs_total"], 0)
        self.assertEqual(snapshot["counts"]["one_sided_pairs_total"], 1)
        self.assertEqual(snapshot["metrics"]["wrm_active_pair_rate"], 0.0)

    def test_evaluate_snapshot_reports_degraded_when_target_is_missed(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "eligible_events_total": 30,
                "active_pairs_observed_total": 5,
                "wrm_pairs_total": 1,
            },
            "metrics": {
                "wrm_active_pair_rate": 0.2,
            },
        }
        evaluation = evaluate_growth_nsm_snapshot(
            snapshot,
            min_events=10,
            min_pairs=3,
            target_wrm_active_pair_rate=0.5,
        )
        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("wrm_active_pair_rate_below_target", evaluation["reasons"])

    def test_evaluate_snapshot_reports_insufficient_data_with_low_samples(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "eligible_events_total": 1,
                "active_pairs_observed_total": 1,
                "wrm_pairs_total": 1,
            },
            "metrics": {
                "wrm_active_pair_rate": 1.0,
            },
        }
        evaluation = evaluate_growth_nsm_snapshot(snapshot, min_events=10, min_pairs=3)
        self.assertEqual(evaluation["status"], "insufficient_data")
        self.assertEqual(evaluation["reasons"], [])


if __name__ == "__main__":
    unittest.main()
