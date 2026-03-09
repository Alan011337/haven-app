#!/usr/bin/env python3
"""Generate dead-letter replay audit summary for notification outbox."""

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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit notification outbox dead-letter replay actions.")
    parser.add_argument("--apply", action="store_true", help="Apply replay action. Default is dry-run.")
    parser.add_argument("--replay-limit", type=int, default=100, help="Maximum dead-letter rows to replay.")
    parser.add_argument(
        "--reset-attempt-count",
        action="store_true",
        help="Reset attempt_count for replayed rows.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    return parser.parse_args()


def _snapshot() -> dict[str, int | float]:
    from app.services.notification_outbox import (
        get_notification_outbox_dead_letter_rate,
        get_notification_outbox_status_counts,
    )

    counts = get_notification_outbox_status_counts()
    return {
        "pending": int(counts.get("pending", 0)),
        "retry": int(counts.get("retry", 0)),
        "processing": int(counts.get("processing", 0)),
        "sent": int(counts.get("sent", 0)),
        "dead": int(counts.get("dead", 0)),
        "dead_letter_rate": float(get_notification_outbox_dead_letter_rate()),
    }


def main(argv: list[str] | None = None) -> int:
    from app.services.notification_outbox import replay_dead_notification_outbox

    args = _parse_args() if argv is None else _parse_args_from(argv)
    before = _snapshot()
    replay_summary = {"selected": 0, "replayed": 0, "errors": 0}
    mode = "dry_run"
    if args.apply:
        mode = "apply"
        replay_summary = replay_dead_notification_outbox(
            limit=max(1, int(args.replay_limit)),
            reset_attempt_count=bool(args.reset_attempt_count),
        )
    after = _snapshot()
    payload = {
        "artifact_kind": "notification-outbox-dead-replay-audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "backend/scripts/run_notification_outbox_dead_replay_audit.py",
        "mode": mode,
        "replay_limit": int(args.replay_limit),
        "reset_attempt_count": bool(args.reset_attempt_count),
        "before": before,
        "replay": {
            "selected": int(replay_summary.get("selected", 0)),
            "replayed": int(replay_summary.get("replayed", 0)),
            "errors": int(replay_summary.get("errors", 0)),
        },
        "after": after,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[notification-outbox-dead-replay-audit] wrote summary: {args.output}")

    print("[notification-outbox-dead-replay-audit] result")
    print(f"  mode: {mode}")
    print(f"  dead_before: {before['dead']}")
    print(f"  dead_after: {after['dead']}")
    print(f"  replayed: {payload['replay']['replayed']}")
    print(f"  errors: {payload['replay']['errors']}")
    return 0 if payload["replay"]["errors"] == 0 else 1


def _parse_args_from(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit notification outbox dead-letter replay actions.")
    parser.add_argument("--apply", action="store_true", help="Apply replay action. Default is dry-run.")
    parser.add_argument("--replay-limit", type=int, default=100, help="Maximum dead-letter rows to replay.")
    parser.add_argument(
        "--reset-attempt-count",
        action="store_true",
        help="Reset attempt_count for replayed rows.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
