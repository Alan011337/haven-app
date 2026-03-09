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
from app.api.routers import users  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.pairing_abuse_guard import PairingAbuseGuard  # noqa: E402
from app.services.rate_limit_runtime_metrics import RateLimitRuntimeMetrics  # noqa: E402


class PairingRateLimitApiTests(unittest.TestCase):
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
        self.original_rate_limit_runtime_metrics = users.rate_limit_runtime_metrics
        users.rate_limit_runtime_metrics = RateLimitRuntimeMetrics()

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
            self.user_a = User(email="a@example.com", full_name="A", hashed_password="hashed")
            self.user_b = User(
                email="b@example.com",
                full_name="B",
                hashed_password="hashed",
                invite_code="VALID01",
                invite_code_created_at=utcnow(),
            )
            self.user_c = User(email="c@example.com", full_name="C", hashed_password="hashed")
            session.add(self.user_a)
            session.add(self.user_b)
            session.add(self.user_c)
            session.commit()
            session.refresh(self.user_a)
            session.refresh(self.user_b)
            session.refresh(self.user_c)
            self.current_user_id = self.user_a.id

    def tearDown(self) -> None:
        users.pairing_abuse_guard = self.original_pairing_guard
        users.pairing_ip_abuse_guard = self.original_pairing_ip_guard
        users.rate_limit_runtime_metrics = self.original_rate_limit_runtime_metrics
        self.client.close()
        self.engine.dispose()

    def _install_guard(
        self,
        *,
        user_limit_count: int = 10,
        user_window_seconds: int = 300,
        user_failure_threshold: int = 5,
        user_cooldown_seconds: int = 600,
        ip_limit_count: int = 30,
        ip_window_seconds: int = 300,
        ip_failure_threshold: int = 15,
        ip_cooldown_seconds: int = 900,
    ) -> None:
        users.pairing_abuse_guard = PairingAbuseGuard(
            limit_count=user_limit_count,
            window_seconds=user_window_seconds,
            failure_threshold=user_failure_threshold,
            cooldown_seconds=user_cooldown_seconds,
        )
        users.pairing_ip_abuse_guard = PairingAbuseGuard(
            limit_count=ip_limit_count,
            window_seconds=ip_window_seconds,
            failure_threshold=ip_failure_threshold,
            cooldown_seconds=ip_cooldown_seconds,
        )

    def test_pair_rate_limited_after_too_many_attempts(self) -> None:
        self._install_guard(
            user_limit_count=2,
            user_window_seconds=300,
            user_failure_threshold=999,
            user_cooldown_seconds=300,
            ip_limit_count=100,
            ip_window_seconds=300,
            ip_failure_threshold=999,
            ip_cooldown_seconds=300,
        )

        response1 = self.client.post("/api/users/pair", json={"invite_code": "BAD01"})
        response2 = self.client.post("/api/users/pair", json={"invite_code": "BAD02"})
        response3 = self.client.post("/api/users/pair", json={"invite_code": "BAD03"})

        self.assertEqual(response1.status_code, 400)
        self.assertEqual(response2.status_code, 400)
        self.assertEqual(response3.status_code, 429)
        self.assertIn("Too many pairing attempts", response3.json()["detail"])
        self.assertIn("Retry-After", response3.headers)
        self.assertGreaterEqual(int(response3.headers["Retry-After"]), 1)
        runtime_snapshot = users.rate_limit_runtime_metrics.snapshot()
        self.assertEqual(runtime_snapshot["blocked_by_action"].get("pairing_attempt"), 1)
        self.assertEqual(runtime_snapshot["blocked_by_scope"].get("user"), 1)

    def test_pair_cooldown_blocks_even_with_valid_code(self) -> None:
        self._install_guard(
            user_limit_count=100,
            user_window_seconds=300,
            user_failure_threshold=2,
            user_cooldown_seconds=300,
            ip_limit_count=100,
            ip_window_seconds=300,
            ip_failure_threshold=999,
            ip_cooldown_seconds=300,
        )

        response1 = self.client.post("/api/users/pair", json={"invite_code": "BAD01"})
        response2 = self.client.post("/api/users/pair", json={"invite_code": "BAD02"})
        response3 = self.client.post("/api/users/pair", json={"invite_code": "VALID01"})

        self.assertEqual(response1.status_code, 400)
        self.assertEqual(response2.status_code, 400)
        self.assertEqual(response3.status_code, 429)
        self.assertIn("temporarily locked", response3.json()["detail"])
        self.assertIn("Retry-After", response3.headers)
        self.assertGreaterEqual(int(response3.headers["Retry-After"]), 1)

    def test_pair_ip_rate_limit_blocks_across_different_users(self) -> None:
        self._install_guard(
            user_limit_count=100,
            user_window_seconds=300,
            user_failure_threshold=999,
            user_cooldown_seconds=300,
            ip_limit_count=2,
            ip_window_seconds=300,
            ip_failure_threshold=999,
            ip_cooldown_seconds=300,
        )
        headers = {"x-forwarded-for": "203.0.113.11"}

        self.current_user_id = self.user_a.id
        response1 = self.client.post("/api/users/pair", json={"invite_code": "BAD01"}, headers=headers)

        self.current_user_id = self.user_c.id
        response2 = self.client.post("/api/users/pair", json={"invite_code": "BAD02"}, headers=headers)
        response3 = self.client.post("/api/users/pair", json={"invite_code": "BAD03"}, headers=headers)

        self.assertEqual(response1.status_code, 400)
        self.assertEqual(response2.status_code, 400)
        self.assertEqual(response3.status_code, 429)
        self.assertIn("Too many pairing attempts", response3.json()["detail"])
        self.assertIn("Retry-After", response3.headers)
        self.assertGreaterEqual(int(response3.headers["Retry-After"]), 1)


if __name__ == "__main__":
    unittest.main()
