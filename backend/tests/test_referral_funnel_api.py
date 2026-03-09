# AUTHZ_MATRIX: POST /api/users/referrals/landing-view
# AUTHZ_MATRIX: POST /api/users/referrals/signup
# AUTHZ_MATRIX: POST /api/users/referrals/couple-invite

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
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.growth_referral_event import GrowthReferralEvent, GrowthReferralEventType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class ReferralFunnelApiTests(unittest.TestCase):
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
            inviter = User(
                email="referrer@example.com",
                full_name="Referrer",
                hashed_password="hashed",
                invite_code="PAIRB1",
                invite_code_created_at=utcnow(),
            )
            invitee = User(
                email="invitee@example.com",
                full_name="Invitee",
                hashed_password="hashed",
            )
            session.add(inviter)
            session.add(invitee)
            session.commit()
            session.refresh(inviter)
            session.refresh(invitee)
            self.inviter_id = inviter.id
            self.invitee_id = invitee.id

        self.current_user_id = self.invitee_id
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        settings.FEATURE_FLAGS_JSON = '{"growth_referral_enabled": true}'
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

    def test_landing_view_tracks_and_dedupes_without_exposing_inviter_identity(self) -> None:
        payload = {
            "invite_code": " pairb1 ",
            "event_id": "landing-evt-1",
            "source": "landing_page",
            "landing_path": "/invite/pairb1",
        }
        first = self.client.post("/api/users/referrals/landing-view", json=payload)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(
            first.json(),
            {"accepted": True, "deduped": False, "event_type": "LANDING_VIEW"},
        )

        duplicate = self.client.post("/api/users/referrals/landing-view", json=payload)
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(
            duplicate.json(),
            {"accepted": True, "deduped": True, "event_type": "LANDING_VIEW"},
        )

        with Session(self.engine) as session:
            events = session.exec(select(GrowthReferralEvent)).all()
            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event.event_type, GrowthReferralEventType.LANDING_VIEW)
            self.assertEqual(event.inviter_user_id, self.inviter_id)
            self.assertIsNone(event.actor_user_id)
            self.assertEqual(len(event.invite_code_hash), 64)

    def test_signup_event_uses_current_user_identity(self) -> None:
        response = self.client.post(
            "/api/users/referrals/signup",
            json={
                "invite_code": "PAIRB1",
                "event_id": "signup-evt-1",
                "source": "register_page",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"accepted": True, "deduped": False, "event_type": "SIGNUP"},
        )

        with Session(self.engine) as session:
            row = session.exec(
                select(GrowthReferralEvent).where(
                    GrowthReferralEvent.event_type == GrowthReferralEventType.SIGNUP
                )
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.actor_user_id, self.invitee_id)
            self.assertEqual(row.inviter_user_id, self.inviter_id)

    def test_signup_rejects_overposted_actor_identity(self) -> None:
        response = self.client.post(
            "/api/users/referrals/signup",
            json={
                "invite_code": "PAIRB1",
                "event_id": "signup-evt-2",
                "source": "register_page",
                "actor_user_id": str(self.inviter_id),
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_signup_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            response = client.post(
                "/api/users/referrals/signup",
                json={
                    "invite_code": "PAIRB1",
                    "event_id": "signup-evt-unauth",
                    "source": "register_page",
                },
            )
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()

    def test_couple_invite_tracks_current_user_invite_link_share(self) -> None:
        self.current_user_id = self.inviter_id
        response = self.client.post(
            "/api/users/referrals/couple-invite",
            json={
                "invite_code": "pairb1",
                "event_id": "couple-invite-evt-1",
                "source": "partner_settings",
                "share_channel": "link_copy",
                "landing_path": "/register",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"accepted": True, "deduped": False, "event_type": "COUPLE_INVITE"},
        )

        duplicate = self.client.post(
            "/api/users/referrals/couple-invite",
            json={
                "invite_code": "PAIRB1",
                "event_id": "couple-invite-evt-1",
                "source": "partner_settings",
                "share_channel": "link_copy",
            },
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(
            duplicate.json(),
            {"accepted": True, "deduped": True, "event_type": "COUPLE_INVITE"},
        )

        with Session(self.engine) as session:
            row = session.exec(
                select(GrowthReferralEvent).where(
                    GrowthReferralEvent.event_type == GrowthReferralEventType.COUPLE_INVITE
                )
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.actor_user_id, self.inviter_id)
            self.assertEqual(row.inviter_user_id, self.inviter_id)

    def test_couple_invite_rejects_invite_code_not_owned_by_current_user(self) -> None:
        response = self.client.post(
            "/api/users/referrals/couple-invite",
            json={
                "invite_code": "PAIRB1",
                "event_id": "couple-invite-evt-foreign",
                "source": "partner_settings",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_couple_invite_rejects_overposted_actor_identity(self) -> None:
        self.current_user_id = self.inviter_id
        response = self.client.post(
            "/api/users/referrals/couple-invite",
            json={
                "invite_code": "PAIRB1",
                "event_id": "couple-invite-evt-overpost",
                "source": "partner_settings",
                "actor_user_id": str(self.invitee_id),
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_couple_invite_requires_authentication_when_dependency_override_absent(self) -> None:
        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)
        try:
            response = client.post(
                "/api/users/referrals/couple-invite",
                json={
                    "invite_code": "PAIRB1",
                    "event_id": "couple-invite-evt-unauth",
                    "source": "partner_settings",
                },
            )
            self.assertEqual(response.status_code, 401)
        finally:
            client.close()

    def test_pair_success_records_referral_bind_event(self) -> None:
        response = self.client.post("/api/users/pair", json={"invite_code": "pairb1"})
        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            row = session.exec(
                select(GrowthReferralEvent).where(
                    GrowthReferralEvent.event_type == GrowthReferralEventType.BIND
                )
            ).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.actor_user_id, self.invitee_id)
            self.assertEqual(row.inviter_user_id, self.inviter_id)

    def test_kill_switch_disables_referral_tracking_without_failing_request(self) -> None:
        settings.FEATURE_KILL_SWITCHES_JSON = (
            '{"disable_referral_funnel": true, "disable_growth_events_ingest": false}'
        )
        response = self.client.post(
            "/api/users/referrals/landing-view",
            json={
                "invite_code": "pairb1",
                "event_id": "landing-evt-kill-switch",
                "source": "landing_page",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {"accepted": False, "deduped": False, "event_type": "LANDING_VIEW"},
        )

        with Session(self.engine) as session:
            count = len(session.exec(select(GrowthReferralEvent)).all())
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
