#!/usr/bin/env python3
"""Cleanup stale push subscriptions (invalid -> tombstoned -> purged)."""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.datetime_utils import utcnow  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models.push_subscription import PushSubscription, PushSubscriptionState  # noqa: E402


def _hash_endpoint(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def cleanup_push_subscriptions(
    session: Session,
    *,
    now: datetime,
    dry_run: bool,
    invalid_retention_days: int,
    tombstone_purge_days: int,
) -> dict[str, Any]:
    invalid_cutoff = now - timedelta(days=max(1, invalid_retention_days))
    tombstone_cutoff = now - timedelta(days=max(1, tombstone_purge_days))

    invalid_rows = session.exec(
        select(PushSubscription).where(
            PushSubscription.state == PushSubscriptionState.INVALID,
            PushSubscription.updated_at < invalid_cutoff,
        )
    ).all()
    tombstoned_rows = session.exec(
        select(PushSubscription).where(
            PushSubscription.state == PushSubscriptionState.TOMBSTONED,
            PushSubscription.updated_at < tombstone_cutoff,
        )
    ).all()

    if not dry_run:
        for row in invalid_rows:
            row.state = PushSubscriptionState.TOMBSTONED
            row.deleted_at = row.deleted_at or now
            row.updated_at = now
            row.fail_reason = row.fail_reason or "cleanup_invalid_retention"
            session.add(row)

        for row in tombstoned_rows:
            purged_endpoint = f"purged:{row.id}"
            row.state = PushSubscriptionState.PURGED
            row.deleted_at = row.deleted_at or now
            row.updated_at = now
            row.endpoint = purged_endpoint
            row.endpoint_hash = _hash_endpoint(purged_endpoint)
            row.p256dh_key = "[purged]"
            row.auth_key = "[purged]"
            row.user_agent = None
            row.expiration_time = None
            row.fail_reason = "purged"
            session.add(row)

        session.commit()

    return {
        "dry_run": dry_run,
        "checked_at": now.isoformat(),
        "invalid_retention_days": invalid_retention_days,
        "tombstone_purge_days": tombstone_purge_days,
        "invalid_to_tombstone_count": len(invalid_rows),
        "tombstone_to_purge_count": len(tombstoned_rows),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply updates. By default this script runs in dry-run mode.",
    )
    parser.add_argument(
        "--invalid-retention-days",
        type=int,
        default=settings.PUSH_INVALID_RETENTION_DAYS,
    )
    parser.add_argument(
        "--tombstone-purge-days",
        type=int,
        default=settings.PUSH_TOMBSTONE_PURGE_DAYS,
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    with Session(engine) as session:
        result = cleanup_push_subscriptions(
            session,
            now=utcnow(),
            dry_run=not args.execute,
            invalid_retention_days=args.invalid_retention_days,
            tombstone_purge_days=args.tombstone_purge_days,
        )
    print("[push-subscription-cleanup]")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print("result: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

