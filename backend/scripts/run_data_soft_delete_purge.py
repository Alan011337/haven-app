#!/usr/bin/env python3
"""Execute (or dry-run) purge for soft-deleted data beyond retention window."""

from __future__ import annotations

import argparse
import json

from sqlmodel import Session

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.db.session import engine
from app.services.data_soft_delete_purge import (
    SOFT_DELETE_PURGE_COUNT_KEYS,
    purge_soft_deleted_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purge soft-deleted data rows.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=settings.DATA_SOFT_DELETE_PURGE_RETENTION_DAYS,
        help=(
            "Soft-delete purge retention window in days "
            "(default: DATA_SOFT_DELETE_PURGE_RETENTION_DAYS)."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply physical deletion. Default is dry-run.",
    )
    parser.add_argument(
        "--allow-when-disabled",
        action="store_true",
        help=(
            "Allow --apply execution even when DATA_SOFT_DELETE_ENABLED=false. "
            "Useful for one-time cleanup."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    retention_days = max(1, int(args.retention_days))
    apply_mode = bool(args.apply)

    if apply_mode and not settings.DATA_SOFT_DELETE_ENABLED and not args.allow_when_disabled:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "reason": "soft_delete_disabled",
                    "detail": (
                        "Refusing --apply while DATA_SOFT_DELETE_ENABLED=false. "
                        "Use --allow-when-disabled for intentional cleanup."
                    ),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 1

    now = utcnow()
    with Session(engine) as session:
        result = purge_soft_deleted_rows(
            session=session,
            purge_retention_days=retention_days,
            dry_run=not apply_mode,
            now=now,
        )
        if apply_mode:
            session.commit()
        else:
            session.rollback()

    total_candidates = sum(result.candidate_counts.get(key, 0) for key in SOFT_DELETE_PURGE_COUNT_KEYS)
    total_purged = sum(result.purged_counts.get(key, 0) for key in SOFT_DELETE_PURGE_COUNT_KEYS)

    print(
        json.dumps(
            {
                "status": "ok",
                "mode": "apply" if apply_mode else "dry_run",
                "soft_delete_enabled": settings.DATA_SOFT_DELETE_ENABLED,
                "retention_days": retention_days,
                "cutoff_iso": result.cutoff.isoformat(),
                "candidate_counts": result.candidate_counts,
                "purged_counts": result.purged_counts,
                "total_candidates": total_candidates,
                "total_purged": total_purged,
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
