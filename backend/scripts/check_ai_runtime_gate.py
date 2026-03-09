#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_RESULTS = {"pass", "degraded", "fail"}
ALLOWED_REASON_ENUM = {
    "none",
    "missing_evidence",
    "stale_evidence",
    "evaluation_failed",
    "drift_detected",
    "schema_non_compliant",
    "hallucination_proxy_high",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AI runtime/gate snapshot determinism and enums.")
    parser.add_argument("--snapshot", required=True, help="Path to AI quality snapshot evidence JSON.")
    parser.add_argument("--summary-path", default="")
    parser.add_argument("--allow-degraded", action="store_true")
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
        print(f"[ai-runtime-gate] fail: snapshot missing: {snapshot_path}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["missing_evidence"]})
        return 1

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    evaluation_block = payload.get("evaluation") if isinstance(payload, dict) else None
    if isinstance(evaluation_block, dict):
        evaluation_result = str(evaluation_block.get("result") or "unknown")
        reasons_raw = evaluation_block.get("degraded_reasons")
    else:
        evaluation_result = str(payload.get("evaluation_result") or "unknown")
        reasons_raw = payload.get("degraded_reasons")
    reasons = reasons_raw if isinstance(reasons_raw, list) else []

    fail_reasons: list[str] = []
    if evaluation_result not in ALLOWED_RESULTS:
        fail_reasons.append("invalid_evaluation_result")

    invalid_reason_values = [r for r in reasons if str(r) not in ALLOWED_REASON_ENUM]
    if invalid_reason_values:
        fail_reasons.append("invalid_reason_enum")

    gate_result = "pass"
    if evaluation_result == "fail":
        gate_result = "fail"
    elif evaluation_result == "degraded" and not args.allow_degraded:
        gate_result = "fail"
    if fail_reasons:
        gate_result = "fail"

    summary = {
        "result": gate_result,
        "reasons": fail_reasons,
        "meta": {
            "evaluation_result": evaluation_result,
            "degraded_reason_count": len(reasons),
            "allow_degraded": bool(args.allow_degraded),
        },
    }
    _write_summary(args.summary_path, summary)

    print("[ai-runtime-gate] result")
    print(f"  result: {gate_result}")
    print(f"  evaluation_result: {evaluation_result}")
    print(f"  degraded_reasons: {', '.join(str(r) for r in reasons) if reasons else 'none'}")
    print(f"  reasons: {', '.join(fail_reasons) if fail_reasons else 'none'}")
    return 0 if gate_result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
