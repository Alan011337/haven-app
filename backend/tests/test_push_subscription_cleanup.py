import importlib.util
import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.push_subscription import PushSubscription, PushSubscriptionState  # noqa: E402
from app.models.user import User  # noqa: E402

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_push_subscription_cleanup.py"
_SPEC = importlib.util.spec_from_file_location("run_push_subscription_cleanup", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load cleanup module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class PushSubscriptionCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        now = utcnow()
        with Session(self.engine) as session:
            user = User(email="cleanup@example.com", full_name="Cleanup", hashed_password="hashed")
            session.add(user)
            session.commit()
            session.refresh(user)
            self.user_id = user.id

            self.invalid_id = uuid.uuid4()
            self.tombstoned_id = uuid.uuid4()

            session.add(
                PushSubscription(
                    id=self.invalid_id,
                    user_id=user.id,
                    endpoint="https://push.example.com/invalid",
                    endpoint_hash="invalidhash",
                    p256dh_key="k1",
                    auth_key="a1",
                    state=PushSubscriptionState.INVALID,
                    updated_at=now - timedelta(days=10),
                    created_at=now - timedelta(days=20),
                    fail_reason="410 gone",
                )
            )
            session.add(
                PushSubscription(
                    id=self.tombstoned_id,
                    user_id=user.id,
                    endpoint="https://push.example.com/tomb",
                    endpoint_hash="tombhash",
                    p256dh_key="k2",
                    auth_key="a2",
                    state=PushSubscriptionState.TOMBSTONED,
                    updated_at=now - timedelta(days=40),
                    created_at=now - timedelta(days=50),
                    deleted_at=now - timedelta(days=40),
                    fail_reason="user_opt_out",
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_dry_run_reports_without_state_changes(self) -> None:
        now = utcnow()
        with Session(self.engine) as session:
            result = _MODULE.cleanup_push_subscriptions(
                session,
                now=now,
                dry_run=True,
                invalid_retention_days=7,
                tombstone_purge_days=30,
            )

            self.assertTrue(result["dry_run"])
            self.assertEqual(result["invalid_to_tombstone_count"], 1)
            self.assertEqual(result["tombstone_to_purge_count"], 1)

            invalid_row = session.get(PushSubscription, self.invalid_id)
            tomb_row = session.get(PushSubscription, self.tombstoned_id)
            self.assertIsNotNone(invalid_row)
            self.assertIsNotNone(tomb_row)
            assert invalid_row is not None
            assert tomb_row is not None
            self.assertEqual(invalid_row.state, PushSubscriptionState.INVALID)
            self.assertEqual(tomb_row.state, PushSubscriptionState.TOMBSTONED)

    def test_execute_transitions_and_is_idempotent(self) -> None:
        now = utcnow()
        with Session(self.engine) as session:
            first = _MODULE.cleanup_push_subscriptions(
                session,
                now=now,
                dry_run=False,
                invalid_retention_days=7,
                tombstone_purge_days=30,
            )
            self.assertFalse(first["dry_run"])
            self.assertEqual(first["invalid_to_tombstone_count"], 1)
            self.assertEqual(first["tombstone_to_purge_count"], 1)

            invalid_row = session.get(PushSubscription, self.invalid_id)
            tomb_row = session.get(PushSubscription, self.tombstoned_id)
            self.assertIsNotNone(invalid_row)
            self.assertIsNotNone(tomb_row)
            assert invalid_row is not None
            assert tomb_row is not None
            self.assertEqual(invalid_row.state, PushSubscriptionState.TOMBSTONED)
            self.assertEqual(tomb_row.state, PushSubscriptionState.PURGED)
            self.assertTrue(tomb_row.endpoint.startswith("purged:"))
            self.assertEqual(tomb_row.p256dh_key, "[purged]")
            self.assertEqual(tomb_row.auth_key, "[purged]")

            second = _MODULE.cleanup_push_subscriptions(
                session,
                now=now + timedelta(minutes=1),
                dry_run=False,
                invalid_retention_days=7,
                tombstone_purge_days=30,
            )
            self.assertEqual(second["invalid_to_tombstone_count"], 0)
            self.assertEqual(second["tombstone_to_purge_count"], 0)


if __name__ == "__main__":
    unittest.main()

