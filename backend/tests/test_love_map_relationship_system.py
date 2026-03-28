# READ_AUTHZ_MATRIX: GET /api/love-map/system

import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import love_map  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.appreciation import Appreciation  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.couple_goal import CoupleGoal  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.love_map_note import LoveMapNote  # noqa: E402
from app.models.relationship_baseline import RelationshipBaseline  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.wishlist_item import WishlistItem  # noqa: E402


class LoveMapRelationshipSystemTests(unittest.TestCase):
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
            alice = User(email="alice-love-map@example.com", full_name="Alice", hashed_password="hashed")
            bob = User(email="bob-love-map@example.com", full_name="Bob", hashed_password="hashed")
            solo = User(email="solo-love-map@example.com", full_name="Solo", hashed_password="hashed")
            session.add(alice)
            session.add(bob)
            session.add(solo)
            session.commit()
            session.refresh(alice)
            session.refresh(bob)
            session.refresh(solo)

            alice.partner_id = bob.id
            bob.partner_id = alice.id
            session.add(alice)
            session.add(bob)

            session.add(
                RelationshipBaseline(
                    user_id=alice.id,
                    partner_id=bob.id,
                    scores={
                        "intimacy": 4,
                        "conflict": 3,
                        "trust": 5,
                        "communication": 4,
                        "commitment": 5,
                    },
                )
            )
            session.add(
                RelationshipBaseline(
                    user_id=bob.id,
                    partner_id=alice.id,
                    scores={
                        "intimacy": 5,
                        "conflict": 3,
                        "trust": 4,
                        "communication": 4,
                        "commitment": 5,
                    },
                )
            )
            session.add(CoupleGoal(user_id=min(alice.id, bob.id), partner_id=max(alice.id, bob.id), goal_slug="more_trust"))
            session.add(LoveMapNote(user_id=alice.id, partner_id=bob.id, layer="safe", content="Alice safe note"))
            session.add(LoveMapNote(user_id=alice.id, partner_id=bob.id, layer="deep", content="Alice deep note"))
            session.add(LoveMapNote(user_id=bob.id, partner_id=alice.id, layer="safe", content="Bob private note"))
            session.add(WishlistItem(user_id=alice.id, partner_id=bob.id, title="Kyoto in spring", notes="Sakura trip"))
            session.add(WishlistItem(user_id=bob.id, partner_id=alice.id, title="Monthly tea ritual", notes="No phones"))

            story_card = Card(
                category=CardCategory.MEMORY_LANE,
                title="Shared weather",
                description="A remembered conversation prompt.",
                question="What has felt different between us lately?",
                difficulty_level=1,
                depth_level=1,
            )
            session.add(story_card)
            session.commit()
            session.refresh(story_card)

            now = utcnow()
            recent_story_time = now - timedelta(days=2)
            one_year_story_time = now - timedelta(days=365)

            session.add(
                Journal(
                    user_id=alice.id,
                    content="We found a quiet coffee shop and stayed there all afternoon.",
                    mood_label="Warm",
                    created_at=recent_story_time,
                )
            )
            session.add(
                Appreciation(
                    user_id=alice.id,
                    partner_id=bob.id,
                    body_text="謝謝你每天早上幫我準備咖啡。",
                    created_at=recent_story_time + timedelta(hours=1),
                )
            )

            story_session = CardSession(
                creator_id=alice.id,
                partner_id=bob.id,
                card_id=story_card.id,
                category=story_card.category.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.COMPLETED,
                created_at=recent_story_time + timedelta(hours=2),
            )
            session.add(story_session)
            session.commit()
            session.refresh(story_session)

            session.add(
                CardResponse(
                    card_id=story_card.id,
                    user_id=alice.id,
                    session_id=story_session.id,
                    content="I want us to protect our slower moments.",
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                    created_at=recent_story_time + timedelta(hours=2),
                )
            )
            session.add(
                CardResponse(
                    card_id=story_card.id,
                    user_id=bob.id,
                    session_id=story_session.id,
                    content="I miss how easy it is when we stop rushing.",
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                    created_at=recent_story_time + timedelta(hours=2),
                )
            )

            session.add(
                Journal(
                    user_id=alice.id,
                    content="A year ago today we found a hidden cafe and stayed until sunset.",
                    mood_label="Memory",
                    created_at=one_year_story_time,
                )
            )
            capsule_session = CardSession(
                creator_id=alice.id,
                partner_id=bob.id,
                card_id=story_card.id,
                category=story_card.category.value,
                mode=CardSessionMode.DAILY_RITUAL,
                status=CardSessionStatus.COMPLETED,
                created_at=one_year_story_time,
            )
            session.add(capsule_session)
            session.commit()
            session.refresh(capsule_session)
            session.add(
                CardResponse(
                    card_id=story_card.id,
                    user_id=alice.id,
                    session_id=capsule_session.id,
                    content="Coming home to you still feels like the softest part of my day.",
                    status=ResponseStatus.REVEALED,
                    is_initiator=True,
                    created_at=one_year_story_time,
                )
            )
            session.add(
                CardResponse(
                    card_id=story_card.id,
                    user_id=bob.id,
                    session_id=capsule_session.id,
                    content="Even quiet days with you feel full.",
                    status=ResponseStatus.REVEALED,
                    is_initiator=False,
                    created_at=one_year_story_time,
                )
            )
            session.add(
                Appreciation(
                    user_id=alice.id,
                    partner_id=bob.id,
                    body_text="謝謝你那天下午陪我去咖啡廳。",
                    created_at=one_year_story_time,
                )
            )
            session.add(
                RelationshipBaseline(
                    user_id=solo.id,
                    partner_id=None,
                    scores={
                        "intimacy": 2,
                        "conflict": 2,
                        "trust": 2,
                        "communication": 2,
                        "commitment": 2,
                    },
                )
            )
            session.commit()

            self.alice_id = alice.id
            self.bob_id = bob.id
            self.solo_id = solo.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_system_snapshot_returns_structured_relationship_truth_without_partner_note_leak(self) -> None:
        self.current_user_id = self.alice_id

        response = self.client.get("/api/love-map/system")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["has_partner"])
        self.assertEqual(payload["partner"]["partner_name"], "Bob")
        self.assertIsNotNone(payload["baseline"]["mine"])
        self.assertIsNotNone(payload["baseline"]["partner"])
        self.assertEqual(payload["couple_goal"]["goal_slug"], "more_trust")
        self.assertTrue(payload["story"]["available"])
        self.assertEqual(len(payload["story"]["moments"]), 3)
        self.assertEqual({moment["kind"] for moment in payload["story"]["moments"]}, {"journal", "card", "appreciation"})
        self.assertIn("謝謝你每天早上幫我準備咖啡。", [moment["description"] for moment in payload["story"]["moments"]])
        self.assertIsNotNone(payload["story"]["time_capsule"])
        self.assertEqual(payload["story"]["time_capsule"]["journals_count"], 1)
        self.assertEqual(payload["story"]["time_capsule"]["cards_count"], 1)
        self.assertEqual(payload["story"]["time_capsule"]["appreciations_count"], 1)
        self.assertEqual(len(payload["notes"]), 2)
        self.assertEqual({note["layer"] for note in payload["notes"]}, {"safe", "deep"})
        self.assertEqual(payload["stats"]["filled_note_layers"], 2)
        self.assertEqual(payload["stats"]["wishlist_count"], 2)
        self.assertEqual(len(payload["wishlist_items"]), 2)
        self.assertNotIn("Bob private note", {note["content"] for note in payload["notes"]})

    def test_system_snapshot_stays_honest_for_solo_user(self) -> None:
        self.current_user_id = self.solo_id

        response = self.client.get("/api/love-map/system")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertFalse(payload["has_partner"])
        self.assertIsNone(payload["partner"])
        self.assertIsNone(payload["couple_goal"])
        self.assertFalse(payload["story"]["available"])
        self.assertEqual(payload["story"]["moments"], [])
        self.assertIsNone(payload["story"]["time_capsule"])
        self.assertEqual(payload["notes"], [])
        self.assertEqual(payload["wishlist_items"], [])
        self.assertTrue(payload["stats"]["baseline_ready_mine"])
        self.assertFalse(payload["stats"]["baseline_ready_partner"])


if __name__ == "__main__":
    unittest.main()
