from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.user import User  # noqa: E402
from app.services.entitlement_usage_runtime import consume_daily_quota  # noqa: E402


class EntitlementUsageRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            user = User(email="quota@example.com", hashed_password="hashed")
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_consume_daily_quota_allows_until_limit(self) -> None:
        with Session(self.engine) as session:
            allowed1, used1 = consume_daily_quota(
                session=session,
                user_id=self.user_id,
                feature_key="journals_per_day",
                quota_limit=2,
            )
            allowed2, used2 = consume_daily_quota(
                session=session,
                user_id=self.user_id,
                feature_key="journals_per_day",
                quota_limit=2,
            )
            allowed3, used3 = consume_daily_quota(
                session=session,
                user_id=self.user_id,
                feature_key="journals_per_day",
                quota_limit=2,
            )
            session.commit()

        self.assertTrue(allowed1)
        self.assertEqual(used1, 1)
        self.assertTrue(allowed2)
        self.assertEqual(used2, 2)
        self.assertFalse(allowed3)
        self.assertEqual(used3, 2)

    def test_consume_daily_quota_unlimited_bypasses_counter(self) -> None:
        with Session(self.engine) as session:
            allowed, used = consume_daily_quota(
                session=session,
                user_id=self.user_id,
                feature_key="card_draws_per_day",
                quota_limit=None,
            )
        self.assertTrue(allowed)
        self.assertEqual(used, 0)


if __name__ == "__main__":
    unittest.main()
