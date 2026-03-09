import sys
import unittest
import uuid
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.growth_referral_event import GrowthReferralEvent, GrowthReferralEventType  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.growth_activation_runtime import (  # noqa: E402
    build_growth_activation_funnel_snapshot,
    evaluate_growth_activation_funnel_snapshot,
)


class GrowthActivationRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"growth_activation_dashboard_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_activation_dashboard": false}'

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.engine.dispose()

    def test_build_snapshot_counts_activation_and_referral_companion(self) -> None:
        now = utcnow()
        with Session(self.engine) as session:
            user_a = User(
                email="activation-a@example.com",
                full_name="Activation A",
                hashed_password="hashed",
                terms_accepted_at=now,
            )
            user_b = User(
                email="activation-b@example.com",
                full_name="Activation B",
                hashed_password="hashed",
                terms_accepted_at=now,
            )
            user_c = User(
                email="activation-c@example.com",
                full_name="Activation C",
                hashed_password="hashed",
                terms_accepted_at=now,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)

            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)

            session.add(
                Journal(
                    user_id=user_a.id,
                    content="journal from a",
                    title=None,
                    mood=None,
                    tags=None,
                    deck_id=None,
                    card_id=None,
                    deleted_at=None,
                )
            )
            session.add(
                Journal(
                    user_id=user_b.id,
                    content="journal from b",
                    title=None,
                    mood=None,
                    tags=None,
                    deck_id=None,
                    card_id=None,
                    deleted_at=None,
                )
            )
            session.add(
                CardResponse(
                    user_id=user_a.id,
                    card_id=uuid.uuid4(),
                    content="deck response",
                    session_id=None,
                    is_initiator=True,
                )
            )

            session.add(
                GrowthReferralEvent(
                    event_type=GrowthReferralEventType.LANDING_VIEW,
                    source="landing",
                    invite_code_hash="a" * 64,
                    dedupe_key="d" * 64,
                    inviter_user_id=user_a.id,
                    actor_user_id=None,
                    metadata_json=None,
                )
            )
            session.add(
                GrowthReferralEvent(
                    event_type=GrowthReferralEventType.SIGNUP,
                    source="signup",
                    invite_code_hash="b" * 64,
                    dedupe_key="e" * 64,
                    inviter_user_id=user_a.id,
                    actor_user_id=user_b.id,
                    metadata_json=None,
                )
            )
            session.add(
                GrowthReferralEvent(
                    event_type=GrowthReferralEventType.COUPLE_INVITE,
                    source="partner_settings",
                    invite_code_hash="c" * 64,
                    dedupe_key="f" * 64,
                    inviter_user_id=user_a.id,
                    actor_user_id=user_a.id,
                    metadata_json=None,
                )
            )
            session.add(
                GrowthReferralEvent(
                    event_type=GrowthReferralEventType.BIND,
                    source="pair",
                    invite_code_hash="d" * 64,
                    dedupe_key="0" * 64,
                    inviter_user_id=user_a.id,
                    actor_user_id=user_b.id,
                    metadata_json=None,
                )
            )
            session.commit()

            snapshot = build_growth_activation_funnel_snapshot(session=session, window_days=30)

        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(snapshot["counts"]["signup_completed_users"], 3)
        self.assertEqual(snapshot["counts"]["partner_bound_users"], 2)
        self.assertEqual(snapshot["counts"]["first_journal_users"], 2)
        self.assertEqual(snapshot["counts"]["first_deck_users"], 1)
        self.assertEqual(snapshot["metrics"]["bind_rate"], round(2 / 3, 6))
        self.assertEqual(snapshot["metrics"]["first_journal_rate"], round(2 / 3, 6))
        self.assertEqual(snapshot["metrics"]["first_deck_rate"], round(1 / 3, 6))
        self.assertEqual(snapshot["referral_companion"]["counts"]["LANDING_VIEW"], 1)
        self.assertEqual(snapshot["referral_companion"]["counts"]["SIGNUP"], 1)
        self.assertEqual(snapshot["referral_companion"]["counts"]["COUPLE_INVITE"], 1)
        self.assertEqual(snapshot["referral_companion"]["counts"]["BIND"], 1)

    def test_evaluate_snapshot_reports_degraded_when_targets_missed(self) -> None:
        snapshot = {
            "status": "ok",
            "counts": {
                "signup_completed_users": 20,
                "partner_bound_users": 2,
                "first_journal_users": 1,
                "first_deck_users": 0,
            },
            "metrics": {
                "bind_rate": 0.1,
                "first_journal_rate": 0.05,
                "first_deck_rate": 0.0,
            },
        }
        evaluation = evaluate_growth_activation_funnel_snapshot(
            snapshot,
            min_signups=10,
            target_bind_rate=0.3,
            target_first_journal_rate=0.2,
            target_first_deck_rate=0.1,
        )
        self.assertEqual(evaluation["status"], "degraded")
        self.assertIn("bind_rate_below_target", evaluation["reasons"])
        self.assertIn("first_journal_rate_below_target", evaluation["reasons"])
        self.assertIn("first_deck_rate_below_target", evaluation["reasons"])

    def test_build_snapshot_returns_disabled_when_kill_switch_enabled(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_activation_dashboard": true}'
        with Session(self.engine) as session:
            snapshot = build_growth_activation_funnel_snapshot(session=session, window_days=30)
        self.assertEqual(snapshot["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
