# AUTHZ_MATRIX: POST /api/cards/respond

import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import cards  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.user import User  # noqa: E402


class CardAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        self.queue_patch = patch("app.api.routers.cards.queue_partner_notification")
        self.queue_patch.start()
        self.socket_patch = patch(
            "app.api.routers.cards.manager.send_personal_message",
            new=AsyncMock(),
        )
        self.socket_patch.start()

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
            user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            user_b = User(email="b@example.com", full_name="B", hashed_password="hashed")
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Card",
                description="desc",
                question="How are you feeling?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(card)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(card)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.card_id = card.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.socket_patch.stop()
        self.queue_patch.stop()
        self.engine.dispose()

    def test_respond_allows_owner_to_update_own_response(self) -> None:
        first = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card_id), "content": "first answer"},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card_id), "content": "updated answer"},
        )
        self.assertEqual(second.status_code, 200)

        with Session(self.engine) as session:
            rows = session.exec(
                select(CardResponse).where(
                    CardResponse.user_id == self.user_a_id,
                    CardResponse.card_id == self.card_id,
                    CardResponse.session_id.is_(None),
                )
            ).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].content, "updated answer")

    def test_respond_does_not_allow_other_user_to_overwrite_existing_response(self) -> None:
        first = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card_id), "content": "owner original"},
        )
        self.assertEqual(first.status_code, 200)

        self.current_user_id = self.user_b_id
        second = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card_id), "content": "other user answer"},
        )
        self.assertEqual(second.status_code, 200)

        with Session(self.engine) as session:
            owner_row = session.exec(
                select(CardResponse).where(
                    CardResponse.user_id == self.user_a_id,
                    CardResponse.card_id == self.card_id,
                    CardResponse.session_id.is_(None),
                )
            ).first()
            other_row = session.exec(
                select(CardResponse).where(
                    CardResponse.user_id == self.user_b_id,
                    CardResponse.card_id == self.card_id,
                    CardResponse.session_id.is_(None),
                )
            ).first()

            self.assertIsNotNone(owner_row)
            self.assertIsNotNone(other_row)
            self.assertNotEqual(owner_row.id, other_row.id)
            self.assertEqual(owner_row.content, "owner original")
            self.assertEqual(other_row.content, "other user answer")


if __name__ == "__main__":
    unittest.main()
