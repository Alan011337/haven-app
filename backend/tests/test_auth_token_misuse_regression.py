import sys
import unittest
import uuid
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

from app.api.routers import cards, users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.billing import BillingEntitlementState  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.user import User  # noqa: E402


class AuthTokenMisuseRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()
        app.include_router(cards.router, prefix="/api/cards")
        app.include_router(users.router, prefix="/api/users")

        def override_get_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        self.client = TestClient(app)

        with Session(self.engine) as session:
            self.user = User(
                email="token-owner@example.com",
                full_name="Token Owner",
                hashed_password="hashed",
            )
            card = Card(
                category=CardCategory.DAILY_VIBE,
                title="Token Misuse Card",
                description="desc",
                question="question",
                difficulty_level=1,
                is_ai_generated=False,
            )
            session.add(self.user)
            session.add(card)
            session.commit()
            session.refresh(self.user)
            self.user_id = self.user.id
            session.add(
                BillingEntitlementState(
                    user_id=self.user_id,
                    lifecycle_state="ACTIVE",
                    current_plan="premium",
                )
            )
            session.commit()

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

    def test_valid_token_allows_access(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.user_id))

    def test_valid_token_allows_cards_catalog_read(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/cards/", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_valid_token_allows_notification_mark_read(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.post(
            "/api/users/notifications/mark-read",
            headers=self._bearer_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 0)

    def test_valid_token_allows_data_export(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me/data-export", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], str(self.user_id))

    def test_valid_token_allows_data_erase(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.delete("/api/users/me/data", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_user_id"], str(self.user_id))

    def test_token_becomes_invalid_after_data_erase_hard_delete(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        erase_response = self.client.delete("/api/users/me/data", headers=self._bearer_headers(token))
        self.assertEqual(erase_response.status_code, 200)
        self.assertEqual(erase_response.json()["status"], "erased")

        follow_up_response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(follow_up_response.status_code, 401)
        self.assertEqual(follow_up_response.json()["detail"], "Could not validate credentials")

    def test_token_becomes_invalid_after_data_erase_soft_delete(self) -> None:
        previous_value = settings.DATA_SOFT_DELETE_ENABLED
        settings.DATA_SOFT_DELETE_ENABLED = True
        try:
            token = self._encode(
                {
                    "sub": str(self.user_id),
                    "exp": utcnow() + timedelta(minutes=5),
                }
            )
            erase_response = self.client.delete("/api/users/me/data", headers=self._bearer_headers(token))
            self.assertEqual(erase_response.status_code, 200)
            self.assertEqual(erase_response.json()["status"], "soft_deleted")

            follow_up_response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
            self.assertEqual(follow_up_response.status_code, 401)
            self.assertEqual(follow_up_response.json()["detail"], "Could not validate credentials")
        finally:
            settings.DATA_SOFT_DELETE_ENABLED = previous_value

    def test_rejects_expired_token(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() - timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_forged_signature(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            },
            secret="forged-secret",
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_malformed_token(self) -> None:
        response = self.client.get("/api/users/me", headers=self._bearer_headers("not-a-jwt"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_malformed_token_on_cards_catalog_read(self) -> None:
        response = self.client.get(
            "/api/cards/",
            headers=self._bearer_headers("not-a-jwt"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_malformed_token_on_notification_mark_read(self) -> None:
        response = self.client.post(
            "/api/users/notifications/mark-read",
            headers=self._bearer_headers("not-a-jwt"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_malformed_token_on_data_export(self) -> None:
        response = self.client.get(
            "/api/users/me/data-export",
            headers=self._bearer_headers("not-a-jwt"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_malformed_token_on_data_erase(self) -> None:
        response = self.client.delete(
            "/api/users/me/data",
            headers=self._bearer_headers("not-a-jwt"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_refresh_token_type_on_authenticated_read(self) -> None:
        token = self._encode(
            {
                "sub": str(self.user_id),
                "typ": "refresh",
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_token_without_sub(self) -> None:
        token = self._encode({"exp": utcnow() + timedelta(minutes=5)})
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_token_with_non_uuid_subject(self) -> None:
        token = self._encode(
            {
                "sub": "not-a-uuid",
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_token_for_nonexistent_user(self) -> None:
        token = self._encode(
            {
                "sub": str(uuid.uuid4()),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_token_for_inactive_user(self) -> None:
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            assert user is not None
            user.is_active = False
            session.add(user)
            session.commit()

        token = self._encode(
            {
                "sub": str(self.user_id),
                "exp": utcnow() + timedelta(minutes=5),
            }
        )
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")

    def test_rejects_token_for_soft_deleted_user_even_if_active(self) -> None:
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
        response = self.client.get("/api/users/me", headers=self._bearer_headers(token))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Could not validate credentials")


if __name__ == "__main__":
    unittest.main()
