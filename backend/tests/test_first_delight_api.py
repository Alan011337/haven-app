# READ_AUTHZ_MATRIX: GET /api/users/first-delight
# AUTHZ_MATRIX: POST /api/users/first-delight/ack

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


class FirstDelightApiTests(unittest.TestCase):
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
        with Session(self.engine) as session:
            user_a = User(
                email="first-delight-a@example.com",
                full_name="First Delight A",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
            )
            user_b = User(
                email="first-delight-b@example.com",
                full_name="First Delight B",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
            )
            outsider = User(
                email="first-delight-outsider@example.com",
                full_name="First Delight Outsider",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
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
                    content="first-delight-user-a-journal",
                    created_at=now - timedelta(hours=4),
                )
            )
            session.add(
                Journal(
                    user_id=user_b.id,
                    content="first-delight-user-b-journal",
                    created_at=now - timedelta(hours=2),
                )
            )
            session.add(
                CardResponse(
                    user_id=user_a.id,
                    card_id=uuid.uuid4(),
                    content="first-delight-user-a-response",
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    user_id=user_b.id,
                    card_id=uuid.uuid4(),
                    content="first-delight-user-b-response",
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
        settings.FEATURE_FLAGS_JSON = '{"growth_first_delight_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_first_delight": false}'

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.client.close()
        self.engine.dispose()

    def _fetch_first_delight(self) -> dict:
        response = self.client.get("/api/users/first-delight")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_delight_returns_eligible_milestone_for_pair(self) -> None:
        payload = self._fetch_first_delight()
        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["has_partner_context"])
        self.assertFalse(payload["kill_switch_active"])
        self.assertFalse(payload["delivered"])
        self.assertTrue(payload["eligible"])
        self.assertEqual(payload["reason"], "eligible")
        self.assertEqual(len(payload["dedupe_key"]), 64)
        self.assertEqual(payload["metadata"]["target_pair_journal_count"], 2)
        self.assertEqual(payload["metadata"]["target_pair_card_response_count"], 2)
        serialized = str(payload).lower()
        self.assertNotIn("first-delight-a@example.com", serialized)
        self.assertNotIn("first-delight-b@example.com", serialized)

    def test_first_delight_ack_is_idempotent(self) -> None:
        payload = self._fetch_first_delight()
        dedupe_key = payload["dedupe_key"]

        first = self.client.post(
            "/api/users/first-delight/ack",
            json={"dedupe_key": dedupe_key, "source": "home_header"},
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["accepted"])
        self.assertFalse(first.json()["deduped"])
        self.assertEqual(first.json()["reason"], "accepted")

        second = self.client.post(
            "/api/users/first-delight/ack",
            json={"dedupe_key": dedupe_key, "source": "home_header"},
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["accepted"])
        self.assertTrue(second.json()["deduped"])
        self.assertEqual(second.json()["reason"], "deduped")

        refreshed = self._fetch_first_delight()
        self.assertTrue(refreshed["delivered"])
        self.assertFalse(refreshed["eligible"])
        self.assertEqual(refreshed["reason"], "delivered_already")

    def test_first_delight_ack_rejects_mismatched_dedupe_key(self) -> None:
        response = self.client.post(
            "/api/users/first-delight/ack",
            json={"dedupe_key": "x" * 64, "source": "home_header"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["accepted"])
        self.assertFalse(payload["deduped"])
        self.assertEqual(payload["reason"], "dedupe_key_mismatch")

    def test_first_delight_disable_with_kill_switch_and_missing_partner(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_first_delight": true}'
        payload = self._fetch_first_delight()
        self.assertFalse(payload["enabled"])
        self.assertTrue(payload["kill_switch_active"])
        self.assertFalse(payload["eligible"])
        self.assertIsNone(payload["dedupe_key"])

        self.current_user_id = self.outsider_id
        payload_no_partner = self._fetch_first_delight()
        self.assertFalse(payload_no_partner["enabled"])
        self.assertFalse(payload_no_partner["has_partner_context"])
        self.assertEqual(payload_no_partner["reason"], "disabled")

        ack_without_partner = self.client.post(
            "/api/users/first-delight/ack",
            json={"dedupe_key": "a" * 64, "source": "home_header"},
        )
        self.assertEqual(ack_without_partner.status_code, 200)
        self.assertEqual(ack_without_partner.json()["reason"], "partner_required")

    def test_first_delight_ignores_overposted_user_id_query(self) -> None:
        baseline = self.client.get("/api/users/first-delight")
        self.assertEqual(baseline.status_code, 200)
        overposted = self.client.get(
            "/api/users/first-delight",
            params={"user_id": str(self.user_b_id)},
        )
        self.assertEqual(overposted.status_code, 200)
        self.assertEqual(overposted.json(), baseline.json())

    def test_first_delight_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            get_response = client.get("/api/users/first-delight")
            self.assertEqual(get_response.status_code, 401)
            post_response = client.post(
                "/api/users/first-delight/ack",
                json={"dedupe_key": "a" * 64},
            )
            self.assertEqual(post_response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
