#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export OpenAPI route snapshot for contract drift checks.")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--inventory",
        default="../docs/security/api-inventory.json",
        help="API inventory source used as contract snapshot baseline.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"[openapi-snapshot] fail: inventory missing: {inventory_path}")
        return 1

    route_entries: list[dict[str, str]] = []
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        print("[openapi-snapshot] fail: inventory entries missing")
        return 1

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        route_entries.append(
            {
                "method": str(entry.get("method") or "").upper(),
                "path": str(entry.get("path") or ""),
                "operation_id": str(entry.get("endpoint") or ""),
            }
        )

    payload = {
        "schema_version": "v1",
        "recorded_at": _iso_now(),
        "route_total": len(route_entries),
        "routes": route_entries,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

    print("[openapi-snapshot] result")
    print(f"  output: {output_path}")
    print(f"  route_total: {len(route_entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
