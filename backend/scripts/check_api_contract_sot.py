#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_KEYS = {
    "path",
    "method",
    "endpoint",
    "auth_policy",
    "owner_team",
    "data_sensitivity",
}

ALLOW_NON_API_PREFIXES = (
    "/",
    "/health",
    "/health/slo",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/ws/",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate API inventory as single source of truth contract.")
    parser.add_argument(
        "--inventory",
        default="docs/security/api-inventory.json",
        help="Path to api inventory json.",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="Optional summary output path.",
    )
    parser.add_argument(
        "--require-api-prefix",
        action="store_true",
        help="Require every entry path to start with '/' and API entries to use '/api' prefix unless root health endpoints.",
    )
    return parser.parse_args()


def _write_summary(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"[api-contract-sot] fail: inventory missing: {inventory_path}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["inventory_missing"]})
        return 1

    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except Exception:
        print("[api-contract-sot] fail: inventory parse error")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["inventory_parse_error"]})
        return 1

    entries = payload.get("entries") if isinstance(payload, dict) else None
    schema_version = payload.get("schema_version") if isinstance(payload, dict) else None
    reasons: list[str] = []

    schema_version_text = str(schema_version or "")
    if not (schema_version_text == "v1" or schema_version_text.startswith("1.")):
        reasons.append("schema_version_mismatch")
    if not isinstance(entries, list) or not entries:
        reasons.append("entries_missing")
        entries = []

    missing_required = 0
    invalid_paths = 0
    api_entries = 0

    for entry in entries:
        if not isinstance(entry, dict):
            missing_required += 1
            continue
        missing = REQUIRED_KEYS - set(entry.keys())
        if missing:
            missing_required += 1
        path = str(entry.get("path") or "")
        if not path.startswith("/"):
            invalid_paths += 1
            continue
        if path.startswith("/api"):
            api_entries += 1
        if args.require_api_prefix and not path.startswith("/api") and not path.startswith(ALLOW_NON_API_PREFIXES):
            invalid_paths += 1

    if missing_required > 0:
        reasons.append("entry_required_keys_missing")
    if invalid_paths > 0:
        reasons.append("path_contract_violation")
    if api_entries == 0:
        reasons.append("api_entries_missing")

    result = "pass" if not reasons else "fail"
    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "schema_version": schema_version,
            "entry_total": len(entries),
            "api_entry_total": api_entries,
            "missing_required_entries": missing_required,
            "invalid_path_entries": invalid_paths,
        },
    }
    _write_summary(args.summary_path, summary)

    print("[api-contract-sot] result")
    print(f"  result: {result}")
    print(f"  schema_version: {schema_version}")
    print(f"  entry_total: {len(entries)}")
    print(f"  api_entry_total: {api_entries}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
