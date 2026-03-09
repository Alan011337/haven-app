# AUTHZ_MATRIX: POST /api/users/events/cuj

import json
import sys
import unittest
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.cuj_event import CujEvent  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class CujEventIngestApiTests(unittest.TestCase):
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
        self.original_pairing_guard = users.pairing_abuse_guard
        self.original_pairing_ip_guard = users.pairing_ip_abuse_guard
        users.pairing_abuse_guard = PairingAbuseGuard(
            limit_count=100,
            window_seconds=300,
            failure_threshold=100,
            cooldown_seconds=300,
        )
        users.pairing_ip_abuse_guard = PairingAbuseGuard(
            limit_count=1000,
            window_seconds=300,
            failure_threshold=1000,
            cooldown_seconds=300,
        )

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
            user_a = User(email="cuj-a@example.com", full_name="CUJ A", hashed_password="hashed")
            user_b = User(email="cuj-b@example.com", full_name="CUJ B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)
            session.commit()
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

        self.current_user_id = self.user_a_id
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = "{}"
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_referral_funnel": false, "disable_growth_events_ingest": false}'
        )

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        users.pairing_abuse_guard = self.original_pairing_guard
        users.pairing_ip_abuse_guard = self.original_pairing_ip_guard
        self.client.close()
        self.engine.dispose()

    def test_tracks_and_dedupes_cuj_event(self) -> None:
        payload = {
            "event_name": "RITUAL_DRAW",
            "event_id": "evt-cuj-draw-001",
            "source": "web",
            "mode": "DAILY_RITUAL",
            "metadata": {"step": 1, "ui": "daily_card"},
        }
        first = self.client.post("/api/users/events/cuj", json=payload)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(
            first.json(),
            {"accepted": True, "deduped": False, "event_name": "RITUAL_DRAW"},
        )

        duplicate = self.client.post("/api/users/events/cuj", json=payload)
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(
            duplicate.json(),
            {"accepted": True, "deduped": True, "event_name": "RITUAL_DRAW"},
        )

        with Session(self.engine) as session:
            rows = session.exec(select(CujEvent)).all()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(str(row.user_id), str(self.user_a_id))
            self.assertEqual(str(row.partner_user_id), str(self.user_b_id))
            self.assertEqual(row.mode, "DAILY_RITUAL")
            self.assertEqual(row.event_name, "RITUAL_DRAW")

    def test_rejects_overposted_actor_identity(self) -> None:
        response = self.client.post(
            "/api/users/events/cuj",
            json={
                "event_name": "RITUAL_LOAD",
                "event_id": "evt-cuj-load-001",
                "source": "web",
                "actor_user_id": str(self.user_b_id),
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_redacts_sensitive_metadata_keys(self) -> None:
        response = self.client.post(
            "/api/users/events/cuj",
            json={
                "event_name": "JOURNAL_SUBMIT",
                "event_id": "evt-cuj-journal-001",
                "source": "web",
                "metadata": {
                    "email": "private@example.com",
                    "journal_text": "sensitive",
                    "safe_key": "allowed",
                },
            },
        )
        self.assertEqual(response.status_code, 202)

        with Session(self.engine) as session:
            row = session.exec(select(CujEvent).where(CujEvent.event_id == "evt-cuj-journal-001")).first()
            self.assertIsNotNone(row)
            assert row is not None
            payload = json.loads(row.metadata_json or "{}")
            self.assertEqual(payload, {"safe_key": "allowed"})

    def test_kill_switch_disables_ingest_without_failing_request(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_referral_funnel": false, "disable_growth_events_ingest": true}'
        )
        response = self.client.post(
            "/api/users/events/cuj",
            json={
                "event_name": "RITUAL_UNLOCK",
                "event_id": "evt-cuj-unlock-001",
                "source": "web",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {"accepted": False, "deduped": False, "event_name": "RITUAL_UNLOCK"},
        )

        with Session(self.engine) as session:
            rows = session.exec(select(CujEvent)).all()
            self.assertEqual(rows, [])

    def test_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            response = client.post(
                "/api/users/events/cuj",
                json={
                    "event_name": "RITUAL_LOAD",
                    "event_id": "evt-cuj-auth-001",
                    "source": "web",
                },
            )
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
