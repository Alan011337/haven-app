#!/usr/bin/env python3
"""Dry-run/apply retention cleanup for events_log."""

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
    parser = argparse.ArgumentParser(description="events_log retention cleanup")
    parser.add_argument("--retention-days", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument(
        "--max-apply-batch-size",
        type=int,
        default=5000,
        help="Safety cap for --apply mode; apply fails when batch-size exceeds this value.",
    )
    parser.add_argument(
        "--max-apply-matched",
        type=int,
        default=50000,
        help="Safety cap for --apply mode; apply fails when dry-run matched exceeds this value.",
    )
    parser.add_argument(
        "--expected-cutoff-unix",
        type=int,
        default=None,
        help="Optional cutoff guard. If provided and mismatched, --apply exits non-zero.",
    )
    parser.add_argument(
        "--confirm-apply",
        default="",
        help="Required for --apply; must equal 'events-log-retention-apply'.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletion. Default mode is dry-run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from app.services.events_log_retention import cleanup_events_log

    args = _build_parser().parse_args(argv)
    if not args.apply:
        summary = cleanup_events_log(
            retention_days=args.retention_days,
            batch_size=args.batch_size,
            apply=False,
        )
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
        return 0

    if args.confirm_apply != "events-log-retention-apply":
        print(
            json.dumps(
                {
                    "apply": True,
                    "accepted": False,
                    "failure_reason": "missing_confirm_apply_token",
                    "required_confirm_apply": "events-log-retention-apply",
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1

    dry_run_summary = cleanup_events_log(
        retention_days=args.retention_days,
        batch_size=args.batch_size,
        apply=False,
    )
    effective_batch_size = int(dry_run_summary.get("batch_size", 0) or 0)
    matched = int(dry_run_summary.get("matched", 0) or 0)
    cutoff_unix = int(dry_run_summary.get("cutoff_unix", 0) or 0)
    max_apply_batch_size = max(1, int(args.max_apply_batch_size))
    max_apply_matched = max(1, int(args.max_apply_matched))

    if effective_batch_size > max_apply_batch_size:
        print(
            json.dumps(
                {
                    "apply": True,
                    "accepted": False,
                    "failure_reason": "apply_batch_size_exceeds_cap",
                    "batch_size": effective_batch_size,
                    "max_apply_batch_size": max_apply_batch_size,
                    "preflight": dry_run_summary,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1

    if matched > max_apply_matched:
        print(
            json.dumps(
                {
                    "apply": True,
                    "accepted": False,
                    "failure_reason": "apply_matched_exceeds_cap",
                    "matched": matched,
                    "max_apply_matched": max_apply_matched,
                    "preflight": dry_run_summary,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1

    if args.expected_cutoff_unix is not None and int(args.expected_cutoff_unix) != cutoff_unix:
        print(
            json.dumps(
                {
                    "apply": True,
                    "accepted": False,
                    "failure_reason": "expected_cutoff_mismatch",
                    "expected_cutoff_unix": int(args.expected_cutoff_unix),
                    "actual_cutoff_unix": cutoff_unix,
                    "preflight": dry_run_summary,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 1

    summary = cleanup_events_log(
        retention_days=args.retention_days,
        batch_size=args.batch_size,
        apply=True,
    )
    output = {
        "apply": True,
        "accepted": True,
        "preflight": dry_run_summary,
        "result": summary,
    }
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
