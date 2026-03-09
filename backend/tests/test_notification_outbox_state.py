from datetime import timedelta

from app.core.datetime_utils import utcnow
from app.models.notification_outbox import NotificationOutbox, NotificationOutboxStatus
from app.services.notification_outbox_state import resolve_dispatch_transition


def _build_row(*, attempt_count: int, max_attempts: int) -> NotificationOutbox:
    return NotificationOutbox(
        receiver_email="a@example.com",
        sender_name="haven",
        action_type="journal",
        attempt_count=attempt_count,
        max_attempts=max_attempts,
    )


def test_resolve_dispatch_transition_sent() -> None:
    row = _build_row(attempt_count=1, max_attempts=3)
    now = utcnow()
    transition = resolve_dispatch_transition(
        row=row,
        delivered=True,
        failure_reason=None,
        now_utc=now,
        backoff_seconds=10,
    )
    assert transition.status == NotificationOutboxStatus.SENT
    assert transition.last_error_reason is None
    assert transition.available_at is None
    assert transition.release_dedupe_slot is False
    assert transition.summary_bucket == "sent"


def test_resolve_dispatch_transition_dead_letter() -> None:
    row = _build_row(attempt_count=3, max_attempts=3)
    now = utcnow()
    transition = resolve_dispatch_transition(
        row=row,
        delivered=False,
        failure_reason="transport_error",
        now_utc=now,
        backoff_seconds=10,
    )
    assert transition.status == NotificationOutboxStatus.DEAD
    assert transition.last_error_reason == "transport_error"
    assert transition.available_at is None
    assert transition.release_dedupe_slot is True
    assert transition.summary_bucket == "dead"


def test_resolve_dispatch_transition_retry() -> None:
    row = _build_row(attempt_count=1, max_attempts=3)
    now = utcnow()
    transition = resolve_dispatch_transition(
        row=row,
        delivered=False,
        failure_reason="transport_error",
        now_utc=now,
        backoff_seconds=30,
    )
    assert transition.status == NotificationOutboxStatus.RETRY
    assert transition.last_error_reason == "transport_error"
    assert transition.available_at is not None
    assert transition.available_at >= now + timedelta(seconds=30)
    assert transition.release_dedupe_slot is False
    assert transition.summary_bucket == "retried"

