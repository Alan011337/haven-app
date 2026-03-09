from __future__ import annotations

import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.push_subscription import PushSubscription, PushSubscriptionState  # noqa: E402
from app.services.notification_multichannel import _load_active_push_subscriptions  # noqa: E402


class NotificationPushDispatchFanoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine, tables=[PushSubscription.__table__])
        self.user_id = uuid.uuid4()

    def tearDown(self) -> None:
        self.engine.dispose()

    def _seed_subscriptions(self, count: int) -> None:
        now = utcnow()
        with Session(self.engine) as session:
            for idx in range(count):
                session.add(
                    PushSubscription(
                        user_id=self.user_id,
                        endpoint=f"https://example.com/push/{idx}",
                        endpoint_hash=f"h-{idx}",
                        p256dh_key=f"p256-{idx}",
                        auth_key=f"auth-{idx}",
                        state=PushSubscriptionState.ACTIVE,
                        updated_at=now - timedelta(seconds=idx),
                    )
                )
            session.commit()

    def test_load_active_subscriptions_uses_batching_and_max_cap(self) -> None:
        self._seed_subscriptions(12)
        with patch("app.db.session.engine", self.engine), patch(
            "app.services.notification_multichannel._push_dispatch_max_active_subscriptions",
            return_value=9,
        ), patch(
            "app.services.notification_multichannel._push_dispatch_batch_size",
            return_value=4,
        ):
            rows = _load_active_push_subscriptions(receiver_user_id=self.user_id)

        self.assertEqual(len(rows), 9)
        updated = [row.updated_at for row in rows]
        self.assertEqual(updated, sorted(updated, reverse=True))


if __name__ == "__main__":
    unittest.main()
