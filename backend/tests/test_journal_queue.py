# P2-B QUEUE-01: Tests for async journal analysis queue (enqueue, is_enabled, job runners).
import asyncio
import json
import uuid
from unittest.mock import patch

from app.queue.journal_tasks import (
    QUEUE_KEY_ANALYSIS_DLQ,
    enqueue_journal_analysis,
    enqueue_journal_notification,
    is_async_journal_analysis_enabled,
    _run_analysis_with_timeout,
    run_notification_job,
)


class TestJournalQueueEnabled:
    """When REDIS_URL and ASYNC_JOURNAL_ANALYSIS are not set, queue is disabled."""

    def test_is_async_journal_analysis_enabled_false_without_redis(self) -> None:
        with patch("app.queue.journal_tasks.settings") as s:
            s.REDIS_URL = None
            s.ASYNC_JOURNAL_ANALYSIS = True
            assert is_async_journal_analysis_enabled() is False

    def test_enqueue_journal_analysis_returns_false_without_client(self) -> None:
        with patch("app.queue.journal_tasks._get_queue_client", return_value=None):
            ok = enqueue_journal_analysis(
                journal_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )
            assert ok is False

    def test_enqueue_journal_notification_returns_false_without_client(self) -> None:
        with patch("app.queue.journal_tasks._get_queue_client", return_value=None):
            ok = enqueue_journal_notification(uuid.uuid4())
            assert ok is False


class TestRunNotificationJob:
    """run_notification_job handles invalid payload without raising."""

    def test_run_notification_job_invalid_json(self) -> None:
        run_notification_job("not-json")

    def test_run_notification_job_missing_journal_id(self) -> None:
        run_notification_job("{}")


class _FakeQueueClient:
    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def rpush(self, key: str, value: str) -> None:
        self.items.append((key, value))


class TestAnalysisDeadLetter:
    def test_run_analysis_timeout_pushes_dead_letter(self) -> None:
        async def _always_timeout(payload_str: str) -> None:  # noqa: ARG001
            await asyncio.sleep(0)
            raise asyncio.TimeoutError()

        fake_client = _FakeQueueClient()
        with patch("app.queue.journal_tasks.run_analysis_job", side_effect=_always_timeout):
            ok = asyncio.run(
                _run_analysis_with_timeout(client=fake_client, payload_str='{"journal_id":"x"}')
            )

        assert ok is False
        assert len(fake_client.items) == 1
        key, value = fake_client.items[0]
        assert key == QUEUE_KEY_ANALYSIS_DLQ
        payload = json.loads(value)
        assert payload["job_type"] == "analysis"
        assert payload["reason"] == "timeout"
