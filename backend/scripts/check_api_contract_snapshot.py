#!/usr/bin/env python3
"""Fail-closed API contract drift gate based on FastAPI route snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import IDEMPOTENCY_EXEMPT_PATHS, app as fastapi_app  # noqa: E402

SNAPSHOT_SCHEMA_VERSION = "v1"
DEFAULT_SNAPSHOT_PATH = REPO_ROOT / "docs" / "security" / "api-contract-snapshot.json"
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
IGNORE_METHODS = frozenset({"HEAD", "OPTIONS"})


def _iter_api_routes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in fastapi_app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = str(route.path)
        if not path.startswith("/api/"):
            continue
        methods = sorted(str(method).upper().strip() for method in (route.methods or set()))
        for method in methods:
            if method in IGNORE_METHODS:
                continue
            idempotency_policy = "n/a"
            if method in MUTATING_METHODS:
                idempotency_policy = "exempt" if path in IDEMPOTENCY_EXEMPT_PATHS else "required"
            rows.append(
                {
                    "method": method,
                    "path": path,
                    "idempotency_policy": idempotency_policy,
                }
            )
    rows.sort(key=lambda item: (str(item["path"]), str(item["method"])))
    return rows


def build_api_contract_snapshot() -> dict[str, Any]:
    routes = _iter_api_routes()
    hash_input = "\n".join(
        f"{row['method']} {row['path']} {row['idempotency_policy']}" for row in routes
    )
    digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "route_count": len(routes),
        "route_digest": digest,
        "idempotency_exempt_paths": sorted(str(path) for path in IDEMPOTENCY_EXEMPT_PATHS),
        "routes": routes,
    }


def _load_snapshot(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("snapshot root must be object")
    return payload


def _write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _check_snapshot(path: Path, expected: dict[str, Any]) -> int:
    if not path.exists():
        print(f"[api-contract-snapshot] fail: snapshot missing: {path}")
        print("[api-contract-snapshot] hint: run with --write to create/update snapshot")
        return 1
    try:
        current = _load_snapshot(path)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[api-contract-snapshot] fail: invalid snapshot: {type(exc).__name__}")
        return 1

    if current.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        print(
            "[api-contract-snapshot] fail: schema version mismatch "
            f"(expected={SNAPSHOT_SCHEMA_VERSION} got={current.get('schema_version')})"
        )
        return 1

    if current != expected:
        print("[api-contract-snapshot] fail: API contract drift detected")
        print(f"  expected_digest: {expected.get('route_digest')}")
        print(f"  current_digest:  {current.get('route_digest')}")
        print("[api-contract-snapshot] hint: review route/idempotency changes then run --write")
        return 1

    print("[api-contract-snapshot] ok: contract snapshot matches")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check/write API contract snapshot")
    parser.add_argument(
        "--snapshot-path",
        default=str(DEFAULT_SNAPSHOT_PATH),
        help="Path to api-contract-snapshot.json",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write current snapshot to file and exit 0.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    snapshot_path = Path(args.snapshot_path).resolve()
    expected = build_api_contract_snapshot()
    if args.write:
        _write_snapshot(snapshot_path, expected)
        print(f"[api-contract-snapshot] wrote snapshot: {snapshot_path}")
        return 0
    return _check_snapshot(snapshot_path, expected)


if __name__ == "__main__":
    raise SystemExit(main())
