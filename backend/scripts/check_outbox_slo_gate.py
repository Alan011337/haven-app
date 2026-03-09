#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate notification outbox SLO warning thresholds.")
    parser.add_argument("--snapshot", required=True, help="Path to outbox health snapshot json.")
    parser.add_argument("--summary-path", default="")
    parser.add_argument("--warn-depth", type=float, default=25.0)
    parser.add_argument("--warn-dead-rate", type=float, default=0.20)
    parser.add_argument("--fail-on-degraded", action="store_true")
    return parser.parse_args()


def _write_summary(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"[outbox-slo-gate] fail: snapshot missing: {snapshot_path}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["snapshot_missing"]})
        return 1

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    outbox = payload.get("outbox") if isinstance(payload, dict) else None
    if not isinstance(outbox, dict):
        print("[outbox-slo-gate] fail: snapshot missing outbox object")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["outbox_missing"]})
        return 1

    depth = outbox.get("depth")
    dead_rate = outbox.get("dead_letter_rate")

    reasons: list[str] = []
    if isinstance(depth, (int, float)) and float(depth) > float(args.warn_depth):
        reasons.append("outbox_depth_above_warn_threshold")
    if isinstance(dead_rate, (int, float)) and float(dead_rate) > float(args.warn_dead_rate):
        reasons.append("outbox_dead_letter_rate_above_warn_threshold")

    degraded = bool(reasons)
    result = "degraded" if degraded else "pass"
    if degraded and args.fail_on_degraded:
        result = "fail"

    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "depth": depth,
            "dead_letter_rate": dead_rate,
            "warn_depth": float(args.warn_depth),
            "warn_dead_rate": float(args.warn_dead_rate),
            "fail_on_degraded": bool(args.fail_on_degraded),
        },
    }
    _write_summary(args.summary_path, summary)

    print("[outbox-slo-gate] result")
    print(f"  result: {result}")
    print(f"  depth: {depth}")
    print(f"  dead_letter_rate: {dead_rate}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
