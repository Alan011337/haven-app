from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, col, delete, func, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.db.session import engine
from app.models.events_log import EventsLog
from app.models.events_log_daily_rollup import EventsLogDailyRollup


def _rollup_enabled() -> bool:
    return bool(getattr(settings, "EVENTS_LOG_ROLLUP_ENABLED", True))


def _retention_days(raw: int | None = None) -> int:
    value = int(raw if raw is not None else getattr(settings, "EVENTS_LOG_ROLLUP_RETENTION_DAYS", 30))
    return max(1, value)


def _batch_size(raw: int | None = None) -> int:
    value = int(raw if raw is not None else getattr(settings, "EVENTS_LOG_ROLLUP_BATCH_SIZE", 5000))
    return max(1, value)


def _resolve_user_scope(*, partner_user_id) -> str:
    return "paired" if partner_user_id else "solo"


def rollup_events_log_daily(
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

        selected_rows = list(
            session.exec(
                select(
                    EventsLog.id,
                    EventsLog.ts,
                    EventsLog.event_name,
                    EventsLog.source,
                    EventsLog.partner_user_id,
                )
                .where(EventsLog.ts < cutoff)
                .order_by(col(EventsLog.ts).asc(), col(EventsLog.id).asc())
                .limit(limit)
            ).all()
        )

        if not apply or not _rollup_enabled() or not selected_rows:
            return {
                "apply": bool(apply),
                "enabled": _rollup_enabled(),
                "retention_days": days,
                "batch_size": limit,
                "cutoff_unix": int(cutoff.timestamp()),
                "matched": matched,
                "selected": len(selected_rows),
                "rolled_up_rows": 0,
                "purged": 0,
            }

        grouped_counts: dict[tuple, int] = {}
        selected_ids: list = []
        for row in selected_rows:
            selected_ids.append(row.id)
            key = (
                row.ts.date(),
                str(row.event_name or "unknown"),
                str(row.source or "unknown"),
                _resolve_user_scope(partner_user_id=row.partner_user_id),
            )
            grouped_counts[key] = grouped_counts.get(key, 0) + 1

        for (rollup_date, event_name, source, user_scope), event_count in grouped_counts.items():
            existing = session.exec(
                select(EventsLogDailyRollup).where(
                    EventsLogDailyRollup.rollup_date == rollup_date,
                    EventsLogDailyRollup.event_name == event_name,
                    EventsLogDailyRollup.source == source,
                    EventsLogDailyRollup.user_scope == user_scope,
                )
            ).first()
            if existing is None:
                session.add(
                    EventsLogDailyRollup(
                        rollup_date=rollup_date,
                        event_name=event_name,
                        source=source,
                        user_scope=user_scope,
                        event_count=event_count,
                        created_at=utcnow(),
                        updated_at=utcnow(),
                    )
                )
                continue
            existing.event_count = int(existing.event_count) + int(event_count)
            existing.updated_at = utcnow()
            session.add(existing)

        delete_result = session.exec(
            delete(EventsLog).where(EventsLog.id.in_(selected_ids))
        )
        purged = int(getattr(delete_result, "rowcount", 0) or 0)
        session.commit()
        return {
            "apply": True,
            "enabled": True,
            "retention_days": days,
            "batch_size": limit,
            "cutoff_unix": int(cutoff.timestamp()),
            "matched": matched,
            "selected": len(selected_rows),
            "rolled_up_rows": len(grouped_counts),
            "purged": max(0, purged),
        }
