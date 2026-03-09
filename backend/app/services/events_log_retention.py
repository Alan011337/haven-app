from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, col, delete, func, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.db.session import engine
from app.models.events_log import EventsLog


def _retention_days(raw: int | None = None) -> int:
    value = int(raw if raw is not None else getattr(settings, "EVENTS_LOG_RETENTION_DAYS", 120))
    return max(1, value)


def _batch_size(raw: int | None = None) -> int:
    value = int(raw if raw is not None else getattr(settings, "EVENTS_LOG_PURGE_BATCH_SIZE", 2000))
    return max(1, value)


def cleanup_events_log(
    *,
    retention_days: int | None = None,
    batch_size: int | None = None,
    apply: bool = False,
) -> dict[str, int | str | bool]:
    days = _retention_days(retention_days)
    limit = _batch_size(batch_size)
    cutoff = utcnow() - timedelta(days=days)

    with Session(engine) as session:
        matched = int(
            session.exec(
                select(func.count(EventsLog.id)).where(
                    EventsLog.ts < cutoff,
                )
            ).one()
            or 0
        )

        if not apply or matched == 0:
            return {
                "apply": bool(apply),
                "retention_days": days,
                "batch_size": limit,
                "cutoff_unix": int(cutoff.timestamp()),
                "matched": matched,
                "purged": 0,
            }

        target_ids = list(
            session.exec(
                select(EventsLog.id)
                .where(EventsLog.ts < cutoff)
                .order_by(col(EventsLog.ts).asc(), col(EventsLog.id).asc())
                .limit(limit)
            ).all()
        )
        if not target_ids:
            return {
                "apply": True,
                "retention_days": days,
                "batch_size": limit,
                "cutoff_unix": int(cutoff.timestamp()),
                "matched": matched,
                "purged": 0,
            }

        result = session.exec(
            delete(EventsLog).where(
                EventsLog.id.in_(target_ids),
            )
        )
        purged = int(getattr(result, "rowcount", 0) or 0)
        session.commit()
        return {
            "apply": True,
            "retention_days": days,
            "batch_size": limit,
            "cutoff_unix": int(cutoff.timestamp()),
            "matched": matched,
            "purged": max(0, purged),
        }
