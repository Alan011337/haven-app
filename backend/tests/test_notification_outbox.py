import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.datetime_utils import utcnow  # noqa: E402
from app.models.notification_outbox import NotificationOutbox, NotificationOutboxStatus  # noqa: E402
from app.models.user import User  # noqa: F401,E402
from app.services import notification, notification_outbox  # noqa: E402
from app.services.notification_runtime_metrics import notification_runtime_metrics  # noqa: E402


class NotificationOutboxTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        notification.reset_notification_dedupe_state_for_test()
        notification_runtime_metrics.reset()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    async def test_queue_uses_outbox_path_when_feature_enabled(self) -> None:
        with patch.object(notification, "_is_notification_outbox_enabled", return_value=True), patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ), patch.object(
            notification, "_record_notification_event"
        ) as mock_record, patch(
            "app.services.notification_outbox.enqueue_notification_outbox",
            return_value=uuid.uuid4(),
        ) as mock_enqueue, patch.object(
            notification.asyncio, "create_task"
        ) as mock_create_task:
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                dedupe_key="outbox:test:1",
            )

        mock_enqueue.assert_called_once()
        mock_create_task.assert_not_called()
        statuses = [c.kwargs.get("status") for c in mock_record.call_args_list]
        self.assertIn("QUEUED", statuses)

    async def test_process_outbox_batch_marks_email_success_as_sent(self) -> None:
        row = NotificationOutbox(
            receiver_email="partner@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PENDING,
            max_attempts=3,
            available_at=utcnow(),
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id

        with patch.object(notification_outbox, "engine", self.engine), patch(
            "app.services.notification.send_partner_notification",
            AsyncMock(return_value=True),
        ):
            summary = await notification_outbox.process_notification_outbox_batch(limit=10)

        self.assertEqual(summary["selected"], 1)
        self.assertEqual(summary["sent"], 1)
        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.SENT)
            self.assertEqual(saved.attempt_count, 1)

    async def test_process_outbox_retries_then_moves_to_dead_and_releases_dedupe(self) -> None:
        key = "outbox:test:dedupe-release"
        self.assertTrue(notification._reserve_notification_slot(key))
        row = NotificationOutbox(
            receiver_email="partner@example.com",
            sender_name="Alex",
            action_type="journal",
            dedupe_key=key,
            dedupe_slot_reserved=True,
            status=NotificationOutboxStatus.PENDING,
            max_attempts=2,
            available_at=utcnow(),
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id

        with patch.object(notification_outbox, "engine", self.engine), patch.object(
            notification_outbox.settings, "NOTIFICATION_OUTBOX_RETRY_BASE_SECONDS", 1
        ), patch(
            "app.services.notification.send_partner_notification",
            AsyncMock(return_value=False),
        ):
            first = await notification_outbox.process_notification_outbox_batch(limit=10)
            self.assertEqual(first["retried"], 1)

            with Session(self.engine) as session:
                retry_row = session.get(NotificationOutbox, row_id)
                assert retry_row is not None
                retry_row.available_at = utcnow()
                session.add(retry_row)
                session.commit()

            second = await notification_outbox.process_notification_outbox_batch(limit=10)
            self.assertEqual(second["dead"], 1)

        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.DEAD)
            self.assertEqual(saved.attempt_count, 2)

        self.assertTrue(notification._reserve_notification_slot(key))

    async def test_process_outbox_multichannel_success_marks_sent(self) -> None:
        row = NotificationOutbox(
            receiver_email="partner@example.com",
            sender_name="Alex",
            action_type="journal",
            event_type="journal_created",
            receiver_user_id=uuid.uuid4(),
            status=NotificationOutboxStatus.PENDING,
            available_at=utcnow(),
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id

        with patch.object(notification_outbox, "engine", self.engine), patch(
            "app.services.notification_multichannel.dispatch_multichannel",
            AsyncMock(return_value={"email": False, "in_app_ws": True}),
        ):
            summary = await notification_outbox.process_notification_outbox_batch(limit=10)

        self.assertEqual(summary["sent"], 1)
        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.SENT)

    async def test_process_outbox_defers_email_fallback_without_sleeping_worker(self) -> None:
        receiver_user_id = uuid.uuid4()
        row = NotificationOutbox(
            receiver_email="partner@example.com",
            sender_name="Alex",
            action_type="journal",
            event_type="journal_created",
            receiver_user_id=receiver_user_id,
            status=NotificationOutboxStatus.PENDING,
            available_at=utcnow(),
            max_attempts=3,
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id
            created_at = row.created_at

        with patch.object(notification_outbox, "engine", self.engine), patch(
            "app.services.notification_multichannel.dispatch_multichannel",
            AsyncMock(return_value={"email": False, "in_app_ws": False}),
        ), patch(
            "app.services.notification.is_email_notification_enabled",
            return_value=True,
        ), patch(
            "app.services.notification._is_receiver_email_opted_out",
            return_value=False,
        ), patch(
            "app.services.notification.send_partner_notification_with_retry",
            AsyncMock(return_value=False),
        ) as mock_email_retry, patch.object(
            notification_outbox.settings,
            "NOTIFICATION_EMAIL_FALLBACK_DELAY_SECONDS",
            120,
        ):
            summary = await notification_outbox.process_notification_outbox_batch(limit=10)

        self.assertEqual(summary["retried"], 1)
        mock_email_retry.assert_not_awaited()
        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.RETRY)
            self.assertEqual(saved.last_error_reason, "email_fallback_deferred")
            self.assertIsNotNone(saved.available_at)
            assert saved.available_at is not None
            self.assertGreaterEqual(
                int((saved.available_at - created_at).total_seconds()),
                120,
            )

    async def test_claim_ready_outbox_ids_is_atomic_for_processing_status(self) -> None:
        row = NotificationOutbox(
            receiver_email="partner@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PENDING,
            available_at=utcnow(),
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id

        now = utcnow()
        with patch.object(notification_outbox, "engine", self.engine):
            with Session(self.engine) as first_session:
                first_claim = notification_outbox._claim_ready_outbox_ids(
                    session=first_session,
                    now_utc=now,
                    limit=10,
                )
            with Session(self.engine) as second_session:
                second_claim = notification_outbox._claim_ready_outbox_ids(
                    session=second_session,
                    now_utc=now,
                    limit=10,
                )

        self.assertEqual(first_claim, [row_id])
        self.assertEqual(second_claim, [])
        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.PROCESSING)
        metrics = notification_runtime_metrics.snapshot()
        self.assertEqual(metrics.get("notification_outbox_claim_round_total"), 1)
        self.assertEqual(metrics.get("notification_outbox_claim_candidate_total"), 1)
        self.assertEqual(metrics.get("notification_outbox_claimed_total"), 1)
        self.assertEqual(metrics.get("notification_outbox_claim_gap_total", 0), 0)

    async def test_process_outbox_reclaims_stale_processing_rows(self) -> None:
        stale_time = utcnow() - timedelta(minutes=10)
        row = NotificationOutbox(
            receiver_email="partner@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PROCESSING,
            available_at=stale_time,
            updated_at=stale_time,
            max_attempts=3,
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id

        with patch.object(notification_outbox, "engine", self.engine), patch.object(
            notification_outbox.settings,
            "NOTIFICATION_OUTBOX_PROCESSING_TIMEOUT_SECONDS",
            60,
        ), patch(
            "app.services.notification.send_partner_notification",
            AsyncMock(return_value=True),
        ):
            summary = await notification_outbox.process_notification_outbox_batch(limit=10)

        self.assertGreaterEqual(summary.get("reclaimed", 0), 1)
        self.assertEqual(summary["sent"], 1)
        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.SENT)

    async def test_cleanup_notification_outbox_purges_old_terminal_rows(self) -> None:
        now = utcnow()
        old_sent = NotificationOutbox(
            receiver_email="old-sent@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.SENT,
            available_at=now - timedelta(days=40),
            updated_at=now - timedelta(days=40),
        )
        old_dead = NotificationOutbox(
            receiver_email="old-dead@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.DEAD,
            available_at=now - timedelta(days=60),
            updated_at=now - timedelta(days=60),
        )
        recent_sent = NotificationOutbox(
            receiver_email="recent-sent@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.SENT,
            available_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        pending = NotificationOutbox(
            receiver_email="pending@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PENDING,
            available_at=now,
            updated_at=now,
        )

        with Session(self.engine) as session:
            session.add(old_sent)
            session.add(old_dead)
            session.add(recent_sent)
            session.add(pending)
            session.commit()

        with patch.object(notification_outbox, "engine", self.engine):
            summary = notification_outbox.cleanup_notification_outbox(
                sent_retention_days=14,
                dead_retention_days=30,
            )

        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["purged_sent"], 1)
        self.assertEqual(summary["purged_dead"], 1)

        with Session(self.engine) as session:
            remaining = session.exec(select(NotificationOutbox)).all()
            self.assertEqual(len(remaining), 2)
            remaining_statuses = {row.status for row in remaining}
            self.assertIn(NotificationOutboxStatus.SENT, remaining_statuses)
            self.assertIn(NotificationOutboxStatus.PENDING, remaining_statuses)

    async def test_replay_dead_notification_outbox_moves_rows_to_retry(self) -> None:
        row = NotificationOutbox(
            receiver_email="dead@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.DEAD,
            attempt_count=5,
            max_attempts=5,
            dedupe_slot_reserved=True,
            last_error_reason="retry_exhausted",
            available_at=utcnow() - timedelta(minutes=10),
            updated_at=utcnow() - timedelta(minutes=5),
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            row_id = row.id

        with patch.object(notification_outbox, "engine", self.engine):
            summary = notification_outbox.replay_dead_notification_outbox(
                limit=10,
                reset_attempt_count=True,
            )

        self.assertEqual(summary["selected"], 1)
        self.assertEqual(summary["replayed"], 1)
        self.assertEqual(summary["errors"], 0)

        with Session(self.engine) as session:
            saved = session.get(NotificationOutbox, row_id)
            assert saved is not None
            self.assertEqual(saved.status, NotificationOutboxStatus.RETRY)
            self.assertEqual(saved.attempt_count, 0)
            self.assertEqual(saved.last_error_reason, "manual_replay_requested")
            self.assertFalse(saved.dedupe_slot_reserved)

    async def test_auto_replay_dead_notification_outbox_triggers_on_threshold(self) -> None:
        row_dead_a = NotificationOutbox(
            receiver_email="dead-a@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.DEAD,
            attempt_count=3,
            max_attempts=3,
            available_at=utcnow() - timedelta(minutes=5),
            updated_at=utcnow() - timedelta(minutes=5),
        )
        row_dead_b = NotificationOutbox(
            receiver_email="dead-b@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.DEAD,
            attempt_count=3,
            max_attempts=3,
            available_at=utcnow() - timedelta(minutes=4),
            updated_at=utcnow() - timedelta(minutes=4),
        )
        with Session(self.engine) as session:
            session.add(row_dead_a)
            session.add(row_dead_b)
            session.commit()

        with patch.object(notification_outbox, "engine", self.engine):
            summary = notification_outbox.auto_replay_dead_notification_outbox(
                enabled=True,
                replay_limit=1,
                min_dead_rows=1,
                min_dead_letter_rate=0.5,
            )

        self.assertEqual(summary["triggered"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["replayed"], 1)

    async def test_auto_replay_dead_notification_outbox_skips_when_disabled(self) -> None:
        with patch.object(notification_outbox, "engine", self.engine):
            summary = notification_outbox.auto_replay_dead_notification_outbox(
                enabled=False,
                replay_limit=5,
                min_dead_rows=1,
                min_dead_letter_rate=0.0,
            )
        self.assertEqual(summary["enabled"], 0)
        self.assertEqual(summary["triggered"], 0)
        self.assertEqual(summary["replayed"], 0)

    async def test_get_notification_outbox_oldest_pending_age_seconds(self) -> None:
        now = utcnow()
        row_old = NotificationOutbox(
            receiver_email="pending-old@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PENDING,
            available_at=now - timedelta(minutes=10),
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
        )
        row_new = NotificationOutbox(
            receiver_email="pending-new@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.RETRY,
            available_at=now - timedelta(minutes=2),
            created_at=now - timedelta(minutes=2),
            updated_at=now - timedelta(minutes=2),
        )
        with Session(self.engine) as session:
            session.add(row_old)
            session.add(row_new)
            session.commit()

        with patch.object(notification_outbox, "engine", self.engine):
            age_seconds = notification_outbox.get_notification_outbox_oldest_pending_age_seconds()

        self.assertGreaterEqual(age_seconds, 600)

    async def test_get_notification_outbox_stale_processing_count(self) -> None:
        now = utcnow()
        row_stale = NotificationOutbox(
            receiver_email="processing-stale@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PROCESSING,
            available_at=now - timedelta(minutes=10),
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
        )
        row_fresh = NotificationOutbox(
            receiver_email="processing-fresh@example.com",
            sender_name="Alex",
            action_type="journal",
            status=NotificationOutboxStatus.PROCESSING,
            available_at=now - timedelta(seconds=20),
            created_at=now - timedelta(seconds=20),
            updated_at=now - timedelta(seconds=20),
        )
        with Session(self.engine) as session:
            session.add(row_stale)
            session.add(row_fresh)
            session.commit()

        with patch.object(notification_outbox, "engine", self.engine), patch.object(
            notification_outbox.settings,
            "NOTIFICATION_OUTBOX_PROCESSING_TIMEOUT_SECONDS",
            60,
        ):
            stale_count = notification_outbox.get_notification_outbox_stale_processing_count()
        self.assertEqual(stale_count, 1)

    def test_resolve_notification_outbox_claim_limit_scales_with_backlog(self) -> None:
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=50,
                backlog_depth=120,
                adaptive_enabled=True,
                adaptive_max_limit=500,
            ),
            50,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=50,
                backlog_depth=260,
                adaptive_enabled=True,
                adaptive_max_limit=500,
            ),
            150,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=50,
                backlog_depth=520,
                adaptive_enabled=True,
                adaptive_max_limit=500,
            ),
            200,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=50,
                backlog_depth=1200,
                adaptive_enabled=True,
                adaptive_max_limit=500,
            ),
            400,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=50,
                backlog_depth=4000,
                adaptive_enabled=True,
                adaptive_max_limit=300,
            ),
            300,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=50,
                backlog_depth=4000,
                adaptive_enabled=False,
                adaptive_max_limit=500,
            ),
            50,
        )

    def test_resolve_notification_outbox_claim_limit_scales_with_oldest_pending_age(self) -> None:
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=40,
                backlog_depth=10,
                oldest_pending_age_seconds=100,
                adaptive_enabled=True,
                adaptive_max_limit=500,
                age_scale_threshold_seconds=300,
                age_critical_seconds=1200,
            ),
            40,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=40,
                backlog_depth=10,
                oldest_pending_age_seconds=350,
                adaptive_enabled=True,
                adaptive_max_limit=500,
                age_scale_threshold_seconds=300,
                age_critical_seconds=1200,
            ),
            80,
        )
        self.assertEqual(
            notification_outbox.resolve_notification_outbox_claim_limit(
                base_limit=40,
                backlog_depth=10,
                oldest_pending_age_seconds=1300,
                adaptive_enabled=True,
                adaptive_max_limit=500,
                age_scale_threshold_seconds=300,
                age_critical_seconds=1200,
            ),
            320,
        )

    def test_evaluate_notification_outbox_backpressure_triggers_on_depth(self) -> None:
        config = type(
            "_Cfg",
            (),
            {
                "backlog_throttle_enabled": True,
                "backlog_throttle_depth_threshold": 2000,
                "backlog_throttle_oldest_pending_seconds_threshold": 1200,
                "backlog_throttle_exempt_event_types": (),
                "backlog_throttle_exempt_action_types": ("journal",),
            },
        )()
        with patch.object(notification_outbox, "get_notification_outbox_depth", return_value=2100), patch.object(
            notification_outbox,
            "get_notification_outbox_oldest_pending_age_seconds",
            return_value=20,
        ), patch.object(
            notification_outbox,
            "get_notification_outbox_settings",
            return_value=config,
        ):
            summary = notification_outbox.evaluate_notification_outbox_backpressure(
                event_type="journal_created",
                action_type="card",
            )

        self.assertTrue(summary["throttle"])
        self.assertEqual(summary["reason"], "depth_threshold")

    def test_evaluate_notification_outbox_backpressure_respects_action_exemption(self) -> None:
        config = type(
            "_Cfg",
            (),
            {
                "backlog_throttle_enabled": True,
                "backlog_throttle_depth_threshold": 2000,
                "backlog_throttle_oldest_pending_seconds_threshold": 1200,
                "backlog_throttle_exempt_event_types": (),
                "backlog_throttle_exempt_action_types": ("journal", "active_care"),
            },
        )()
        with patch.object(notification_outbox, "get_notification_outbox_depth", return_value=9999), patch.object(
            notification_outbox,
            "get_notification_outbox_oldest_pending_age_seconds",
            return_value=9999,
        ), patch.object(
            notification_outbox,
            "get_notification_outbox_settings",
            return_value=config,
        ):
            summary = notification_outbox.evaluate_notification_outbox_backpressure(
                event_type="journal_created",
                action_type="journal",
            )

        self.assertFalse(summary["throttle"])
        self.assertEqual(summary["reason"], "exempt")


if __name__ == "__main__":
    unittest.main()
