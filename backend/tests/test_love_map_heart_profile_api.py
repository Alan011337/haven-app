# AUTHZ_MATRIX: PUT /api/love-map/essentials/heart-profile
# AUTHZ_DENY_MATRIX: PUT /api/love-map/essentials/heart-profile

import sys
import unittest
import uuid
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
from app.api.routers import love_map  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.love_language import LoveLanguagePreference  # noqa: E402
from app.models.relationship_care_profile import RelationshipCareProfile  # noqa: E402
from app.models.user import User  # noqa: E402


class LoveMapHeartProfileApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(love_map.router, prefix="/api/love-map")

        self.current_user_id: uuid.UUID | None = None

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        def override_get_current_user() -> User:
            if self.current_user_id is None:
                raise RuntimeError("current_user_id not set")
            with Session(self.engine) as session:
                user = session.get(User, self.current_user_id)
                if not user:
                    raise RuntimeError("user not found")
                return user

        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

        with Session(self.engine) as session:
            alice = User(email="alice-heart@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-heart@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-heart@example.com", full_name="Carol", hashed_password="hashed")
            solo = User(email="solo-heart@example.com", full_name="Solo", hashed_password="hashed")
            session.add(alice)
            session.add(bob)
            session.add(carol)
            session.add(solo)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(carol)
            session.refresh(solo)

            alice.partner_id = bob.id
            bob.partner_id = alice.id
            session.add(alice)
            session.add(bob)
            session.add(
                RelationshipCareProfile(
                    user_id=alice.id,
                    partner_id=carol.id,
                    support_me="stale other-pair note",
                    avoid_when_stressed="stale avoid",
                    small_delights="stale delight",
                )
            )
            session.commit()

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.carol_id = carol.id
            self.solo_id = solo.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_paired_user_can_upsert_own_heart_playbook(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/heart-profile",
            json={
                "primary": "acts",
                "secondary": "time",
                "support_me": "先幫我把手機放遠一點。",
                "avoid_when_stressed": "不要立刻逼我做決定。",
                "small_delights": "回家時先抱我一下。",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["care_preferences"]["primary"], "acts")
        self.assertEqual(payload["care_preferences"]["secondary"], "time")
        self.assertEqual(payload["care_profile"]["support_me"], "先幫我把手機放遠一點。")
        self.assertEqual(payload["care_profile"]["avoid_when_stressed"], "不要立刻逼我做決定。")
        self.assertEqual(payload["care_profile"]["small_delights"], "回家時先抱我一下。")

        with Session(self.engine) as session:
            preference = session.get(LoveLanguagePreference, self.alice_id)
            self.assertIsNotNone(preference)
            assert preference is not None
            self.assertEqual(preference.preference["primary"], "acts")
            self.assertEqual(preference.preference["secondary"], "time")

            row = session.exec(
                select(RelationshipCareProfile).where(
                    RelationshipCareProfile.user_id == self.alice_id,
                    RelationshipCareProfile.partner_id == self.bob_id,
                )
            ).first()
            self.assertIsNotNone(row)

    def test_unpaired_user_cannot_upsert_heart_playbook(self) -> None:
        self.current_user_id = self.solo_id

        response = self.client.put(
            "/api/love-map/essentials/heart-profile",
            json={
                "primary": "words",
                "secondary": "time",
                "support_me": "先陪我坐一下。",
                "avoid_when_stressed": "",
                "small_delights": "",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_heart_profile_write_does_not_touch_other_pair_scope(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.put(
            "/api/love-map/essentials/heart-profile",
            json={
                "primary": "words",
                "secondary": "touch",
                "support_me": "先提醒我喝口水。",
                "avoid_when_stressed": "不要用玩笑帶過。",
                "small_delights": "把客廳燈光調暗。",
            },
        )

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            pair_row = session.exec(
                select(RelationshipCareProfile).where(
                    RelationshipCareProfile.user_id == self.alice_id,
                    RelationshipCareProfile.partner_id == self.bob_id,
                )
            ).first()
            self.assertIsNotNone(pair_row)
            assert pair_row is not None
            self.assertEqual(pair_row.support_me, "先提醒我喝口水。")

            stale_row = session.exec(
                select(RelationshipCareProfile).where(
                    RelationshipCareProfile.user_id == self.alice_id,
                    RelationshipCareProfile.partner_id == self.carol_id,
                )
            ).first()
            self.assertIsNotNone(stale_row)
            assert stale_row is not None
            self.assertEqual(stale_row.support_me, "stale other-pair note")


if __name__ == "__main__":
    unittest.main()
