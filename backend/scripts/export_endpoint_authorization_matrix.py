#!/usr/bin/env python3
"""Generate and validate endpoint authorization matrix drift for mutating HTTP routes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import IDEMPOTENCY_EXEMPT_PATHS, app as fastapi_app  # noqa: E402

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
EXCLUDED_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"})
DEFAULT_MATRIX_PATH = REPO_ROOT / "docs" / "security" / "endpoint-authorization-matrix.json"
DEFAULT_INVENTORY_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "security" / "endpoint-authorization-matrix.generated.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _iter_mutating_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in EXCLUDED_PATHS:
            continue
        for method in route.methods or set():
            normalized = str(method).upper().strip()
            if normalized in MUTATING_METHODS:
                keys.add((normalized, route.path))
    return keys


def _inventory_entry_by_key(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("protocol") != "http":
            continue
        method = str(entry.get("method", "")).upper().strip()
        path = str(entry.get("path", "")).strip()
        if method in MUTATING_METHODS and path:
            index[(method, path)] = entry
    return index


def _matrix_entry_by_key(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        method = str(entry.get("method", "")).upper().strip()
        path = str(entry.get("path", "")).strip()
        if method in MUTATING_METHODS and path:
            index[(method, path)] = entry
    return index


def _infer_auth_mode(
    *,
    existing_entry: dict[str, Any] | None,
    inventory_entry: dict[str, Any] | None,
) -> str:
    existing_auth_mode = str((existing_entry or {}).get("auth_mode", "")).strip()
    if existing_auth_mode in {"public", "authenticated"}:
        return existing_auth_mode
    inventory_policy = str((inventory_entry or {}).get("auth_policy", "")).strip()
    return "public" if inventory_policy == "public" else "authenticated"


def _infer_subject_scope(
    *,
    existing_entry: dict[str, Any] | None,
    auth_mode: str,
) -> str:
    existing_scope = str((existing_entry or {}).get("subject_scope", "")).strip()
    if existing_scope:
        return existing_scope
    return "n/a" if auth_mode == "public" else "current_user"


def _infer_test_ref(
    *,
    existing_entry: dict[str, Any] | None,
    owner_team: str,
) -> str:
    existing_ref = str((existing_entry or {}).get("test_ref", "")).strip()
    if existing_ref:
        return existing_ref
    if owner_team == "backend-billing":
        return "backend/tests/test_billing_authorization_matrix.py"
    if owner_team == "backend-auth":
        return "backend/tests/test_auth_token_endpoint_security.py"
    if owner_team == "backend-core":
        return "backend/tests/test_core_read_authorization_matrix.py"
    return "backend/tests/test_endpoint_authorization_matrix_policy.py"


def build_generated_matrix_payload(
    *,
    app: FastAPI,
    matrix_payload: dict[str, Any],
    inventory_payload: dict[str, Any],
) -> dict[str, Any]:
    inventory_index = _inventory_entry_by_key(inventory_payload)
    existing_index = _matrix_entry_by_key(matrix_payload)
    route_keys = sorted(_iter_mutating_route_keys(app), key=lambda item: (item[1], item[0]))

    entries: list[dict[str, Any]] = []
    for method, path in route_keys:
        existing = existing_index.get((method, path))
        inventory_entry = inventory_index.get((method, path), {})
        owner_team = str(inventory_entry.get("owner_team") or (existing or {}).get("owner_team") or "backend-platform")
        auth_mode = _infer_auth_mode(existing_entry=existing, inventory_entry=inventory_entry)
        subject_scope = _infer_subject_scope(existing_entry=existing, auth_mode=auth_mode)
        test_ref = _infer_test_ref(existing_entry=existing, owner_team=owner_team)
        idempotency_policy = "exempt" if path in IDEMPOTENCY_EXEMPT_PATHS else "required"

        entry: dict[str, Any] = {
            "method": method,
            "path": path,
            "auth_mode": auth_mode,
            "subject_scope": subject_scope,
            "owner_team": owner_team,
            "idempotency_policy": idempotency_policy,
            "test_ref": test_ref,
        }
        entries.append(entry)

    return {
        "schema_version": matrix_payload.get("schema_version", "1.0.0"),
        "artifact_kind": matrix_payload.get("artifact_kind", "endpoint-authorization-matrix"),
        "generated_by": "backend/scripts/export_endpoint_authorization_matrix.py",
        "entries": entries,
    }


def check_matrix_drift(
    *,
    app: FastAPI,
    matrix_payload: dict[str, Any],
    inventory_payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    route_keys = _iter_mutating_route_keys(app)
    matrix_index = _matrix_entry_by_key(matrix_payload)
    inventory_index = _inventory_entry_by_key(inventory_payload)

    missing_keys = sorted(route_keys - set(matrix_index), key=lambda item: (item[1], item[0]))
    stale_keys = sorted(set(matrix_index) - route_keys, key=lambda item: (item[1], item[0]))
    for method, path in missing_keys:
        errors.append(f"missing matrix entry for {method} {path}")
    for method, path in stale_keys:
        errors.append(f"stale matrix entry for {method} {path}")

    for key in sorted(route_keys, key=lambda item: (item[1], item[0])):
        matrix_entry = matrix_index.get(key)
        inventory_entry = inventory_index.get(key)
        if matrix_entry is None:
            continue
        if inventory_entry is None:
            errors.append(f"missing inventory entry for {key[0]} {key[1]}")
            continue
        inventory_owner = str(inventory_entry.get("owner_team", "")).strip()
        matrix_owner = str(matrix_entry.get("owner_team", "")).strip()
        if inventory_owner and matrix_owner != inventory_owner:
            errors.append(
                f"owner mismatch for {key[0]} {key[1]}: matrix={matrix_owner} inventory={inventory_owner}"
            )

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX_PATH)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--check-current", action="store_true")
    parser.add_argument("--write-draft", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    matrix_payload = _load_json(args.matrix)
    inventory_payload = _load_json(args.inventory)

    if args.check_current:
        errors = check_matrix_drift(
            app=fastapi_app,
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )
        if errors:
            print("[endpoint-matrix-export] drift detected:", file=sys.stderr)
            for line in errors:
                print(f"  - {line}", file=sys.stderr)
            return 1
        print("[endpoint-matrix-export] check ok: no route/owner drift")
        return 0

    generated = build_generated_matrix_payload(
        app=fastapi_app,
        matrix_payload=matrix_payload,
        inventory_payload=inventory_payload,
    )
    if args.write_draft:
        args.output.write_text(_canonical_json(generated), encoding="utf-8")
        print(f"[endpoint-matrix-export] wrote draft: {args.output}")
        return 0

    print(_canonical_json(generated), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
