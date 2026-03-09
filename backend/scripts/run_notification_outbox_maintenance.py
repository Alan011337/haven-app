#!/usr/bin/env python3
"""Run outbox maintenance routines (cleanup + stale reclaim + auto replay)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only read metrics; no writes.")
    parser.add_argument("--output", default="", help="Optional JSON summary output path.")
    parser.add_argument("--replay-limit", type=int, default=None)
    parser.add_argument("--sent-retention-days", type=int, default=None)
    parser.add_argument("--dead-retention-days", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    from app.core.config import settings
    from app.core.datetime_utils import utcnow
    from app.db.session import engine
    from app.services.notification_outbox import (
        auto_replay_dead_notification_outbox,
        cleanup_notification_outbox,
        get_notification_outbox_dead_letter_rate,
        get_notification_outbox_depth,
        get_notification_outbox_oldest_pending_age_seconds,
        get_notification_outbox_stale_processing_count,
        reclaim_stale_processing_rows,
    )
    from sqlmodel import Session

    args = _parse_args()
    now = datetime.now(timezone.utc).isoformat()
    before_snapshot = {
        "depth": int(get_notification_outbox_depth()),
        "oldest_pending_age_seconds": int(get_notification_outbox_oldest_pending_age_seconds()),
        "stale_processing_count": int(get_notification_outbox_stale_processing_count()),
        "dead_letter_rate": float(get_notification_outbox_dead_letter_rate()),
    }

    summary: dict[str, object] = {
        "timestamp": now,
        "dry_run": bool(args.dry_run),
        "before": before_snapshot,
        "actions": {
            "reclaimed": 0,
            "cleanup": {"purged_sent": 0, "purged_dead": 0, "errors": 0},
            "auto_replay": {
                "enabled": 0,
                "triggered": 0,
                "dead_rows": 0,
                "dead_letter_rate": 0.0,
                "replayed": 0,
                "errors": 0,
            },
        },
    }

    if not args.dry_run:
        with Session(engine) as session:
            summary["actions"]["reclaimed"] = int(
                reclaim_stale_processing_rows(session=session, now_utc=utcnow())
            )
        summary["actions"]["cleanup"] = cleanup_notification_outbox(
            sent_retention_days=args.sent_retention_days,
            dead_retention_days=args.dead_retention_days,
        )
        summary["actions"]["auto_replay"] = auto_replay_dead_notification_outbox(
            replay_limit=args.replay_limit,
        )

    summary["after"] = {
        "depth": int(get_notification_outbox_depth()),
        "oldest_pending_age_seconds": int(get_notification_outbox_oldest_pending_age_seconds()),
        "stale_processing_count": int(get_notification_outbox_stale_processing_count()),
        "dead_letter_rate": float(get_notification_outbox_dead_letter_rate()),
    }
    summary["config"] = {
        "outbox_enabled": bool(getattr(settings, "NOTIFICATION_OUTBOX_ENABLED", False)),
        "auto_replay_enabled": bool(getattr(settings, "NOTIFICATION_OUTBOX_AUTO_REPLAY_ENABLED", True)),
    }

    output_text = _canonical_json(summary)
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"[outbox-maintenance] wrote summary: {args.output}")
    else:
        print(output_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
