#!/usr/bin/env python3
"""Notification outbox recovery probe.

Dry-run by default: reports backlog/dead-letter state and whether auto replay would trigger.
Use --apply to execute the replay action.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe/recover notification outbox dead letters.")
    parser.add_argument("--apply", action="store_true", help="Execute replay action when thresholds match.")
    parser.add_argument("--replay-limit", type=int, default=None, help="Override replay limit.")
    parser.add_argument("--min-dead-rows", type=int, default=None, help="Override minimum dead rows.")
    parser.add_argument(
        "--min-dead-rate",
        type=float,
        default=None,
        help="Override minimum dead-letter rate to trigger replay.",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only.")
    return parser.parse_args()


def main() -> int:
    from app.services.notification_outbox import auto_replay_dead_notification_outbox

    args = _parse_args()
    summary = auto_replay_dead_notification_outbox(
        enabled=True,
        replay_limit=args.replay_limit,
        min_dead_rows=args.min_dead_rows,
        min_dead_letter_rate=args.min_dead_rate,
        reset_attempt_count=False,
    )
    if not args.apply:
        summary["triggered"] = 0
        summary["replayed"] = 0
        summary["mode"] = "dry_run"
    else:
        summary["mode"] = "apply"

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "[notification-outbox-recovery] mode={mode} dead_rows={dead_rows} dead_rate={rate:.4f} "
            "triggered={triggered} replayed={replayed} errors={errors}".format(
                mode=summary.get("mode", "dry_run"),
                dead_rows=int(summary.get("dead_rows", 0)),
                rate=float(summary.get("dead_letter_rate", 0.0)),
                triggered=int(summary.get("triggered", 0)),
                replayed=int(summary.get("replayed", 0)),
                errors=int(summary.get("errors", 0)),
            )
        )
    return 0 if int(summary.get("errors", 0)) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

