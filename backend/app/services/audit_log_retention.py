from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete as sqlalchemy_delete
from sqlmodel import Session

from app.core.datetime_utils import utcnow
from app.models.audit_event import AuditEvent


def purge_expired_audit_events(
    *,
    session: Session,
    retention_days: int,
    now: datetime | None = None,
) -> int:
    effective_retention_days = max(1, int(retention_days))
    cutoff = (now or utcnow()) - timedelta(days=effective_retention_days)

    result = session.exec(
        sqlalchemy_delete(AuditEvent).where(AuditEvent.created_at < cutoff)
    )
    return int(result.rowcount or 0)

