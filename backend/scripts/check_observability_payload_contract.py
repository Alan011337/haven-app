#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_SLI_KEYS = {
    "notification_runtime",
    "dynamic_content_runtime",
}


REQUIRED_OUTBOX_CHECK_KEYS = {
    "notification_outbox_depth",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate /health or /health/slo payload observability contract.")
    parser.add_argument("--payload-file", required=True)
    parser.add_argument("--summary-path", default="")
    parser.add_argument("--allow-missing-keys", action="store_true")
    return parser.parse_args()


def _write_summary(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    payload_path = Path(args.payload_file)
    if not payload_path.exists():
        print(f"[observability-contract] fail: payload missing: {payload_path}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["payload_missing"]})
        return 1

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    sli = payload.get("sli") if isinstance(payload, dict) else None
    checks = payload.get("checks") if isinstance(payload, dict) else None

    reasons: list[str] = []
    if not isinstance(sli, dict):
        reasons.append("sli_missing")
        sli = {}
    if not isinstance(checks, dict):
        reasons.append("checks_missing")
        checks = {}

    missing_sli = sorted([key for key in REQUIRED_SLI_KEYS if key not in sli])
    missing_checks = sorted([key for key in REQUIRED_OUTBOX_CHECK_KEYS if key not in checks])

    if missing_sli:
        reasons.append("sli_keys_missing")
    if missing_checks:
        reasons.append("checks_keys_missing")

    if reasons and args.allow_missing_keys:
        result = "skipped"
    else:
        result = "pass" if not reasons else "fail"
    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "missing_sli": missing_sli,
            "missing_checks": missing_checks,
        },
    }
    _write_summary(args.summary_path, summary)

    print("[observability-contract] result")
    print(f"  result: {result}")
    print(f"  missing_sli: {', '.join(missing_sli) if missing_sli else 'none'}")
    print(f"  missing_checks: {', '.join(missing_checks) if missing_checks else 'none'}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result in {"pass", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
