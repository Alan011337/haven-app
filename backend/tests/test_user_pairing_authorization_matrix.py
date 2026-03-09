# AUTHZ_MATRIX: POST /api/users/invite-code
# AUTHZ_MATRIX: POST /api/users/pair

import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import users  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402


class UserPairingAuthorizationMatrixTests(unittest.TestCase):
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
            user_a = User(email="pair-a@example.com", full_name="Pair A", hashed_password="hashed")
            user_b = User(
                email="pair-b@example.com",
                full_name="Pair B",
                hashed_password="hashed",
                invite_code="PAIRB1",
                invite_code_created_at=utcnow(),
            )
            user_c = User(email="pair-c@example.com", full_name="Pair C", hashed_password="hashed")
            user_d = User(email="pair-d@example.com", full_name="Pair D", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.add(user_c)
            session.add(user_d)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            session.refresh(user_c)
            session.refresh(user_d)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id
            self.user_c_id = user_c.id
            self.user_d_id = user_d.id

        self.current_user_id = self.user_a_id

    def tearDown(self) -> None:
        users.pairing_abuse_guard = self.original_pairing_guard
        users.pairing_ip_abuse_guard = self.original_pairing_ip_guard
        self.client.close()
        self.engine.dispose()

    def test_pair_success_updates_only_current_user_and_target(self) -> None:
        response = self.client.post("/api/users/pair", json={"invite_code": "  pairb1  "})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user_a_id))
        self.assertEqual(payload["partner_id"], str(self.user_b_id))

        with Session(self.engine) as session:
            user_a = session.get(User, self.user_a_id)
            user_b = session.get(User, self.user_b_id)
            user_c = session.get(User, self.user_c_id)
            user_d = session.get(User, self.user_d_id)
            self.assertIsNotNone(user_a)
            self.assertIsNotNone(user_b)
            self.assertIsNotNone(user_c)
            self.assertIsNotNone(user_d)
            assert user_a is not None
            assert user_b is not None
            assert user_c is not None
            assert user_d is not None
            self.assertEqual(user_a.partner_id, self.user_b_id)
            self.assertEqual(user_b.partner_id, self.user_a_id)
            self.assertIsNone(user_c.partner_id)
            self.assertIsNone(user_d.partner_id)
            self.assertIsNone(user_a.invite_code)
            self.assertIsNone(user_b.invite_code)

    def test_pair_rejects_target_already_paired_without_mutating_others(self) -> None:
        with Session(self.engine) as session:
            user_b = session.get(User, self.user_b_id)
            user_d = session.get(User, self.user_d_id)
            assert user_b is not None
            assert user_d is not None
            user_b.partner_id = self.user_d_id
            user_d.partner_id = self.user_b_id
            user_b.invite_code = "PAIRLOCK"
            user_b.invite_code_created_at = utcnow()
            session.add(user_b)
            session.add(user_d)
            session.commit()

        response = self.client.post("/api/users/pair", json={"invite_code": "PAIRLOCK"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "This user is already paired.")

        with Session(self.engine) as session:
            user_a = session.get(User, self.user_a_id)
            user_b = session.get(User, self.user_b_id)
            user_d = session.get(User, self.user_d_id)
            assert user_a is not None
            assert user_b is not None
            assert user_d is not None
            self.assertIsNone(user_a.partner_id)
            self.assertEqual(user_b.partner_id, self.user_d_id)
            self.assertEqual(user_d.partner_id, self.user_b_id)
            self.assertEqual(user_b.invite_code, "PAIRLOCK")

    def test_pair_rejects_self_invite_code_without_state_change(self) -> None:
        with Session(self.engine) as session:
            user_a = session.get(User, self.user_a_id)
            assert user_a is not None
            user_a.invite_code = "SELF01"
            user_a.invite_code_created_at = utcnow()
            session.add(user_a)
            session.commit()

        response = self.client.post("/api/users/pair", json={"invite_code": "self01"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "You cannot pair with yourself.")

        with Session(self.engine) as session:
            user_a = session.get(User, self.user_a_id)
            assert user_a is not None
            self.assertIsNone(user_a.partner_id)
            self.assertEqual(user_a.invite_code, "SELF01")

    def test_invite_code_generation_updates_only_current_user(self) -> None:
        with patch("app.api.routers.users.secrets.token_hex", return_value="abc123"):
            response = self.client.post("/api/users/invite-code")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "ABC123")

        with Session(self.engine) as session:
            user_a = session.get(User, self.user_a_id)
            user_b = session.get(User, self.user_b_id)
            user_c = session.get(User, self.user_c_id)
            assert user_a is not None
            assert user_b is not None
            assert user_c is not None
            self.assertEqual(user_a.invite_code, "ABC123")
            self.assertEqual(user_b.invite_code, "PAIRB1")
            self.assertIsNone(user_c.invite_code)


if __name__ == "__main__":
    unittest.main()
