#!/usr/bin/env python3
"""Orchestrate events_log lifecycle governance (rollup -> retention)."""

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
    parser = argparse.ArgumentParser(description="events_log lifecycle governance")
    parser.add_argument("--rollup-retention-days", type=int, default=None)
    parser.add_argument("--rollup-batch-size", type=int, default=None)
    parser.add_argument("--retention-days", type=int, default=None)
    parser.add_argument("--retention-batch-size", type=int, default=None)
    parser.add_argument(
        "--max-apply-rollup-selected",
        type=int,
        default=100000,
        help="Safety cap for --apply mode; abort when preflight rollup selected exceeds this value.",
    )
    parser.add_argument(
        "--max-apply-retention-matched",
        type=int,
        default=50000,
        help="Safety cap for --apply mode; abort when preflight retention matched exceeds this value.",
    )
    parser.add_argument(
        "--confirm-apply",
        default="",
        help="Required for --apply; must equal 'events-log-lifecycle-apply'.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply lifecycle operations.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    return parser


def _print_or_write(payload: dict, *, output: str) -> None:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    print(text)


def _build_preflight_payload(*, args: argparse.Namespace) -> dict:
    from app.services.events_log_retention import cleanup_events_log
    from app.services.events_log_rollup import rollup_events_log_daily

    rollup = rollup_events_log_daily(
        retention_days=args.rollup_retention_days,
        batch_size=args.rollup_batch_size,
        apply=False,
    )
    retention = cleanup_events_log(
        retention_days=args.retention_days,
        batch_size=args.retention_batch_size,
        apply=False,
    )
    return {
        "apply": False,
        "governance_stage": "preflight",
        "ordering": "rollup_then_retention",
        "rollup_preflight": rollup,
        "retention_preflight": retention,
    }


def main(argv: list[str] | None = None) -> int:
    from app.services.events_log_retention import cleanup_events_log
    from app.services.events_log_rollup import rollup_events_log_daily

    args = _build_parser().parse_args(argv)
    preflight = _build_preflight_payload(args=args)
    if not args.apply:
        _print_or_write(preflight, output=args.output)
        return 0

    if args.confirm_apply != "events-log-lifecycle-apply":
        _print_or_write(
            {
                "apply": True,
                "accepted": False,
                "failure_reason": "missing_confirm_apply_token",
                "required_confirm_apply": "events-log-lifecycle-apply",
                "preflight": preflight,
            },
            output=args.output,
        )
        return 1

    rollup_selected = int(preflight["rollup_preflight"].get("selected", 0) or 0)
    retention_matched = int(preflight["retention_preflight"].get("matched", 0) or 0)
    max_rollup_selected = max(1, int(args.max_apply_rollup_selected))
    max_retention_matched = max(1, int(args.max_apply_retention_matched))

    if rollup_selected > max_rollup_selected:
        _print_or_write(
            {
                "apply": True,
                "accepted": False,
                "failure_reason": "apply_rollup_selected_exceeds_cap",
                "rollup_selected": rollup_selected,
                "max_apply_rollup_selected": max_rollup_selected,
                "preflight": preflight,
            },
            output=args.output,
        )
        return 1

    if retention_matched > max_retention_matched:
        _print_or_write(
            {
                "apply": True,
                "accepted": False,
                "failure_reason": "apply_retention_matched_exceeds_cap",
                "retention_matched": retention_matched,
                "max_apply_retention_matched": max_retention_matched,
                "preflight": preflight,
            },
            output=args.output,
        )
        return 1

    rollup_result = rollup_events_log_daily(
        retention_days=args.rollup_retention_days,
        batch_size=args.rollup_batch_size,
        apply=True,
    )
    retention_result = cleanup_events_log(
        retention_days=args.retention_days,
        batch_size=args.retention_batch_size,
        apply=True,
    )

    _print_or_write(
        {
            "apply": True,
            "accepted": True,
            "governance_stage": "applied",
            "ordering": "rollup_then_retention",
            "preflight": preflight,
            "result": {
                "rollup": rollup_result,
                "retention": retention_result,
            },
        },
        output=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
