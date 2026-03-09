#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate data-rights fire-drill snapshot report.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--md-output", default="", help="Optional markdown output path.")
    parser.add_argument("--access-latency-seconds", type=float, default=0.0)
    parser.add_argument("--export-latency-seconds", type=float, default=0.0)
    parser.add_argument("--erase-latency-seconds", type=float, default=0.0)
    parser.add_argument("--result", choices=["pass", "degraded", "fail"], default="pass")
    parser.add_argument("--notes", default="")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "v1",
        "recorded_at": _iso_now(),
        "result": args.result,
        "checks": {
            "access": {"latency_seconds": float(args.access_latency_seconds), "status": "pass" if args.result != "fail" else "fail"},
            "export": {"latency_seconds": float(args.export_latency_seconds), "status": "pass" if args.result == "pass" else "degraded"},
            "erase": {"latency_seconds": float(args.erase_latency_seconds), "status": "pass" if args.result == "pass" else "degraded"},
        },
        "notes": (args.notes or "").strip(),
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

    if args.md_output:
        md_path = Path(args.md_output)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md = [
            "# Data Rights Fire Drill Snapshot",
            "",
            f"- recorded_at: {payload['recorded_at']}",
            f"- result: {payload['result']}",
            f"- access_latency_seconds: {payload['checks']['access']['latency_seconds']}",
            f"- export_latency_seconds: {payload['checks']['export']['latency_seconds']}",
            f"- erase_latency_seconds: {payload['checks']['erase']['latency_seconds']}",
            f"- notes: {payload['notes'] or 'none'}",
        ]
        md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print("[data-rights-fire-drill] result")
    print(f"  output: {output_path}")
    print(f"  result: {payload['result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
