#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_TOKENS = (
    "build_rate_limit_scope_key",
    "build_ws_message_scope_key",
    "user:",
    "ip:",
    "device:",
    "pair:",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate rate limit scope policy contract.")
    parser.add_argument("--source", default="backend/app/services/rate_limit_scope.py")
    parser.add_argument("--summary-path", default="")
    return parser.parse_args()


def _write_summary(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    source = Path(args.source)
    if not source.exists():
        print(f"[rate-limit-policy] fail: source missing: {source}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["source_missing"]})
        return 1

    text = source.read_text(encoding="utf-8")
    missing = [token for token in REQUIRED_TOKENS if token not in text]
    result = "pass" if not missing else "fail"
    reasons = [] if result == "pass" else ["required_scope_tokens_missing"]

    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "missing_tokens": missing,
            "source": str(source),
        },
    }
    _write_summary(args.summary_path, summary)

    print("[rate-limit-policy] result")
    print(f"  result: {result}")
    print(f"  missing_tokens: {', '.join(missing) if missing else 'none'}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
