#!/usr/bin/env python3
"""Run audit-log retention cleanup and print deterministic evidence."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta

from sqlmodel import Session, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.db.session import engine
from app.models.audit_event import AuditEvent
from app.services.audit_log_retention import purge_expired_audit_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge expired audit events.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=settings.AUDIT_LOG_RETENTION_DAYS,
        help="Retention window for audit events (default: AUDIT_LOG_RETENTION_DAYS).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    retention_days = max(1, int(args.retention_days))
    now = utcnow()
    cutoff = now - timedelta(days=retention_days)

    with Session(engine) as session:
        before_count = len(session.exec(select(AuditEvent)).all())
        deleted_count = purge_expired_audit_events(
            session=session,
            retention_days=retention_days,
            now=now,
        )
        session.commit()
        after_count = len(session.exec(select(AuditEvent)).all())

    print(
        json.dumps(
            {
                "status": "ok",
                "retention_days": retention_days,
                "cutoff_iso": cutoff.isoformat(),
                "before_count": before_count,
                "deleted_count": deleted_count,
                "after_count": after_count,
                "executed_at": now.isoformat(),
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

