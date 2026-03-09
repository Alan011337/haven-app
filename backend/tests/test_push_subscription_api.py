# AUTHZ_MATRIX: POST /api/users/push-subscriptions
# AUTHZ_MATRIX: POST /api/users/push-subscriptions/dry-run
# AUTHZ_MATRIX: DELETE /api/users/push-subscriptions/{subscription_id}
# AUTHZ_DENY_MATRIX: DELETE /api/users/push-subscriptions/{subscription_id}

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
from app.api.routers import users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.push_subscription import PushSubscription, PushSubscriptionState  # noqa: E402
from app.models.user import User  # noqa: E402


class PushSubscriptionApiTests(unittest.TestCase):
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
            user_a = User(email="push-a@example.com", full_name="Push A", hashed_password="hashed")
            user_b = User(email="push-b@example.com", full_name="Push B", hashed_password="hashed")
            session.add(user_a)
            session.add(user_b)
            session.commit()
            session.refresh(user_a)
            session.refresh(user_b)
            self.user_a_id = user_a.id
            self.user_b_id = user_b.id

        self.current_user_id = self.user_a_id
        self.original_push_enabled = settings.PUSH_NOTIFICATIONS_ENABLED
        self.original_push_max = settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER
        self.original_dry_run_sample_size = settings.PUSH_DRY_RUN_SAMPLE_SIZE
        settings.PUSH_NOTIFICATIONS_ENABLED = True
        settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER = 10
        settings.PUSH_DRY_RUN_SAMPLE_SIZE = 2

    def tearDown(self) -> None:
        settings.PUSH_NOTIFICATIONS_ENABLED = self.original_push_enabled
        settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER = self.original_push_max
        settings.PUSH_DRY_RUN_SAMPLE_SIZE = self.original_dry_run_sample_size
        self.client.close()
        self.engine.dispose()

    @staticmethod
    def _payload(endpoint: str) -> dict:
        return {
            "endpoint": endpoint,
            "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
            "user_agent": "pytest-agent",
        }

    def test_upsert_and_list_scoped_to_current_user(self) -> None:
        created = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/sub-a"),
        )
        self.assertEqual(created.status_code, 200)
        payload = created.json()
        self.assertTrue(payload["created"])
        self.assertEqual(payload["subscription"]["state"], "ACTIVE")
        self.assertEqual(len(payload["subscription"]["endpoint_hash"]), 64)
        self.assertNotIn("endpoint", payload["subscription"])

        listed = self.client.get("/api/users/push-subscriptions")
        self.assertEqual(listed.status_code, 200)
        items = listed.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], payload["subscription"]["id"])

        self.current_user_id = self.user_b_id
        other_listed = self.client.get("/api/users/push-subscriptions")
        self.assertEqual(other_listed.status_code, 200)
        self.assertEqual(other_listed.json(), [])

    def test_rejects_endpoint_claimed_by_other_user(self) -> None:
        first = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/shared"),
        )
        self.assertEqual(first.status_code, 200)

        self.current_user_id = self.user_b_id
        second = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/shared"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("already registered", second.json()["detail"])

    def test_enforces_max_subscription_cap(self) -> None:
        settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER = 1
        first = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/cap-1"),
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/cap-2"),
        )
        self.assertEqual(second.status_code, 429)

    def test_delete_rejects_other_owner_then_tombstones_owner_subscription(self) -> None:
        created = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/delete-me"),
        )
        self.assertEqual(created.status_code, 200)
        subscription_id = uuid.UUID(created.json()["subscription"]["id"])

        self.current_user_id = self.user_b_id
        forbidden = self.client.delete(f"/api/users/push-subscriptions/{subscription_id}")
        self.assertEqual(forbidden.status_code, 404)

        self.current_user_id = self.user_a_id
        removed = self.client.delete(f"/api/users/push-subscriptions/{subscription_id}")
        self.assertEqual(removed.status_code, 200)
        self.assertTrue(removed.json()["deleted"])

        with Session(self.engine) as session:
            row = session.get(PushSubscription, subscription_id)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.state, PushSubscriptionState.TOMBSTONED)
            self.assertIsNotNone(row.deleted_at)

    def test_dry_run_samples_active_subscriptions(self) -> None:
        first = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/dry-1"),
        )
        second = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/dry-2"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        dry_run = self.client.post(
            "/api/users/push-subscriptions/dry-run",
            json={"sample_size": 1},
        )
        self.assertEqual(dry_run.status_code, 200)
        payload = dry_run.json()
        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["sampled_count"], 1)
        self.assertEqual(payload["active_count"], 2)
        self.assertEqual(len(payload["sampled_subscription_ids"]), 1)

        with Session(self.engine) as session:
            rows = session.exec(
                select(PushSubscription).where(PushSubscription.user_id == self.user_a_id)
            ).all()
            sampled = [row for row in rows if row.dry_run_sampled_at is not None]
            self.assertEqual(len(sampled), 1)

    def test_upsert_returns_503_when_push_channel_disabled(self) -> None:
        settings.PUSH_NOTIFICATIONS_ENABLED = False
        response = self.client.post(
            "/api/users/push-subscriptions",
            json=self._payload("https://push.example.com/disabled"),
        )
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
