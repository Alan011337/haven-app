# READ_AUTHZ_MATRIX: GET /api/users/onboarding-quest

import sys
import unittest
import uuid
from datetime import timedelta
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
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class OnboardingQuestApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        self.current_user_id: uuid.UUID | None = None

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

        now = utcnow()
        terms_at = now - timedelta(days=14)
        with Session(self.engine) as session:
            user_a = User(
                email="onboarding-a@example.com",
                full_name="Onboarding A",
                hashed_password="hashed",
                terms_accepted_at=terms_at,
            )
            user_b = User(
                email="onboarding-b@example.com",
                full_name="Onboarding B",
                hashed_password="hashed",
                terms_accepted_at=terms_at,
            )
            outsider = User(
                email="onboarding-outsider@example.com",
                full_name="Onboarding Outsider",
                hashed_password="hashed",
                terms_accepted_at=terms_at,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(outsider)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(outsider)

            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)

            session.add(
                Journal(
                    user_id=user_a.id,
                    content="a-day-1",
                    created_at=now - timedelta(days=1),
                )
            )
            session.add(
                Journal(
                    user_id=user_a.id,
                    content="a-day-2",
                    created_at=now,
                )
            )
            session.add(
                Journal(
                    user_id=user_b.id,
                    content="b-day-1",
                    created_at=now - timedelta(days=1),
                )
            )
            session.add(
                Journal(
                    user_id=user_b.id,
                    content="b-day-2",
                    created_at=now,
                )
            )

            session.add(
                CardResponse(
                    user_id=user_a.id,
                    card_id=uuid.uuid4(),
                    content="card-response-a",
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    user_id=user_b.id,
                    card_id=uuid.uuid4(),
                    content="card-response-b",
                    is_initiator=False,
                )
            )
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.outsider_id = outsider.id

        self.current_user_id = self.user_a_id
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"growth_onboarding_quest_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_onboarding_quest": false}'

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.client.close()
        self.engine.dispose()

    def test_onboarding_quest_returns_completed_progress_for_eligible_pair(self) -> None:
        response = self.client.get("/api/users/onboarding-quest")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["has_partner_context"])
        self.assertFalse(payload["kill_switch_active"])
        self.assertEqual(payload["total_steps"], 7)
        self.assertEqual(payload["completed_steps"], 7)
        self.assertEqual(payload["progress_percent"], 100.0)
        self.assertEqual(len(payload["steps"]), 7)

        step_map = {step["key"]: step for step in payload["steps"]}
        self.assertTrue(step_map["PAIR_STREAK_2_DAYS"]["completed"])
        self.assertEqual(step_map["PAIR_STREAK_2_DAYS"]["reason"], "eligible")
        self.assertEqual(step_map["PAIR_STREAK_2_DAYS"]["metadata"]["shared_journal_days"], 2)
        self.assertEqual(step_map["PAIR_CARD_EXCHANGE"]["metadata"]["pair_card_response_count"], 2)

        serialized = str(payload).lower()
        self.assertNotIn("onboarding-a@example.com", serialized)
        self.assertNotIn("onboarding-b@example.com", serialized)

    def test_onboarding_quest_marks_partner_steps_pending_without_partner(self) -> None:
        self.current_user_id = self.outsider_id
        response = self.client.get("/api/users/onboarding-quest")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["enabled"])
        self.assertFalse(payload["has_partner_context"])
        self.assertLess(payload["completed_steps"], payload["total_steps"])

        step_map = {step["key"]: step for step in payload["steps"]}
        self.assertFalse(step_map["BIND_PARTNER"]["completed"])
        self.assertEqual(step_map["BIND_PARTNER"]["reason"], "partner_not_bound")
        self.assertFalse(step_map["PAIR_CARD_EXCHANGE"]["completed"])
        self.assertEqual(step_map["PAIR_CARD_EXCHANGE"]["reason"], "partner_required")
        self.assertFalse(step_map["PAIR_STREAK_2_DAYS"]["completed"])
        self.assertEqual(step_map["PAIR_STREAK_2_DAYS"]["reason"], "partner_required")

    def test_onboarding_quest_ignores_overposted_user_id_query(self) -> None:
        baseline = self.client.get("/api/users/onboarding-quest")
        self.assertEqual(baseline.status_code, 200)

        overposted = self.client.get(
            "/api/users/onboarding-quest",
            params={"user_id": str(self.user_b_id)},
        )
        self.assertEqual(overposted.status_code, 200)
        self.assertEqual(overposted.json(), baseline.json())

    def test_kill_switch_disables_onboarding_quest(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_onboarding_quest": true}'
        response = self.client.get("/api/users/onboarding-quest")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["enabled"])
        self.assertTrue(payload["kill_switch_active"])
        self.assertEqual(payload["completed_steps"], 0)
        self.assertEqual(payload["progress_percent"], 0.0)
        self.assertEqual(payload["steps"], [])

    def test_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            response = client.get("/api/users/onboarding-quest")
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
