# READ_AUTHZ_MATRIX: GET /api/love-map/system

import sys
import unittest
import uuid
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
from app.api.routers import love_language, love_map  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.love_language import LoveLanguagePreference  # noqa: E402
from app.models.relationship_care_profile import RelationshipCareProfile  # noqa: E402
from app.models.user import User  # noqa: E402


class LoveMapSystemApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(love_map.router, prefix="/api/love-map")
        app.include_router(love_language.router, prefix="/api/love-languages")

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
            alice = User(email="alice-system@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-system@example.com", full_name="Bob", hashed_password="hashed")
            carol = User(email="carol-system@example.com", full_name="Carol", hashed_password="hashed")
            dave = User(email="dave-system@example.com", full_name="Dave", hashed_password="hashed")
            solo = User(email="solo-system@example.com", full_name="Solo", hashed_password="hashed")
            session.add(alice)
            session.add(bob)
            session.add(carol)
            session.add(dave)
            session.add(solo)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(carol)
            session.refresh(dave)
            session.refresh(solo)

            alice.partner_id = bob.id
            bob.partner_id = alice.id
            carol.partner_id = dave.id
            dave.partner_id = carol.id
            session.add(alice)
            session.add(bob)
            session.add(carol)
            session.add(dave)

            session.add(
                LoveLanguagePreference(
                    user_id=alice.id,
                    preference={"primary": "words", "secondary": "time"},
                )
            )
            session.add(
                LoveLanguagePreference(
                    user_id=bob.id,
                    preference={"primary": "acts", "secondary": "touch"},
                )
            )
            session.add(
                LoveLanguagePreference(
                    user_id=carol.id,
                    preference={"primary": "gifts", "secondary": "time"},
                )
            )
            session.add(
                LoveLanguagePreference(
                    user_id=solo.id,
                    preference={"primary": "time", "secondary": "words"},
                )
            )
            session.add(
                RelationshipCareProfile(
                    user_id=alice.id,
                    partner_id=bob.id,
                    support_me="先抱我一下，再慢慢問我怎麼了。",
                    avoid_when_stressed="不要急著幫我下結論。",
                    small_delights="下班時帶熱拿鐵會讓我瞬間放鬆。",
                )
            )
            session.add(
                RelationshipCareProfile(
                    user_id=bob.id,
                    partner_id=alice.id,
                    support_me="先給我十分鐘安靜，再來陪我說。",
                    avoid_when_stressed="不要一直追問我為什麼還沒整理好。",
                    small_delights="如果你先把餐桌整理好，我會覺得被照顧。",
                )
            )
            session.add(
                RelationshipCareProfile(
                    user_id=carol.id,
                    partner_id=dave.id,
                    support_me="幫我把燈關暗一點。",
                    avoid_when_stressed="不要一直講大道理。",
                    small_delights="提醒我去陽台透氣。",
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

    def test_paired_user_sees_pair_visible_care_preferences_and_profiles(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.get("/api/love-map/system")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        essentials = payload["essentials"]
        self.assertEqual(essentials["my_care_preferences"]["primary"], "words")
        self.assertEqual(essentials["my_care_preferences"]["secondary"], "time")
        self.assertEqual(essentials["partner_care_preferences"]["primary"], "acts")
        self.assertEqual(essentials["partner_care_preferences"]["secondary"], "touch")
        self.assertEqual(
            essentials["my_care_profile"]["support_me"],
            "先抱我一下，再慢慢問我怎麼了。",
        )
        self.assertEqual(
            essentials["partner_care_profile"]["small_delights"],
            "如果你先把餐桌整理好，我會覺得被照顧。",
        )

    def test_unpaired_user_gets_no_partner_essentials_or_weekly_task(self) -> None:
        self.current_user_id = self.solo_id

        response = self.client.get("/api/love-map/system")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        essentials = payload["essentials"]
        self.assertFalse(payload["has_partner"])
        self.assertEqual(essentials["my_care_preferences"]["primary"], "time")
        self.assertEqual(essentials["my_care_preferences"]["secondary"], "words")
        self.assertIsNone(essentials["partner_care_preferences"])
        self.assertIsNone(essentials["my_care_profile"])
        self.assertIsNone(essentials["partner_care_profile"])
        self.assertIsNone(essentials["weekly_task"])

    def test_weekly_task_completion_is_reflected_in_love_map_system(self) -> None:
        self.current_user_id = self.alice_id

        complete_response = self.client.post("/api/love-languages/weekly-task/complete")
        self.assertEqual(complete_response.status_code, 200)

        response = self.client.get("/api/love-map/system")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        weekly_task = payload["essentials"]["weekly_task"]
        self.assertIsNotNone(weekly_task)
        self.assertTrue(weekly_task["completed"])
        self.assertIsNotNone(weekly_task["completed_at"])

    def test_relationship_essentials_do_not_leak_other_pairs(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.get("/api/love-map/system")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        essentials = payload["essentials"]
        self.assertEqual(essentials["partner_care_preferences"]["primary"], "acts")
        self.assertNotEqual(essentials["partner_care_preferences"]["primary"], "gifts")
        self.assertEqual(
            essentials["partner_care_profile"]["support_me"],
            "先給我十分鐘安靜，再來陪我說。",
        )
        self.assertNotEqual(
            essentials["partner_care_profile"]["support_me"],
            "幫我把燈關暗一點。",
        )


if __name__ == "__main__":
    unittest.main()
