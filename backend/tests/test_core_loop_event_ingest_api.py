# AUTHZ_MATRIX: POST /api/users/events/core-loop

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
from app.models.events_log import EventsLog  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.events_log import reset_core_loop_ingest_guard_for_tests  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class CoreLoopEventIngestApiTests(unittest.TestCase):
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
            user_a = User(email="core-loop-a@example.com", full_name="Core Loop A", hashed_password="hashed")
            user_b = User(email="core-loop-b@example.com", full_name="Core Loop B", hashed_password="hashed")
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
        reset_core_loop_ingest_guard_for_tests()

    def tearDown(self) -> None:
        reset_core_loop_ingest_guard_for_tests()
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        users.pairing_abuse_guard = self.original_pairing_guard
        users.pairing_ip_abuse_guard = self.original_pairing_ip_guard
        self.client.close()
        self.engine.dispose()

    def test_tracks_and_dedupes_core_loop_event(self) -> None:
        payload = {
            "event_name": "daily_sync_submitted",
            "event_id": "evt-core-loop-001",
            "source": "web",
            "session_id": "sync-session-001",
            "props": {"loop_version": "v1"},
        }
        first = self.client.post("/api/users/events/core-loop", json=payload)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(
            first.json(),
            {
                "accepted": True,
                "deduped": False,
                "event_name": "daily_sync_submitted",
                "loop_completed_today": False,
            },
        )

        duplicate = self.client.post("/api/users/events/core-loop", json=payload)
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(
            duplicate.json(),
            {
                "accepted": True,
                "deduped": True,
                "event_name": "daily_sync_submitted",
                "loop_completed_today": False,
            },
        )

        with Session(self.engine) as session:
            rows = session.exec(select(EventsLog)).all()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(str(row.user_id), str(self.user_a_id))
            self.assertEqual(str(row.partner_user_id), str(self.user_b_id))
            self.assertEqual(row.event_name, "daily_sync_submitted")
            self.assertEqual(row.source, "web")
            self.assertEqual(row.session_id, "sync-session-001")

    def test_rejects_overposted_actor_identity(self) -> None:
        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "daily_card_revealed",
                "event_id": "evt-core-loop-002",
                "source": "web",
                "user_id": str(self.user_b_id),
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_redacts_sensitive_props(self) -> None:
        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "card_answer_submitted",
                "event_id": "evt-core-loop-003",
                "props": {
                    "email": "private@example.com",
                    "answer_content": "sensitive",
                    "time_spent_sec": 120,
                },
            },
        )
        self.assertEqual(response.status_code, 202)

        with Session(self.engine) as session:
            row = session.exec(
                select(EventsLog).where(EventsLog.event_id == "evt-core-loop-003")
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            payload = json.loads(row.props_json or "{}")
            self.assertEqual(payload, {"time_spent_sec": 120})

    def test_redacts_sensitive_context_and_privacy_payload_fields(self) -> None:
        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "daily_sync_submitted",
                "event_id": "evt-core-loop-context-redact-001",
                "context": {
                    "route": "/daily/private@example.com",
                    "app_version": "1.0.0",
                    "auth_token": "should_drop",
                },
                "privacy": {
                    "consent_scope": "analysis",
                    "device_token": "should_drop",
                },
            },
        )
        self.assertEqual(response.status_code, 202)
        with Session(self.engine) as session:
            row = session.exec(
                select(EventsLog).where(EventsLog.event_id == "evt-core-loop-context-redact-001")
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            context_payload = json.loads(row.context_json or "{}")
            privacy_payload = json.loads(row.privacy_json or "{}")
            self.assertIn("route", context_payload)
            self.assertNotIn("private@example.com", context_payload.get("route", ""))
            self.assertNotIn("auth_token", context_payload)
            self.assertEqual(privacy_payload, {"consent_scope": "analysis"})

    def test_drops_unknown_props_and_enriches_context_schema_version(self) -> None:
        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "daily_card_revealed",
                "event_id": "evt-core-loop-unknown-001",
                "props": {
                    "time_spent_sec": 45,
                    "not_allowed_key": "ignored",
                },
                "context": {
                    "route": "/decks",
                    "unknown_context_key": "ignored",
                },
            },
        )
        self.assertEqual(response.status_code, 202)

        with Session(self.engine) as session:
            row = session.exec(
                select(EventsLog).where(EventsLog.event_id == "evt-core-loop-unknown-001")
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            props_payload = json.loads(row.props_json or "{}")
            context_payload = json.loads(row.context_json or "{}")
            self.assertEqual(props_payload, {"time_spent_sec": 45})
            self.assertEqual(context_payload.get("route"), "/decks")
            self.assertEqual(context_payload.get("event_schema_version"), "v1")

    def test_oversized_json_payload_is_dropped_instead_of_failing_ingest(self) -> None:
        original_max_bytes = settings.EVENTS_LOG_JSON_MAX_BYTES
        settings.EVENTS_LOG_JSON_MAX_BYTES = 64
        self.addCleanup(setattr, settings, "EVENTS_LOG_JSON_MAX_BYTES", original_max_bytes)
        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "card_answer_submitted",
                "event_id": "evt-core-loop-oversized-001",
                "props": {
                    "reaction": "x" * 5000,
                    "mood_label": "y" * 5000,
                    "relationship_stage": "z" * 5000,
                },
            },
        )
        self.assertEqual(response.status_code, 202)
        with Session(self.engine) as session:
            row = session.exec(
                select(EventsLog).where(EventsLog.event_id == "evt-core-loop-oversized-001")
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertIsNone(row.props_json)

    def test_kill_switch_disables_core_loop_ingest(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_referral_funnel": false, "disable_growth_events_ingest": true}'
        )
        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "appreciation_sent",
                "event_id": "evt-core-loop-004",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {
                "accepted": False,
                "deduped": False,
                "event_name": "appreciation_sent",
                "loop_completed_today": False,
            },
        )
        with Session(self.engine) as session:
            rows = session.exec(select(EventsLog)).all()
            self.assertEqual(rows, [])

    def test_rate_limit_budget_guard_skips_excess_core_loop_ingest(self) -> None:
        original_count = settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT
        original_window = settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT = 1
        settings.EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS = 60
        self.addCleanup(setattr, settings, "EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT", original_count)
        self.addCleanup(setattr, settings, "EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS", original_window)
        reset_core_loop_ingest_guard_for_tests()

        first = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "daily_sync_submitted",
                "event_id": "evt-core-loop-rate-limit-001",
            },
        )
        second = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "daily_card_revealed",
                "event_id": "evt-core-loop-rate-limit-002",
            },
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()["accepted"], True)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.json()["accepted"], False)
        with Session(self.engine) as session:
            rows = session.exec(select(EventsLog)).all()
            self.assertEqual(len(rows), 1)

    def test_total_json_budget_guard_drops_payload_blobs(self) -> None:
        original_json_max = settings.EVENTS_LOG_JSON_MAX_BYTES
        original_total_max = settings.EVENTS_LOG_TOTAL_JSON_MAX_BYTES
        settings.EVENTS_LOG_JSON_MAX_BYTES = 1024
        settings.EVENTS_LOG_TOTAL_JSON_MAX_BYTES = 520
        self.addCleanup(setattr, settings, "EVENTS_LOG_JSON_MAX_BYTES", original_json_max)
        self.addCleanup(setattr, settings, "EVENTS_LOG_TOTAL_JSON_MAX_BYTES", original_total_max)

        response = self.client.post(
            "/api/users/events/core-loop",
            json={
                "event_name": "daily_sync_submitted",
                "event_id": "evt-core-loop-total-budget-001",
                "props": {
                    "mood_label": "a" * 240,
                    "relationship_stage": "steady",
                },
                "context": {
                    "route": "/daily-" + ("b" * 220),
                    "app_version": "1.2.3-build-abc",
                },
                "privacy": {
                    "consent_scope": "analysis-" + ("c" * 220),
                },
            },
        )
        self.assertEqual(response.status_code, 202)
        with Session(self.engine) as session:
            row = session.exec(
                select(EventsLog).where(EventsLog.event_id == "evt-core-loop-total-budget-001")
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertIsNone(row.props_json)
            self.assertIsNone(row.context_json)
            self.assertIsNone(row.privacy_json)

    def test_auto_records_daily_loop_completed_when_four_steps_present(self) -> None:
        steps = (
            ("daily_sync_submitted", "evt-core-loop-auto-001"),
            ("daily_card_revealed", "evt-core-loop-auto-002"),
            ("card_answer_submitted", "evt-core-loop-auto-003"),
            ("appreciation_sent", "evt-core-loop-auto-004"),
        )
        final_response = None
        for event_name, event_id in steps:
            response = self.client.post(
                "/api/users/events/core-loop",
                json={
                    "event_name": event_name,
                    "event_id": event_id,
                    "source": "web",
                },
            )
            self.assertEqual(response.status_code, 202)
            final_response = response

        assert final_response is not None
        payload = final_response.json()
        self.assertTrue(payload["accepted"])
        self.assertFalse(payload["deduped"])
        self.assertEqual(payload["event_name"], "appreciation_sent")
        self.assertTrue(payload["loop_completed_today"])

        with Session(self.engine) as session:
            rows = session.exec(
                select(EventsLog).where(EventsLog.event_name == "daily_loop_completed")
            ).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].source, "server")

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
                "/api/users/events/core-loop",
                json={
                    "event_name": "daily_loop_completed",
                    "event_id": "evt-core-loop-005",
                },
            )
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
