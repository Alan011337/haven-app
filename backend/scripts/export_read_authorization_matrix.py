#!/usr/bin/env python3
"""Generate and validate critical read authorization matrix drift."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app as fastapi_app  # noqa: E402

READ_POLICY_PATH = BACKEND_ROOT / "scripts" / "check_read_authorization_matrix.py"
_SPEC = importlib.util.spec_from_file_location("check_read_authorization_matrix", READ_POLICY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module: {READ_POLICY_PATH}")
_POLICY = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _POLICY
_SPEC.loader.exec_module(_POLICY)
CRITICAL_READ_KEYS = _POLICY.CRITICAL_READ_KEYS
collect_read_authorization_matrix_violations = _POLICY.collect_read_authorization_matrix_violations

DEFAULT_MATRIX_PATH = REPO_ROOT / "docs" / "security" / "read-authorization-matrix.json"
DEFAULT_INVENTORY_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "security" / "read-authorization-matrix.generated.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _inventory_entry_by_key(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("protocol") != "http":
            continue
        method = str(entry.get("method", "")).upper().strip()
        path = str(entry.get("path", "")).strip()
        if method == "GET" and path:
            index[(method, path)] = entry
    return index


def _matrix_entry_by_key(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        method = str(entry.get("method", "")).upper().strip()
        path = str(entry.get("path", "")).strip()
        if method == "GET" and path:
            index[(method, path)] = entry
    return index


def _infer_test_ref(*, existing: dict[str, Any] | None, owner_team: str) -> str:
    existing_ref = str((existing or {}).get("test_ref", "")).strip()
    if existing_ref:
        return existing_ref
    if owner_team == "backend-billing":
        return "backend/tests/test_billing_authorization_matrix.py"
    return "backend/tests/test_read_authorization_matrix_policy.py"


def build_generated_read_matrix_payload(
    *,
    matrix_payload: dict[str, Any],
    inventory_payload: dict[str, Any],
) -> dict[str, Any]:
    inventory_index = _inventory_entry_by_key(inventory_payload)
    matrix_index = _matrix_entry_by_key(matrix_payload)
    entries: list[dict[str, Any]] = []

    for method, path in sorted(CRITICAL_READ_KEYS, key=lambda item: (item[1], item[0])):
        existing = matrix_index.get((method, path))
        inventory_entry = inventory_index.get((method, path), {})
        owner_team = str(inventory_entry.get("owner_team") or (existing or {}).get("owner_team") or "backend-core")
        subject_scope = str((existing or {}).get("subject_scope", "")).strip() or "current_user"
        entries.append(
            {
                "method": method,
                "path": path,
                "auth_mode": "authenticated",
                "subject_scope": subject_scope,
                "owner_team": owner_team,
                "test_ref": _infer_test_ref(existing=existing, owner_team=owner_team),
            }
        )

    return {
        "schema_version": matrix_payload.get("schema_version", "1.0.0"),
        "artifact_kind": matrix_payload.get("artifact_kind", "read-authorization-matrix"),
        "generated_by": "backend/scripts/export_read_authorization_matrix.py",
        "entries": entries,
    }


def check_read_matrix_drift(
    *,
    matrix_payload: dict[str, Any],
    inventory_payload: dict[str, Any],
) -> list[str]:
    violations = collect_read_authorization_matrix_violations(
        app=fastapi_app,
        matrix_payload=matrix_payload,
        inventory_payload=inventory_payload,
    )
    return [f"{item.reason}: {item.method} {item.path}" for item in violations]


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
        errors = check_read_matrix_drift(
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )
        if errors:
            print("[read-matrix-export] drift detected:", file=sys.stderr)
            for item in errors:
                print(f"  - {item}", file=sys.stderr)
            return 1
        print("[read-matrix-export] check ok: no drift")
        return 0

    payload = build_generated_read_matrix_payload(
        matrix_payload=matrix_payload,
        inventory_payload=inventory_payload,
    )
    if args.write_draft:
        args.output.write_text(_canonical_json(payload), encoding="utf-8")
        print(f"[read-matrix-export] wrote draft: {args.output}")
        return 0

    print(_canonical_json(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
