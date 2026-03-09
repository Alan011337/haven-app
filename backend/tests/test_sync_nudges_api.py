# READ_AUTHZ_MATRIX: GET /api/users/sync-nudges
# AUTHZ_MATRIX: POST /api/users/sync-nudges/{nudge_type}/deliver
# AUTHZ_DENY_MATRIX: POST /api/users/sync-nudges/{nudge_type}/deliver

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
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402


class SyncNudgesApiTests(unittest.TestCase):
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
                email="sync-nudge-a@example.com",
                full_name="Sync Nudge A",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
            )
            user_b = User(
                email="sync-nudge-b@example.com",
                full_name="Sync Nudge B",
                hashed_password="hashed",
                terms_accepted_at=now - timedelta(days=10),
            )
            outsider = User(
                email="sync-nudge-outsider@example.com",
                full_name="Sync Nudge Outsider",
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

            # user_a 有近期日記但不是今天；partner 在今天更新，觸發同步提醒。
            session.add(
                Journal(
                    user_id=user_a.id,
                    content="user-a-yesterday",
                    created_at=now - timedelta(days=1),
                )
            )
            session.add(
                Journal(
                    user_id=user_b.id,
                    content="user-b-today",
                    created_at=now,
                )
            )
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.outsider_id = outsider.id

        self.current_user_id = self.user_a_id
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"growth_sync_nudges_enabled": true}'
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_sync_nudges": false}'

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        self.client.close()
        self.engine.dispose()

    def _fetch_nudges(self) -> dict:
        response = self.client.get("/api/users/sync-nudges")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_sync_nudges_returns_eligible_items_for_partner_pair(self) -> None:
        payload = self._fetch_nudges()
        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["has_partner_context"])
        self.assertFalse(payload["kill_switch_active"])
        self.assertEqual(payload["nudge_cooldown_hours"], 18)
        self.assertEqual(len(payload["nudges"]), 3)

        nudges = {item["nudge_type"]: item for item in payload["nudges"]}
        self.assertTrue(nudges["PARTNER_JOURNAL_REPLY"]["eligible"])
        self.assertIn(nudges["PARTNER_JOURNAL_REPLY"]["reason"], ("eligible", "cooldown_active"))
        self.assertEqual(len(nudges["PARTNER_JOURNAL_REPLY"]["dedupe_key"]), 64)
        self.assertIn("metadata", nudges["PARTNER_JOURNAL_REPLY"])

        serialized = str(payload).lower()
        self.assertNotIn("sync-nudge-a@example.com", serialized)
        self.assertNotIn("sync-nudge-b@example.com", serialized)

    def test_deliver_sync_nudge_is_idempotent_and_enforces_cooldown(self) -> None:
        payload = self._fetch_nudges()
        partner_nudge = next(item for item in payload["nudges"] if item["nudge_type"] == "PARTNER_JOURNAL_REPLY")
        dedupe_key = partner_nudge["dedupe_key"]

        first = self.client.post(
            "/api/users/sync-nudges/PARTNER_JOURNAL_REPLY/deliver",
            json={"dedupe_key": dedupe_key, "source": "home_header"},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["accepted"], True)
        self.assertEqual(first.json()["deduped"], False)
        self.assertEqual(first.json()["reason"], "accepted")

        second = self.client.post(
            "/api/users/sync-nudges/PARTNER_JOURNAL_REPLY/deliver",
            json={"dedupe_key": dedupe_key, "source": "home_header"},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["accepted"], True)
        self.assertEqual(second.json()["deduped"], True)
        self.assertEqual(second.json()["reason"], "deduped")

        refreshed = self._fetch_nudges()
        refreshed_nudge = next(item for item in refreshed["nudges"] if item["nudge_type"] == "PARTNER_JOURNAL_REPLY")
        self.assertFalse(refreshed_nudge["eligible"])
        self.assertEqual(refreshed_nudge["reason"], "cooldown_active")

    def test_deliver_rejects_mismatched_dedupe_key(self) -> None:
        response = self.client.post(
            "/api/users/sync-nudges/PARTNER_JOURNAL_REPLY/deliver",
            json={"dedupe_key": "x" * 64, "source": "home_header"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["accepted"])
        self.assertFalse(payload["deduped"])
        self.assertEqual(payload["reason"], "dedupe_key_mismatch")

    def test_sync_nudges_disable_with_kill_switch_and_missing_partner(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_growth_sync_nudges": true}'
        payload = self._fetch_nudges()
        self.assertFalse(payload["enabled"])
        self.assertTrue(payload["kill_switch_active"])
        self.assertEqual(payload["nudges"], [])

        self.current_user_id = self.outsider_id
        payload_no_partner = self._fetch_nudges()
        self.assertFalse(payload_no_partner["enabled"])
        self.assertFalse(payload_no_partner["has_partner_context"])

        deliver_without_partner = self.client.post(
            "/api/users/sync-nudges/PARTNER_JOURNAL_REPLY/deliver",
            json={"dedupe_key": "a" * 64, "source": "home_header"},
        )
        self.assertEqual(deliver_without_partner.status_code, 200)
        self.assertEqual(deliver_without_partner.json()["reason"], "partner_required")

    def test_sync_nudges_ignores_overposted_user_id_query(self) -> None:
        baseline = self.client.get("/api/users/sync-nudges")
        self.assertEqual(baseline.status_code, 200)
        overposted = self.client.get(
            "/api/users/sync-nudges",
            params={"user_id": str(self.user_b_id)},
        )
        self.assertEqual(overposted.status_code, 200)
        self.assertEqual(overposted.json(), baseline.json())

    def test_sync_nudges_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            get_response = client.get("/api/users/sync-nudges")
            self.assertEqual(get_response.status_code, 401)
            post_response = client.post(
                "/api/users/sync-nudges/PARTNER_JOURNAL_REPLY/deliver",
                json={"dedupe_key": "a" * 64},
            )
            self.assertEqual(post_response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
