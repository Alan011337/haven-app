# AUTHZ_MATRIX: POST /api/card-decks/draw
# AUTHZ_MATRIX: POST /api/card-decks/respond/{session_id}
# AUTHZ_DENY_MATRIX: POST /api/card-decks/respond/{session_id}

import sys
import unittest
import uuid
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
from app.api.routers import card_decks  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.user import User  # noqa: E402


class CardDeckAuthorizationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        self.queue_patch = patch("app.api.routers.card_decks.queue_partner_notification")
        self.queue_patch.start()
        self.socket_patch = patch(
            "app.api.routers.card_decks.manager.send_personal_message",
            new=AsyncMock(),
        )
        self.socket_patch.start()

        app = FastAPI()
        app.include_router(card_decks.router, prefix="/api/card-decks")

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
            user_c = User(email="c@example.com", full_name="C", hashed_password="hashed")
            user_d = User(email="d@example.com", full_name="D", hashed_password="hashed")
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Deck Card",
                description="desc",
                question="How is today?",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.add(card)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)
            session.refresh(user_d)
            session.refresh(card)

            deck_session = CardSession(
                card_id=card.id,
                creator_id=user_a.id,
                partner_id=user_b.id,
                category=card.category.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.PENDING,
            )
            session.add(deck_session)
            session.commit()
            session.refresh(deck_session)

            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id
            self.user_d_id = user_d.id
            self.deck_session_id = deck_session.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        self.client.close()
        self.socket_patch.stop()
        self.queue_patch.stop()
        self.engine.dispose()

    def test_deck_respond_allows_creator(self) -> None:
        response = self.client.post(
            f"/api/card-decks/respond/{self.deck_session_id}",
            json={"content": "creator response"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_status"], CardSessionStatus.WAITING_PARTNER.value)

        with Session(self.engine) as session:
            row = session.exec(
                select(CardResponse).where(
                    CardResponse.session_id == self.deck_session_id,
                    CardResponse.user_id == self.user_a_id,
                )
            ).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.content, "creator response")

    def test_deck_respond_allows_partner(self) -> None:
        self.current_user_id = self.user_b_id
        response = self.client.post(
            f"/api/card-decks/respond/{self.deck_session_id}",
            json={"content": "partner response"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_status"], CardSessionStatus.WAITING_PARTNER.value)

        with Session(self.engine) as session:
            row = session.exec(
                select(CardResponse).where(
                    CardResponse.session_id == self.deck_session_id,
                    CardResponse.user_id == self.user_b_id,
                )
            ).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.content, "partner response")

    def test_deck_respond_rejects_non_participant(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.post(
            f"/api/card-decks/respond/{self.deck_session_id}",
            json={"content": "should not pass"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("沒有權限", response.json()["detail"])

        with Session(self.engine) as session:
            rows = session.exec(
                select(CardResponse).where(CardResponse.session_id == self.deck_session_id)
            ).all()
            self.assertEqual(len(rows), 0)

    def test_deck_respond_rejects_unknown_session(self) -> None:
        response = self.client.post(
            f"/api/card-decks/respond/{uuid.uuid4()}",
            json={"content": "missing session"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("找不到", response.json()["detail"])

    def test_deck_draw_allows_solo_user_without_partner_context(self) -> None:
        self.current_user_id = self.user_c_id
        response = self.client.post("/api/card-decks/draw", params={"category": "DAILY_VIBE"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["creator_id"], str(self.user_c_id))
        self.assertIsNone(payload.get("partner_id"))

    def test_deck_draw_does_not_return_other_pairs_active_session(self) -> None:
        with Session(self.engine) as session:
            user_c = session.get(User, self.user_c_id)
            user_d = session.get(User, self.user_d_id)
            assert user_c is not None
            assert user_d is not None
            user_c.partner_id = self.user_d_id
            user_d.partner_id = self.user_c_id
            session.add(user_c)
            session.add(user_d)
            session.commit()

        self.current_user_id = self.user_c_id
        response = self.client.post("/api/card-decks/draw", params={"category": "DAILY_VIBE"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotEqual(payload["id"], str(self.deck_session_id))

        with Session(self.engine) as session:
            returned_session = session.get(CardSession, uuid.UUID(payload["id"]))
            self.assertIsNotNone(returned_session)
            assert returned_session is not None
            self.assertEqual(returned_session.creator_id, self.user_c_id)
            self.assertEqual(returned_session.partner_id, self.user_d_id)
            self.assertEqual(returned_session.mode, CardSessionMode.DECK)


if __name__ == "__main__":
    unittest.main()
