"""State transition helpers for notification outbox dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.notification_outbox import NotificationOutbox, NotificationOutboxStatus


@dataclass(frozen=True)
class NotificationOutboxTransition:
    status: NotificationOutboxStatus
    last_error_reason: str | None
    available_at: datetime | None
    release_dedupe_slot: bool
    summary_bucket: str
    metric_key: str


def resolve_dispatch_transition(
    *,
    row: NotificationOutbox,
    delivered: bool,
    failure_reason: str | None,
    now_utc: datetime,
    backoff_seconds: int,
) -> NotificationOutboxTransition:
    if delivered:
        return NotificationOutboxTransition(
            status=NotificationOutboxStatus.SENT,
            last_error_reason=None,
            available_at=None,
            release_dedupe_slot=False,
            summary_bucket="sent",
            metric_key="notification_outbox_sent_total",
        )

    reason = failure_reason or "retry_exhausted"
    if int(row.attempt_count) >= max(1, int(row.max_attempts)):
        return NotificationOutboxTransition(
            status=NotificationOutboxStatus.DEAD,
            last_error_reason=reason,
            available_at=None,
            release_dedupe_slot=True,
            summary_bucket="dead",
            metric_key="notification_outbox_dead_total",
        )

    return NotificationOutboxTransition(
        status=NotificationOutboxStatus.RETRY,
        last_error_reason=reason,
        available_at=now_utc + timedelta(seconds=max(0, int(backoff_seconds))),
        release_dedupe_slot=False,
        summary_bucket="retried",
        metric_key="notification_outbox_retry_total",
    )

