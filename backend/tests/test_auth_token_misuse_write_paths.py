import sys
import unittest
from datetime import timedelta
from pathlib import Path
from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import journals  # noqa: E402
from app.api.routers import card_decks, cards, users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.user import User  # noqa: E402


class AuthTokenMisuseWritePathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(users.router, prefix="/api/users")
        app.include_router(journals.router, prefix="/api/journals")
        app.include_router(cards.router, prefix="/api/cards")
        app.include_router(card_decks.router, prefix="/api/card-decks")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

        with Session(self.engine) as session:
            user_a = User(
                email="token-write-a@example.com",
                full_name="Token Write A",
                hashed_password="hashed",
            )
            user_b = User(
                email="token-write-b@example.com",
                full_name="Token Write B",
                hashed_password="hashed",
            )
            user_a.partner_id = user_b.id
            user_b.partner_id = user_a.id

            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Token Write Card",
                description="desc",
                question="How are you?",
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

            self.user_id = user_a.id
            self.card_id = card.id
            self.deck_session_id = deck_session.id

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def _bearer_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _encode(self, payload: dict, *, secret: str | None = None) -> str:
        return jwt.encode(
            payload,
            secret or settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    def test_rejects_malformed_token_on_journal_create(self) -> None:
        response = self.client.post(
            "/api/journals/",
            json={"content": "token misuse"},
            headers=self._bearer_headers("not-a-jwt"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_forged_signature_on_card_respond(self) -> None:
        forged = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            },
            secret="forged-secret",
        )
        response = self.client.post(
            "/api/cards/respond",
            json={"card_id": str(self.card_id), "content": "token misuse"},
            headers=self._bearer_headers(forged),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_expired_token_on_deck_respond(self) -> None:
        expired = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() - timedelta(minutes=5),
            }
        )
        response = self.client.post(
            f"/api/card-decks/respond/{self.deck_session_id}",
            json={"content": "token misuse"},
            headers=self._bearer_headers(expired),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_non_uuid_subject_on_deck_draw(self) -> None:
        malformed_sub = self._encode(
            {
                "sub": "not-a-uuid",
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.post(
            "/api/card-decks/draw",
            params={"category": "DAILY_VIBE"},
            headers=self._bearer_headers(malformed_sub),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_malformed_token_on_invite_code_generation(self) -> None:
        response = self.client.post(
            "/api/users/invite-code",
            headers=self._bearer_headers("not-a-jwt"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_forged_signature_on_pairing(self) -> None:
        forged = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            },
            secret="forged-secret",
        )
        response = self.client.post(
            "/api/users/pair",
            json={"invite_code": "PAIR01"},
            headers=self._bearer_headers(forged),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_expired_token_on_notification_mark_read(self) -> None:
        expired = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() - timedelta(minutes=5),
            }
        )
        response = self.client.post(
            "/api/users/notifications/mark-read",
            headers=self._bearer_headers(expired),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_expired_token_on_data_erase(self) -> None:
        expired = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() - timedelta(minutes=5),
            }
        )
        response = self.client.delete(
            "/api/users/me/data",
            headers=self._bearer_headers(expired),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_soft_deleted_user_token_on_journal_create(self) -> None:
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            assert user is not None
            user.deleted_at = utcnow()
            user.is_active = True
            session.add(user)
            session.commit()

        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.post(
            "/api/journals/",
            json={"content": "should be rejected"},
            headers=self._bearer_headers(token),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_refresh_token_type_on_write_path(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "typ": "refresh",
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.post(
            "/api/journals/",
            json={"content": "refresh token must be rejected"},
            headers=self._bearer_headers(token),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")


if __name__ == "__main__":
    unittest.main()
