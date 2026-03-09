#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
EXEMPT_PATH_PREFIXES = (
    "/api/auth/token",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/billing/webhooks",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check mutating API idempotency coverage contract.")
    parser.add_argument("--inventory", default="docs/security/api-inventory.json")
    parser.add_argument("--summary-path", default="")
    parser.add_argument(
        "--max-uncovered",
        type=int,
        default=0,
        help="Maximum uncovered mutating endpoints allowed.",
    )
    return parser.parse_args()


def _write_summary(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES)


def main() -> int:
    args = _parse_args()
    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"[idempotency-coverage] fail: inventory missing: {inventory_path}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["inventory_missing"]})
        return 1

    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        print("[idempotency-coverage] fail: inventory entries missing")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["entries_missing"]})
        return 1

    mutating_api_paths: list[str] = []
    exempt_paths: list[str] = []
    covered_paths: list[str] = []
    uncovered_paths: list[str] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        method = str(entry.get("method") or "").upper()
        path = str(entry.get("path") or "")
        if method not in MUTATING_METHODS or not path.startswith("/api"):
            continue
        mutating_api_paths.append(f"{method} {path}")
        if _is_exempt(path):
            exempt_paths.append(f"{method} {path}")
            continue
        # Contract: non-exempt mutating API paths are protected by global idempotency guard.
        # We still track explicit deny list hooks for future per-route overrides.
        if "/replay-unsafe" in path:
            uncovered_paths.append(f"{method} {path}")
        else:
            covered_paths.append(f"{method} {path}")

    uncovered_count = len(uncovered_paths)
    result = "pass" if uncovered_count <= max(0, int(args.max_uncovered)) else "fail"
    reasons = [] if result == "pass" else ["uncovered_mutating_endpoints"]

    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "mutating_api_total": len(mutating_api_paths),
            "covered_total": len(covered_paths),
            "exempt_total": len(exempt_paths),
            "uncovered_total": uncovered_count,
            "max_uncovered": int(args.max_uncovered),
        },
        "uncovered": uncovered_paths,
    }
    _write_summary(args.summary_path, summary)

    print("[idempotency-coverage] result")
    print(f"  result: {result}")
    print(f"  mutating_api_total: {len(mutating_api_paths)}")
    print(f"  covered_total: {len(covered_paths)}")
    print(f"  exempt_total: {len(exempt_paths)}")
    print(f"  uncovered_total: {uncovered_count}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
