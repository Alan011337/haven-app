from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, func, select

from app.core.datetime_utils import utcnow
from app.db.session import engine
from app.models.notification_outbox import NotificationOutbox, NotificationOutboxStatus
from app.services.notification_outbox import (
    _classify_outbox_error,  # noqa: PLC2701
    _processing_timeout_seconds,  # noqa: PLC2701
    get_notification_outbox_dispatch_lock_heartbeat_age_seconds,
)
from app.services.notification_outbox_support import (
    compute_dead_letter_rate_from_counts,
    compute_retry_age_p95_seconds,
    normalize_status_counts,
)

logger = logging.getLogger(__name__)

def get_notification_outbox_health_snapshot() -> dict[str, int | float | dict[str, int]]:
    """Fetch outbox probes in one DB session to reduce /health DB probe overhead."""
    snapshot: dict[str, int | float | dict[str, int]] = {
        "depth": -1,
        "oldest_pending_age_seconds": -1,
        "retry_age_p95_seconds": -1,
        "stale_processing_count": -1,
        "dead_letter_rate": -1.0,
        "status_counts": {},
        "dispatch_lock_heartbeat_age_seconds": get_notification_outbox_dispatch_lock_heartbeat_age_seconds(),
    }
    try:
        with Session(engine) as session:
            now_utc = utcnow()
            status_scope = col(NotificationOutbox.status).in_(
                [
                    NotificationOutboxStatus.PENDING,
                    NotificationOutboxStatus.RETRY,
                    NotificationOutboxStatus.PROCESSING,
                ]
            )
            snapshot["depth"] = int(
                session.exec(
                    select(func.count(NotificationOutbox.id)).where(
                        status_scope,
                        NotificationOutbox.available_at <= now_utc,
                    )
                ).one()
                or 0
            )

            oldest_created_at = session.exec(
                select(func.min(NotificationOutbox.created_at)).where(status_scope)
            ).one()
            if oldest_created_at is None:
                snapshot["oldest_pending_age_seconds"] = 0
            else:
                snapshot["oldest_pending_age_seconds"] = max(
                    0, int((now_utc - oldest_created_at).total_seconds())
                )

            status_rows = session.exec(
                select(NotificationOutbox.status, func.count(NotificationOutbox.id)).group_by(
                    NotificationOutbox.status
                )
            ).all()
            status_counts = normalize_status_counts(list(status_rows))
            snapshot["status_counts"] = status_counts
            snapshot["dead_letter_rate"] = compute_dead_letter_rate_from_counts(status_counts)

            retry_rows = session.exec(
                select(NotificationOutbox.created_at).where(
                    NotificationOutbox.status == NotificationOutboxStatus.RETRY
                )
            ).all()
            snapshot["retry_age_p95_seconds"] = compute_retry_age_p95_seconds(
                created_at_rows=list(retry_rows),
                now_utc=now_utc,
            )

            cutoff = now_utc - timedelta(seconds=_processing_timeout_seconds())
            snapshot["stale_processing_count"] = int(
                session.exec(
                    select(func.count(NotificationOutbox.id)).where(
                        NotificationOutbox.status == NotificationOutboxStatus.PROCESSING,
                        NotificationOutbox.updated_at < cutoff,
                    )
                ).one()
                or 0
            )
    except SQLAlchemyError as exc:
        logger.warning(
            "Notification outbox health snapshot probe failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
    return snapshot
