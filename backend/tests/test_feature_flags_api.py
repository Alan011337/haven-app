# READ_AUTHZ_MATRIX: GET /api/users/feature-flags

import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402


class FeatureFlagsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        self.current_user_id = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id is not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(email="flags-a@example.com", full_name="Flags A", hashed_password="hashed")
            user_b = User(email="flags-b@example.com", full_name="Flags B", hashed_password="hashed")
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

        self.current_user_id = self.user_a_id
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_referral_enabled": true, '
            '"growth_ab_experiment_enabled": true, '
            '"growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_referral_funnel": true, "disable_pricing_experiment": true}'
        )

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.client.close()
        self.engine.dispose()

    def test_feature_flags_returns_effective_flags_for_current_user(self) -> None:
        response = self.client.get("/api/users/feature-flags")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_partner_context"])
        self.assertTrue(payload["kill_switches"]["disable_referral_funnel"])
        self.assertTrue(payload["kill_switches"]["disable_pricing_experiment"])
        self.assertFalse(payload["kill_switches"]["disable_growth_ab_experiment"])
        self.assertFalse(payload["kill_switches"]["disable_growth_reengagement_hooks"])
        self.assertFalse(payload["kill_switches"]["disable_growth_activation_dashboard"])
        self.assertFalse(payload["kill_switches"]["disable_growth_onboarding_quest"])
        self.assertFalse(payload["kill_switches"]["disable_growth_sync_nudges"])
        self.assertFalse(payload["kill_switches"]["disable_growth_first_delight"])
        self.assertFalse(payload["kill_switches"]["disable_weekly_review_v1"])
        self.assertFalse(payload["kill_switches"]["disable_repair_flow_v1"])
        self.assertFalse(payload["flags"]["growth_referral_enabled"])
        self.assertTrue(payload["flags"]["growth_ab_experiment_enabled"])
        self.assertFalse(payload["flags"]["growth_pricing_experiment_enabled"])
        self.assertFalse(payload["flags"]["weekly_review_v1"])
        self.assertFalse(payload["flags"]["repair_flow_v1"])
        self.assertNotIn("user_id", payload)
        self.assertNotIn("partner_id", payload)

    def test_feature_flags_ignores_overposted_user_id_query(self) -> None:
        baseline = self.client.get("/api/users/feature-flags")
        self.assertEqual(baseline.status_code, 200)

        overposted = self.client.get(
            "/api/users/feature-flags",
            params={"user_id": str(self.user_b_id)},
        )
        self.assertEqual(overposted.status_code, 200)
        self.assertEqual(overposted.json(), baseline.json())

    def test_partner_dependent_flag_turns_off_when_user_has_no_partner(self) -> None:
        with Session(self.engine) as session:
            user_b = session.get(User, self.user_b_id)
            user_a = session.get(User, self.user_a_id)
            self.assertIsNotNone(user_a)
            self.assertIsNotNone(user_b)
            assert user_a is not None
            assert user_b is not None
            user_a.partner_id = None
            user_b.partner_id = None
            session.add(user_a)
            session.add(user_b)
            session.commit()

        response = self.client.get("/api/users/feature-flags")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["has_partner_context"])
        self.assertFalse(payload["flags"]["growth_referral_enabled"])


if __name__ == "__main__":
    unittest.main()
