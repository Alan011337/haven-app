import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.push_subscription import PushSubscription, PushSubscriptionState  # noqa: E402
from app.services.push_sli_runtime import (  # noqa: E402
    build_push_sli_snapshot,
    evaluate_push_sli_snapshot,
    push_runtime_metrics,
)


class PushSliRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine, tables=[PushSubscription.__table__])
        push_runtime_metrics.reset()

    def tearDown(self) -> None:
        self.engine.dispose()

    def _create_subscription(
        self,
        *,
        state: PushSubscriptionState,
        updated_at_delta_days: int = 0,
    ) -> None:
        now = utcnow()
        with Session(self.engine) as session:
            row = PushSubscription(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                endpoint=f"https://example.com/{uuid.uuid4()}",
                endpoint_hash=f"hash-{uuid.uuid4()}",
                p256dh_key="p256dh-key",
                auth_key="auth-key",
                state=state,
                created_at=now,
                updated_at=now - timedelta(days=updated_at_delta_days),
            )
            session.add(row)
            session.commit()

    def test_snapshot_and_evaluation_are_insufficient_without_dispatch_samples(self) -> None:
        self._create_subscription(state=PushSubscriptionState.ACTIVE)
        with Session(self.engine) as session:
            snapshot = build_push_sli_snapshot(session=session)
        evaluation = evaluate_push_sli_snapshot(snapshot)
        self.assertEqual(snapshot["counts"]["active_subscriptions"], 1)
        self.assertEqual(evaluation["status"], "insufficient_data")

    def test_evaluation_degraded_when_cleanup_backlog_exceeds_target(self) -> None:
        self._create_subscription(
            state=PushSubscriptionState.INVALID,
            updated_at_delta_days=15,
        )
        with patch(
            "app.services.push_sli_runtime.settings.HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX",
            0,
        ):
            with Session(self.engine) as session:
                snapshot = build_push_sli_snapshot(session=session)
            evaluation = evaluate_push_sli_snapshot(snapshot)
        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("push_cleanup_backlog_above_target", evaluation["reasons"])

    def test_evaluation_degraded_when_dry_run_latency_p95_above_target(self) -> None:
        self._create_subscription(state=PushSubscriptionState.ACTIVE)
        push_runtime_metrics.record_dry_run(sampled_count=1, latency_ms=3000.0)
        push_runtime_metrics.record_dry_run(sampled_count=1, latency_ms=2800.0)
        push_runtime_metrics.record_dry_run(sampled_count=1, latency_ms=2600.0)

        with patch(
            "app.services.push_sli_runtime.settings.HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES",
            1,
        ), patch(
            "app.services.push_sli_runtime.settings.HEALTH_PUSH_DRY_RUN_P95_MS_TARGET",
            500.0,
        ):
            with Session(self.engine) as session:
                snapshot = build_push_sli_snapshot(session=session)
            evaluation = evaluate_push_sli_snapshot(snapshot)
        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("push_dry_run_latency_p95_above_target", evaluation["reasons"])


if __name__ == "__main__":
    unittest.main()
