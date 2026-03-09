#!/usr/bin/env python3
"""Summarize optional degraded components from gate orchestration output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--orchestration-summary",
        default="/tmp/release-gate-orchestration-summary-local.json",
        help="Path to build_gate_orchestration_summary output.",
    )
    parser.add_argument("--output", default="/tmp/release-gate-noise-summary.json")
    parser.add_argument("--fail-on-required-degraded", action="store_true")
    parser.add_argument("--fail-on-required-skipped", action="store_true")
    parser.add_argument("--allow-missing-summary", action="store_true")
    return parser


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    source = Path(args.orchestration_summary).resolve()
    output = Path(args.output).resolve()
    if not source.exists():
        payload = {
            "result": "skipped" if args.allow_missing_summary else "fail",
            "reasons": ["orchestration_summary_missing"],
            "meta": {"source": str(source)},
            "required_degraded_components": [],
            "optional_degraded_components": [],
        }
        _write(output, payload)
        print(f"[release-gate-noise] result={payload['result']} reasons=orchestration_summary_missing")
        return 0 if args.allow_missing_summary else 1

    root = json.loads(source.read_text(encoding="utf-8"))
    components = root.get("components")
    if not isinstance(components, list):
        components = []

    required_degraded: list[str] = []
    required_skipped: list[str] = []
    optional_degraded: list[str] = []
    optional_skipped: list[str] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name") or "unknown")
        status = str(component.get("status") or "unknown")
        required = bool(component.get("required"))
        if status == "degraded":
            if required:
                required_degraded.append(name)
            else:
                optional_degraded.append(name)
        elif status == "skipped":
            if required:
                required_skipped.append(name)
            else:
                optional_skipped.append(name)

    result = "pass"
    reasons: list[str] = []
    if required_degraded:
        result = "degraded"
        reasons.append("required_components_degraded")
        if args.fail_on_required_degraded:
            result = "fail"
    if required_skipped:
        if result == "pass":
            result = "degraded"
        reasons.append("required_components_skipped")
        if args.fail_on_required_skipped:
            result = "fail"

    payload = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "source": str(source),
            "required_degraded_total": len(required_degraded),
            "optional_degraded_total": len(optional_degraded),
            "required_skipped_total": len(required_skipped),
            "optional_skipped_total": len(optional_skipped),
        },
        "required_degraded_components": sorted(required_degraded),
        "optional_degraded_components": sorted(optional_degraded),
        "required_skipped_components": sorted(required_skipped),
        "optional_skipped_components": sorted(optional_skipped),
    }
    _write(output, payload)
    print("[release-gate-noise] result")
    print(f"  result: {result}")
    print(f"  required_degraded_total: {len(required_degraded)}")
    print(f"  optional_degraded_total: {len(optional_degraded)}")
    print(f"  required_skipped_total: {len(required_skipped)}")
    print(f"  optional_skipped_total: {len(optional_skipped)}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    if result == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
