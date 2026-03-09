#!/usr/bin/env python3
"""Validate timeline performance budget from perf baseline snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="/tmp/backend-perf-baseline.json")
    parser.add_argument("--timeline-p95-budget-ms", type=float, default=300.0)
    parser.add_argument("--summary-path", default="")
    parser.add_argument("--allow-missing-snapshot", action="store_true")
    parser.add_argument("--fail-on-degraded", action="store_true")
    return parser


def _write(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    snapshot_path = Path(args.snapshot).resolve()
    if not snapshot_path.exists():
        payload = {
            "result": "skipped" if args.allow_missing_snapshot else "fail",
            "reasons": ["snapshot_missing"],
            "meta": {"snapshot": str(snapshot_path)},
        }
        _write(args.summary_path, payload)
        print(f"[timeline-perf-gate] result={payload['result']} reasons=snapshot_missing")
        return 0 if args.allow_missing_snapshot else 1

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    timeline = ((payload.get("results") or {}).get("timeline_query") or {})
    timeline_p95 = timeline.get("p95_ms")
    reasons: list[str] = []
    result = "pass"
    if not isinstance(timeline_p95, (int, float)):
        result = "fail"
        reasons.append("timeline_p95_missing")
    elif float(timeline_p95) > float(args.timeline_p95_budget_ms):
        result = "degraded"
        reasons.append("timeline_p95_above_budget")

    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "snapshot": str(snapshot_path),
            "timeline_p95_ms": timeline_p95,
            "timeline_p95_budget_ms": float(args.timeline_p95_budget_ms),
        },
    }
    _write(args.summary_path, summary)
    print(
        "[timeline-perf-gate] result={result} timeline_p95_ms={p95} budget_ms={budget} reasons={reasons}".format(
            result=result,
            p95=timeline_p95,
            budget=float(args.timeline_p95_budget_ms),
            reasons="none" if not reasons else ",".join(reasons),
        )
    )
    if result == "fail":
        return 1
    if result == "degraded" and args.fail_on_degraded:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
