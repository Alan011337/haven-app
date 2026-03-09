import asyncio
import contextlib
import os
import sys
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import notification  # noqa: E402


class _FakeEmails:
    def __init__(self) -> None:
        self.calls = []

    def send(self, payload):
        self.calls.append(payload)


class NotificationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        notification.reset_notification_dedupe_state_for_test()
        # Legacy queue behavior tests assert in-process async dispatch semantics.
        # Keep durable outbox disabled in this suite to avoid DB dependency coupling.
        self._outbox_enabled_patcher = patch.object(
            notification, "_is_notification_outbox_enabled", return_value=False
        )
        self._outbox_enabled_patcher.start()
        self.addCleanup(self._outbox_enabled_patcher.stop)

    async def test_send_returns_false_when_resend_not_available(self) -> None:
        with patch.object(notification, "resend", None):
            ok = await notification.send_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
            )
        self.assertFalse(ok)

    async def test_send_builds_expected_payload(self) -> None:
        fake_emails = _FakeEmails()
        fake_resend = SimpleNamespace(api_key="test-key", Emails=fake_emails)

        with patch.object(notification, "resend", fake_resend), patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "test-key",
                "RESEND_FROM_EMAIL": "Haven <notify@example.com>",
            },
            clear=False,
        ):
            ok = await notification.send_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="card",
            )

        self.assertTrue(ok)
        self.assertEqual(len(fake_emails.calls), 1)
        payload = fake_emails.calls[0]
        self.assertEqual(payload["to"], "partner@example.com")
        self.assertEqual(payload["from"], "Haven <notify@example.com>")
        self.assertIn("Alex", payload["subject"])

    async def test_send_failure_log_masks_exception_details(self) -> None:
        class _FailingEmails:
            def send(self, payload):  # noqa: ARG002
                raise RuntimeError("smtp://user:super-secret@mail.internal/send failed")

        fake_resend = SimpleNamespace(api_key="test-key", Emails=_FailingEmails())

        with patch.object(notification, "resend", fake_resend), patch.dict(
            os.environ,
            {
                "RESEND_API_KEY": "test-key",
            },
            clear=False,
        ):
            with self.assertLogs(notification.logger, level="ERROR") as captured:
                ok = await notification.send_partner_notification(
                    receiver_email="partner@example.com",
                    sender_name="Alex",
                    action_type="card",
                )

        self.assertFalse(ok)
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("smtp://", merged)

    async def test_record_notification_event_log_masks_exception_details(self) -> None:
        with patch(
            "sqlmodel.Session",
            side_effect=RuntimeError("postgresql://svc:super-secret@db.internal:5432/app"),
        ):
            with self.assertLogs(notification.logger, level="DEBUG") as captured:
                notification._record_notification_event(
                    receiver_email="partner@example.com",
                    action_type="journal",
                    status="FAILED",
                    dedupe_key="test:redaction",
                    error_message="forced_failure",
                )

        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)

    async def test_send_with_retry_stops_after_success(self) -> None:
        with patch.object(
            notification,
            "send_partner_notification",
            AsyncMock(side_effect=[False, True]),
        ) as mocked_send:
            ok = await notification.send_partner_notification_with_retry(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                max_retries=2,
                base_delay_seconds=0,
            )

        self.assertTrue(ok)
        self.assertEqual(mocked_send.await_count, 2)

    async def test_reserve_notification_slot_dedupes_until_release(self) -> None:
        key = "test:dedupe"
        self.assertTrue(notification._reserve_notification_slot(key))
        self.assertFalse(notification._reserve_notification_slot(key))
        notification._release_notification_slot(key)
        self.assertTrue(notification._reserve_notification_slot(key))

    async def test_build_notification_dedupe_key_with_scope(self) -> None:
        sender = uuid.uuid4()
        receiver = uuid.uuid4()
        scope = uuid.uuid4()
        key = notification.build_notification_dedupe_key(
            event_type="card_revealed",
            scope_id=scope,
            sender_user_id=sender,
            receiver_user_id=receiver,
        )
        self.assertEqual(key, f"card_revealed:{scope}:{sender}:{receiver}")

    async def test_build_notification_dedupe_key_without_scope(self) -> None:
        sender = uuid.uuid4()
        receiver = uuid.uuid4()
        key = notification.build_notification_dedupe_key(
            event_type="journal",
            sender_user_id=sender,
            receiver_user_id=receiver,
        )
        self.assertEqual(key, f"journal:{sender}:{receiver}")

    async def test_queue_releases_slot_on_failed_delivery(self) -> None:
        key = "test:release-on-failure"
        with patch.object(
            notification,
            "send_partner_notification_with_retry",
            AsyncMock(return_value=False),
        ), patch.object(notification, "_record_notification_event"), patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ):
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                dedupe_key=key,
            )
            await asyncio.sleep(0.01)

        self.assertTrue(notification._reserve_notification_slot(key))

    async def test_queue_can_bypass_dedupe_cooldown_for_manual_retry(self) -> None:
        key = "test:bypass-dedupe"
        self.assertTrue(notification._reserve_notification_slot(key))
        with patch.object(
            notification,
            "send_partner_notification_with_retry",
            AsyncMock(return_value=True),
        ) as mock_send, patch.object(notification, "_record_notification_event") as mock_record, patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ):
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="card",
                dedupe_key=key,
                bypass_dedupe_cooldown=True,
            )
            await asyncio.sleep(0.01)

        statuses = [call.kwargs.get("status") for call in mock_record.call_args_list]
        self.assertIn("QUEUED", statuses)
        self.assertIn("SENT", statuses)
        self.assertNotIn("THROTTLED", statuses)
        mock_send.assert_awaited_once()

    async def test_queue_fails_fast_when_provider_unavailable(self) -> None:
        key = "test:provider-unavailable"
        with patch.object(notification, "resend", None), patch.object(
            notification, "_record_notification_event"
        ) as mock_record, patch.object(notification.asyncio, "create_task") as mock_create_task:
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                dedupe_key=key,
            )

        mock_create_task.assert_not_called()
        self.assertTrue(notification._reserve_notification_slot(key))
        statuses = [call.kwargs.get("status") for call in mock_record.call_args_list]
        self.assertIn("FAILED", statuses)
        self.assertIn("provider_unavailable", [call.kwargs.get("error_message") for call in mock_record.call_args_list])

    async def test_queue_records_queued_and_sent_status(self) -> None:
        key = "test:queued-then-sent"
        with patch.object(
            notification,
            "send_partner_notification_with_retry",
            AsyncMock(return_value=True),
        ), patch.object(notification, "_record_notification_event") as mock_record, patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ):
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                dedupe_key=key,
            )
            await asyncio.sleep(0.01)

        statuses = [call.kwargs.get("status") for call in mock_record.call_args_list]
        self.assertIn("QUEUED", statuses)
        self.assertIn("SENT", statuses)

    async def test_receiver_opt_out_uses_runtime_cache(self) -> None:
        receiver_user_id = uuid.uuid4()

        class _FakeSession:
            def __init__(self) -> None:
                self.calls = 0

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def get(self, model, user_id):  # noqa: ARG002
                self.calls += 1
                return SimpleNamespace(notification_frequency="off")

        fake_session = _FakeSession()
        with patch.object(notification.settings, "NOTIFICATION_CONSENT_CACHE_SECONDS", 60), patch(
            "sqlmodel.Session",
            return_value=fake_session,
        ):
            first = notification._is_receiver_email_opted_out(receiver_user_id)
            second = notification._is_receiver_email_opted_out(receiver_user_id)

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(fake_session.calls, 1)
        notification.invalidate_notification_preference_cache(receiver_user_id)

    async def test_queue_outbox_backpressure_skips_enqueue_and_releases_dedupe_slot(self) -> None:
        key = "test:outbox-backpressure"
        with patch.object(notification, "_is_notification_outbox_enabled", return_value=True), patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ), patch(
            "app.services.notification_outbox.evaluate_notification_outbox_backpressure",
            return_value={
                "enabled": True,
                "throttle": True,
                "reason": "depth_threshold",
                "depth": 2500,
                "oldest_pending_age_seconds": 200,
            },
        ), patch(
            "app.services.notification_outbox.enqueue_notification_outbox"
        ) as mock_enqueue, patch.object(
            notification, "_record_notification_event"
        ) as mock_record:
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="card",
                dedupe_key=key,
            )

        mock_enqueue.assert_not_called()
        self.assertTrue(notification._reserve_notification_slot(key))
        statuses = [call.kwargs.get("status") for call in mock_record.call_args_list]
        self.assertIn("THROTTLED", statuses)
        error_messages = [call.kwargs.get("error_message") for call in mock_record.call_args_list]
        self.assertIn("outbox_backpressure", error_messages)

    async def test_queue_records_queued_and_failed_status(self) -> None:
        key = "test:queued-then-failed"
        with patch.object(
            notification,
            "send_partner_notification_with_retry",
            AsyncMock(return_value=False),
        ), patch.object(notification, "_record_notification_event") as mock_record, patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ):
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                dedupe_key=key,
            )
            await asyncio.sleep(0.01)

        statuses = [call.kwargs.get("status") for call in mock_record.call_args_list]
        self.assertIn("QUEUED", statuses)
        self.assertIn("FAILED", statuses)

    async def test_queue_runner_error_log_masks_exception_details(self) -> None:
        key = "test:runner-exception-log-redaction"
        with patch.object(
            notification,
            "send_partner_notification_with_retry",
            AsyncMock(
                side_effect=RuntimeError(
                    "postgresql://svc:super-secret@db.internal:5432/haven unavailable"
                )
            ),
        ), patch.object(notification, "is_email_notification_enabled", return_value=True):
            with self.assertLogs(notification.logger, level="ERROR") as captured:
                notification.queue_partner_notification(
                    receiver_email="partner@example.com",
                    sender_name="Alex",
                    action_type="journal",
                    dedupe_key=key,
                )
                await asyncio.sleep(0.01)

        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)

    async def test_queue_releases_slot_when_task_cancelled(self) -> None:
        key = "test:release-on-cancel"
        blocker = asyncio.Event()
        captured_task: dict[str, asyncio.Task[None]] = {}
        real_create_task = asyncio.create_task

        async def _never_finish(*args, **kwargs):
            await blocker.wait()
            return True

        def _capture_create_task(coro, *args, **kwargs):
            task = real_create_task(coro, *args, **kwargs)
            captured_task["task"] = task
            return task

        with patch.object(
            notification,
            "send_partner_notification_with_retry",
            AsyncMock(side_effect=_never_finish),
        ), patch.object(notification.asyncio, "create_task", side_effect=_capture_create_task), patch.object(
            notification, "_record_notification_event"
        ), patch.object(
            notification, "is_email_notification_enabled", return_value=True
        ):
            notification.queue_partner_notification(
                receiver_email="partner@example.com",
                sender_name="Alex",
                action_type="journal",
                dedupe_key=key,
            )
            await asyncio.sleep(0)
            task = captured_task["task"]
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await asyncio.sleep(0.01)

        self.assertTrue(notification._reserve_notification_slot(key))

    async def test_record_event_upsert_by_dedupe_updates_single_row(self) -> None:
        from app.db import session as db_session_module
        from app.models.notification_event import NotificationDeliveryStatus, NotificationEvent
        from app.models.user import User  # noqa: F401

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)

        with patch.object(db_session_module, "engine", engine):
            notification._record_notification_event(
                receiver_email="partner@example.com",
                action_type="journal",
                status="QUEUED",
                dedupe_key="card:session-1:user-a:user-b",
                upsert_by_dedupe=True,
            )
            notification._record_notification_event(
                receiver_email="partner@example.com",
                action_type="journal",
                status="SENT",
                dedupe_key="card:session-1:user-a:user-b",
                upsert_by_dedupe=True,
            )

        with Session(engine) as session:
            rows = session.exec(select(NotificationEvent)).all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, NotificationDeliveryStatus.SENT)
        self.assertEqual(rows[0].receiver_email, "partner@example.com")

    async def test_record_event_upsert_recovers_from_commit_integrity_error(self) -> None:
        from app.db import session as db_session_module
        from app.models.notification_event import NotificationDeliveryStatus, NotificationEvent
        from app.models.user import User  # noqa: F401
        from sqlmodel import Session as SQLModelSession

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)

        with patch.object(db_session_module, "engine", engine):
            notification._record_notification_event(
                receiver_email="partner@example.com",
                action_type="card",
                status="QUEUED",
                dedupe_key="card:session-2:user-a:user-b",
                upsert_by_dedupe=True,
            )

            original_commit = SQLModelSession.commit
            raise_once = {"done": False}

            def flaky_commit(session: SQLModelSession) -> None:
                if not raise_once["done"]:
                    raise_once["done"] = True
                    raise IntegrityError("forced_conflict", params=None, orig=Exception("duplicate"))
                original_commit(session)

            with patch.object(SQLModelSession, "commit", new=flaky_commit):
                notification._record_notification_event(
                    receiver_email="partner@example.com",
                    action_type="card",
                    status="SENT",
                    dedupe_key="card:session-2:user-a:user-b",
                    upsert_by_dedupe=True,
                )

        with Session(engine) as session:
            rows = session.exec(select(NotificationEvent)).all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, NotificationDeliveryStatus.SENT)
        self.assertEqual(rows[0].receiver_email, "partner@example.com")


if __name__ == "__main__":
    unittest.main()
