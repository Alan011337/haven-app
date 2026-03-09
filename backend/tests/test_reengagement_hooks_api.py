# READ_AUTHZ_MATRIX: GET /api/users/reengagement-hooks

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


class ReengagementHooksApiTests(unittest.TestCase):
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
        old_terms = now - timedelta(days=40)
        with Session(self.engine) as session:
            user_a = User(
                email="reengage-a@example.com",
                full_name="Reengage A",
                hashed_password="hashed",
                terms_accepted_at=old_terms,
            )
            user_b = User(
                email="reengage-b@example.com",
                full_name="Reengage B",
                hashed_password="hashed",
                terms_accepted_at=old_terms,
            )
            outsider = User(
                email="reengage-outsider@example.com",
                full_name="Reengage Outsider",
                hashed_password="hashed",
                terms_accepted_at=old_terms,
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

            for idx in range(3):
                session.add(
                    Journal(
                        user_id=user_a.id,
                        content=f"user-a-journal-{idx}",
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
                        content=f"user-b-journal-{idx}",
                        title=None,
                        mood=None,
                        tags=None,
                        deck_id=None,
                        card_id=None,
                        deleted_at=None,
                    )
                )

            # outsider activity should not leak into pair counts
            for idx in range(4):
                session.add(
                    Journal(
                        user_id=outsider.id,
                        content=f"outsider-journal-{idx}",
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
                    content="card-response-a",
                    session_id=None,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    user_id=user_b.id,
                    card_id=uuid.uuid4(),
                    content="card-response-b",
                    session_id=None,
                    is_initiator=False,
                )
            )
            session.add(
                CardResponse(
                    user_id=outsider.id,
                    card_id=uuid.uuid4(),
                    content="card-response-outsider",
                    session_id=None,
                    is_initiator=True,
                )
            )
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.outsider_id = outsider.id

        self.current_user_id = self.user_a_id
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"growth_reengagement_hooks_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_reengagement_hooks": false}'

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.client.close()
        self.engine.dispose()

    def test_reengagement_hooks_returns_two_eligible_hooks_for_mature_pair(self) -> None:
        response = self.client.get("/api/users/reengagement-hooks")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["has_partner_context"])
        self.assertFalse(payload["kill_switch_active"])
        self.assertEqual(len(payload["hooks"]), 2)

        hooks = {item["hook_type"]: item for item in payload["hooks"]}
        social_hook = hooks["SOCIAL_SHARE_CARD"]
        self.assertTrue(social_hook["eligible"])
        self.assertEqual(social_hook["reason"], "eligible")
        self.assertEqual(len(social_hook["dedupe_key"]), 64)
        self.assertEqual(social_hook["metadata"]["pair_journal_count"], 6)
        self.assertEqual(social_hook["metadata"]["user_journal_count"], 3)
        self.assertEqual(social_hook["metadata"]["partner_journal_count"], 3)

        time_capsule_hook = hooks["TIME_CAPSULE"]
        self.assertTrue(time_capsule_hook["eligible"])
        self.assertEqual(time_capsule_hook["reason"], "eligible")
        self.assertEqual(len(time_capsule_hook["dedupe_key"]), 64)
        self.assertEqual(time_capsule_hook["metadata"]["pair_journal_count"], 6)
        self.assertEqual(time_capsule_hook["metadata"]["pair_card_response_count"], 2)

        serialized = str(payload).lower()
        self.assertNotIn("reengage-a@example.com", serialized)
        self.assertNotIn("reengage-b@example.com", serialized)
        self.assertNotIn("outsider", serialized)

    def test_kill_switch_disables_reengagement_hooks(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_reengagement_hooks": true}'
        response = self.client.get("/api/users/reengagement-hooks")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["enabled"])
        self.assertTrue(payload["kill_switch_active"])
        self.assertEqual(payload["hooks"], [])

    def test_missing_partner_context_disables_hooks_without_error(self) -> None:
        self.current_user_id = self.outsider_id
        response = self.client.get("/api/users/reengagement-hooks")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["enabled"])
        self.assertFalse(payload["has_partner_context"])
        self.assertEqual(payload["hooks"], [])

    def test_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            response = client.get("/api/users/reengagement-hooks")
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
