#!/usr/bin/env python3
"""Dry-run/apply daily rollup for events_log historical rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="events_log daily rollup")
    parser.add_argument("--retention-days", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument(
        "--confirm-apply",
        default="",
        help="Required for --apply; must equal 'events-log-rollup-apply'.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply rollup. Default mode is dry-run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from app.services.events_log_rollup import rollup_events_log_daily

    args = _build_parser().parse_args(argv)
    if not args.apply:
        summary = rollup_events_log_daily(
            retention_days=args.retention_days,
            batch_size=args.batch_size,
            apply=False,
        )
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0

    if args.confirm_apply != "events-log-rollup-apply":
        print(
            json.dumps(
                {
                    "apply": True,
                    "accepted": False,
                    "failure_reason": "missing_confirm_apply_token",
                    "required_confirm_apply": "events-log-rollup-apply",
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1

    summary = rollup_events_log_daily(
        retention_days=args.retention_days,
        batch_size=args.batch_size,
        apply=True,
    )
    output = {
        "apply": True,
        "accepted": True,
        "result": summary,
    }
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
