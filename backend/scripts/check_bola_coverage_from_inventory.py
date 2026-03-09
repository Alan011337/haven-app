#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

CRITICAL_RESOURCE_PREFIXES = (
    "/api/journals",
    "/api/cards",
    "/api/decks",
    "/api/memory",
    "/api/users",
)

ALLOW_PUBLIC_CRITICAL = {
    ("POST", "/api/users/"),
    ("POST", "/api/users/referrals/landing-view"),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check BOLA baseline coverage from API inventory metadata.")
    parser.add_argument("--inventory", default="docs/security/api-inventory.json")
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
    inventory = Path(args.inventory)
    if not inventory.exists():
        print(f"[bola-coverage] fail: inventory missing: {inventory}")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["inventory_missing"]})
        return 1

    payload = json.loads(inventory.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        print("[bola-coverage] fail: entries missing")
        _write_summary(args.summary_path, {"result": "fail", "reasons": ["entries_missing"]})
        return 1

    critical_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and isinstance(entry.get("path"), str)
        and entry["path"].startswith(CRITICAL_RESOURCE_PREFIXES)
    ]

    public_critical = []
    for entry in critical_entries:
        if str(entry.get("auth_policy") or "").lower() != "public":
            continue
        method = str(entry.get("method") or "").upper()
        path = str(entry.get("path") or "")
        if (method, path) in ALLOW_PUBLIC_CRITICAL:
            continue
        public_critical.append(f"{method} {path}")

    reasons: list[str] = []
    if not critical_entries:
        reasons.append("critical_entries_missing")
    if public_critical:
        reasons.append("critical_entry_public_auth_policy")

    result = "pass" if not reasons else "fail"
    summary = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "critical_entry_total": len(critical_entries),
            "public_critical_total": len(public_critical),
        },
        "public_critical": public_critical,
    }
    _write_summary(args.summary_path, summary)

    print("[bola-coverage] result")
    print(f"  result: {result}")
    print(f"  critical_entry_total: {len(critical_entries)}")
    print(f"  public_critical_total: {len(public_critical)}")
    print(f"  reasons: {', '.join(reasons) if reasons else 'none'}")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
