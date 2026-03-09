import sys
import unittest
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
from app.api.routers import cards  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.user import User  # noqa: E402


class CardResourceConsumptionGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(cards.router, prefix="/api/cards")
        self.current_user_id = None

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
            user_a = User(email="resource-a@example.com", full_name="Resource A", hashed_password="hashed")
            user_b = User(email="resource-b@example.com", full_name="Resource B", hashed_password="hashed")
            user_c = User(email="resource-c@example.com", full_name="Resource C", hashed_password="hashed")
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)

            card_a = Card(
                category=CardCategory.DAILY_VIBE,
                title="Card A",
                description="desc",
                question="Q1?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            card_b = Card(
                category=CardCategory.DAILY_VIBE,
                title="Card B",
                description="desc",
                question="Q2?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            card_c = Card(
                category=CardCategory.DAILY_VIBE,
                title="Card C",
                description="desc",
                question="Q3?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(card_a)
            session.add(card_b)
            session.add(card_c)
            session.commit()
            session.refresh(card_a)
            session.refresh(card_b)
            session.refresh(card_c)

            session.add(
                CardResponse(
                    card_id=card_a.id,
                    user_id=user_a.id,
                    content="self conversation a",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=False,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_a.id,
                    user_id=user_b.id,
                    content="partner backlog a",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_b.id,
                    user_id=user_b.id,
                    content="partner backlog b",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.add(
                CardResponse(
                    card_id=card_c.id,
                    user_id=user_c.id,
                    content="foreign backlog",
                    session_id=None,
                    status=ResponseStatus.PENDING,
                    is_initiator=True,
                )
            )
            session.commit()

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.card_a_id = card_a.id
            self.card_b_id = card_b.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def test_read_cards_rejects_limit_above_cap(self) -> None:
        response = self.client.get("/api/cards/", params={"limit": 101})
        self.assertEqual(response.status_code, 422)
        self.assertIn("less than or equal to 100", str(response.json()))

    def test_read_cards_rejects_limit_below_minimum(self) -> None:
        response = self.client.get("/api/cards/", params={"limit": 0})
        self.assertEqual(response.status_code, 422)
        self.assertIn("greater than or equal to 1", str(response.json()))

    def test_read_cards_allows_valid_limit(self) -> None:
        response = self.client.get("/api/cards/", params={"limit": 2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertLessEqual(len(payload), 2)

    def test_backlog_rejects_limit_above_cap(self) -> None:
        response = self.client.get("/api/cards/backlog", params={"limit": 101})
        self.assertEqual(response.status_code, 422)
        self.assertIn("less than or equal to 100", str(response.json()))

    def test_backlog_rejects_limit_below_minimum(self) -> None:
        response = self.client.get("/api/cards/backlog", params={"limit": 0})
        self.assertEqual(response.status_code, 422)
        self.assertIn("greater than or equal to 1", str(response.json()))

    def test_backlog_allows_valid_limit(self) -> None:
        response = self.client.get("/api/cards/backlog", params={"limit": 1})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertLessEqual(len(payload), 1)
        expected_ids = {str(self.card_a_id), str(self.card_b_id)}
        self.assertTrue(all(item["id"] in expected_ids for item in payload))

    def test_conversation_rejects_limit_above_cap(self) -> None:
        response = self.client.get(
            f"/api/cards/{self.card_a_id}/conversation",
            params={"limit": 101},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("less than or equal to 100", str(response.json()))

    def test_conversation_rejects_limit_below_minimum(self) -> None:
        response = self.client.get(
            f"/api/cards/{self.card_a_id}/conversation",
            params={"limit": 0},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("greater than or equal to 1", str(response.json()))

    def test_conversation_allows_valid_limit(self) -> None:
        response = self.client.get(
            f"/api/cards/{self.card_a_id}/conversation",
            params={"limit": 1},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertLessEqual(len(payload), 1)
        allowed_users = {str(self.user_a_id), str(self.user_b_id)}
        self.assertTrue(all(item["user_id"] in allowed_users for item in payload))


if __name__ == "__main__":
    unittest.main()
