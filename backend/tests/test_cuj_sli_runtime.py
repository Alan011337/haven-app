import json
import sys
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.cuj_event import CujEvent  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.cuj_sli_runtime import (  # noqa: E402
    CUJ_METRIC_ANALYSIS_LAG_MS,
    CUJ_METRIC_JOURNAL_WRITE_MS,
    CUJ_METRIC_KEYS,
    build_cuj_sli_snapshot,
    evaluate_cuj_sli_snapshot,
)


class CujSliRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            self.user = User(
                email="cuj-sli-user@example.com",
                full_name="CUJ SLI User",
                hashed_password="hashed",
            )
            self.partner = User(
                email="cuj-sli-partner@example.com",
                full_name="CUJ SLI Partner",
                hashed_password="hashed",
            )
            session.add(self.user)
            session.add(self.partner)
            session.commit()
            session.refresh(self.user)
            session.refresh(self.partner)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _add_event(
        self,
        *,
        session: Session,
        event_name: str,
        event_id: str,
        metadata: dict | None = None,
        metadata_json: str | None = None,
    ) -> None:
        payload_json = metadata_json
        if payload_json is None and metadata is not None:
            payload_json = json.dumps(metadata, sort_keys=True)
        now = utcnow()
        session.add(
            CujEvent(
                user_id=self.user.id,
                partner_user_id=self.partner.id,
                event_name=event_name,
                event_id=event_id,
                source="test",
                mode="DAILY_RITUAL",
                session_id=None,
                request_id="req-test",
                dedupe_key=f"dedupe-{event_id}",
                metadata_json=payload_json,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )

    def test_cuj_metric_keys_are_stable(self) -> None:
        """CUJ/SLO: Canonical metric keys are stable for event metadata emission."""
        self.assertEqual(CUJ_METRIC_JOURNAL_WRITE_MS, "journal_write_ms")
        self.assertEqual(CUJ_METRIC_ANALYSIS_LAG_MS, "analysis_async_lag_ms")
        self.assertEqual(CUJ_METRIC_KEYS["journal_write"], CUJ_METRIC_JOURNAL_WRITE_MS)
        self.assertEqual(CUJ_METRIC_KEYS["analysis_lag"], CUJ_METRIC_ANALYSIS_LAG_MS)

    def test_build_snapshot_accepts_canonical_metric_keys(self) -> None:
        """CUJ/SLO: Snapshot extracts latency from canonical keys."""
        with Session(self.engine) as session:
            self._add_event(
                session=session,
                event_name="JOURNAL_PERSIST",
                event_id="persist-canonical",
                metadata={CUJ_METRIC_JOURNAL_WRITE_MS: 500},
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_ANALYSIS_DELIVERED",
                event_id="delivered-canonical",
                metadata={CUJ_METRIC_ANALYSIS_LAG_MS: 1200},
            )
            session.commit()
            snapshot = build_cuj_sli_snapshot(session=session, window_hours=24)
        self.assertEqual(snapshot["metrics"]["journal_write_p95_ms"], 500.0)
        self.assertEqual(snapshot["metrics"]["analysis_async_lag_p95_ms"], 1200.0)

    def test_build_snapshot_aggregates_counts_and_latency_metrics(self) -> None:
        with Session(self.engine) as session:
            self._add_event(session=session, event_name="RITUAL_DRAW", event_id="draw-1")
            self._add_event(session=session, event_name="RITUAL_DRAW", event_id="draw-2")
            self._add_event(session=session, event_name="RITUAL_DRAW", event_id="draw-3")
            self._add_event(session=session, event_name="RITUAL_UNLOCK", event_id="unlock-1")
            self._add_event(session=session, event_name="RITUAL_UNLOCK", event_id="unlock-2")
            self._add_event(session=session, event_name="BIND_START", event_id="bind-start-1")
            self._add_event(session=session, event_name="BIND_START", event_id="bind-start-2")
            self._add_event(session=session, event_name="BIND_SUCCESS", event_id="bind-success-1")
            self._add_event(session=session, event_name="BIND_SUCCESS", event_id="bind-success-2")
            self._add_event(session=session, event_name="JOURNAL_SUBMIT", event_id="journal-submit-1")
            self._add_event(session=session, event_name="JOURNAL_SUBMIT", event_id="journal-submit-2")
            self._add_event(
                session=session,
                event_name="JOURNAL_PERSIST",
                event_id="journal-persist-1",
                metadata={"journal_write_ms": 1000},
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_PERSIST",
                event_id="journal-persist-2",
                metadata={"journal_write_ms": 3000},
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_ANALYSIS_QUEUED",
                event_id="analysis-queued-1",
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_ANALYSIS_QUEUED",
                event_id="analysis-queued-2",
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_ANALYSIS_DELIVERED",
                event_id="analysis-delivered-1",
                metadata={"analysis_async_lag_ms": 1500},
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_ANALYSIS_DELIVERED",
                event_id="analysis-delivered-2",
                metadata={"analysis_async_lag_ms": 2500},
            )
            session.commit()

            snapshot = build_cuj_sli_snapshot(session=session, window_hours=24)

        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(snapshot["counts"]["ritual_draw_total"], 3)
        self.assertEqual(snapshot["counts"]["ritual_unlock_total"], 2)
        self.assertEqual(snapshot["counts"]["bind_start_total"], 2)
        self.assertEqual(snapshot["counts"]["bind_success_total"], 2)
        self.assertEqual(snapshot["metrics"]["ritual_success_rate"], 0.666667)
        self.assertEqual(snapshot["metrics"]["partner_binding_success_rate"], 1.0)
        self.assertEqual(snapshot["metrics"]["journal_write_p95_ms"], 2900.0)
        self.assertEqual(snapshot["metrics"]["analysis_async_lag_p95_ms"], 2450.0)
        self.assertEqual(snapshot["samples"]["journal_write_latency_samples"], 2)
        self.assertEqual(snapshot["samples"]["analysis_async_lag_samples"], 2)
        self.assertIn("ritual_success_rate", snapshot["targets"])

    def test_build_snapshot_ignores_invalid_latency_metadata(self) -> None:
        with Session(self.engine) as session:
            self._add_event(
                session=session,
                event_name="JOURNAL_PERSIST",
                event_id="journal-persist-invalid-json",
                metadata_json="{invalid",
            )
            self._add_event(
                session=session,
                event_name="JOURNAL_ANALYSIS_DELIVERED",
                event_id="analysis-delivered-non-numeric",
                metadata={"analysis_async_lag_ms": "slow"},
            )
            session.commit()
            snapshot = build_cuj_sli_snapshot(session=session, window_hours=24)

        self.assertIsNone(snapshot["metrics"]["journal_write_p95_ms"])
        self.assertIsNone(snapshot["metrics"]["analysis_async_lag_p95_ms"])
        self.assertEqual(snapshot["samples"]["journal_write_latency_samples"], 0)
        self.assertEqual(snapshot["samples"]["analysis_async_lag_samples"], 0)

    def test_evaluate_snapshot_degraded_when_targets_missed(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "ritual_draw_total": 50,
                "bind_start_total": 50,
            },
            "metrics": {
                "ritual_success_rate": 0.9,
                "partner_binding_success_rate": 0.98,
                "journal_write_p95_ms": 4200.0,
                "analysis_async_lag_p95_ms": 3500.0,
            },
            "samples": {
                "journal_write_latency_samples": 25,
                "analysis_async_lag_samples": 25,
            },
        }

        evaluation = evaluate_cuj_sli_snapshot(snapshot, min_rate_samples=20, min_latency_samples=10)

        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("ritual_success_rate_below_target", evaluation["reasons"])
        self.assertIn("partner_binding_success_rate_below_target", evaluation["reasons"])
        self.assertIn("journal_write_p95_above_target", evaluation["reasons"])
        self.assertNotIn("analysis_async_lag_p95_above_target", evaluation["reasons"])

    def test_evaluate_snapshot_insufficient_with_low_sample_counts(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "ritual_draw_total": 1,
                "bind_start_total": 1,
            },
            "metrics": {
                "ritual_success_rate": 1.0,
                "partner_binding_success_rate": 1.0,
                "journal_write_p95_ms": 2000.0,
                "analysis_async_lag_p95_ms": 2000.0,
            },
            "samples": {
                "journal_write_latency_samples": 1,
                "analysis_async_lag_samples": 1,
            },
        }

        evaluation = evaluate_cuj_sli_snapshot(snapshot)
        self.assertEqual(evaluation["status"], "insufficient_data")
        self.assertEqual(evaluation["reasons"], [])

    def test_evaluate_snapshot_degraded_when_ai_feedback_downvote_rate_above_target(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "ritual_draw_total": 50,
                "bind_start_total": 50,
                "journal_analysis_delivered_total": 100,
            },
            "metrics": {
                "ritual_success_rate": 1.0,
                "partner_binding_success_rate": 1.0,
                "journal_write_p95_ms": 2000.0,
                "analysis_async_lag_p95_ms": 2000.0,
                "ai_feedback_downvote_rate": 0.08,
            },
            "samples": {
                "journal_write_latency_samples": 25,
                "analysis_async_lag_samples": 25,
            },
        }
        evaluation = evaluate_cuj_sli_snapshot(snapshot, min_rate_samples=20, min_latency_samples=10)
        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("ai_feedback_downvote_rate_above_target", evaluation["reasons"])
        self.assertIn("ai_feedback_downvote_rate", evaluation["evaluated"])


if __name__ == "__main__":
    unittest.main()
