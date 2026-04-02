#!/usr/bin/env python3
"""Policy-as-code gate for critical read endpoint authorization matrix coverage."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app as fastapi_app  # noqa: E402

MATRIX_SCHEMA_VERSION = "1.0.0"
MATRIX_PATH = REPO_ROOT / "docs" / "security" / "read-authorization-matrix.json"
INVENTORY_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"

READ_METHOD = "GET"
EXCLUDED_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"})
ALLOWED_AUTH_MODES = frozenset({"authenticated"})
ALLOWED_SUBJECT_SCOPES = frozenset(
    {
        "current_user",
        "pair_member",
        "session_participant",
        "notification_owner",
        "self_or_partner",
    }
)

CRITICAL_READ_KEYS = frozenset(
    {
        (READ_METHOD, "/api/billing/reconciliation"),
        (READ_METHOD, "/api/card-decks/{deck_id}/draw"),
        (READ_METHOD, "/api/card-decks/history"),
        (READ_METHOD, "/api/card-decks/history/summary"),
        (READ_METHOD, "/api/card-decks/stats"),
        (READ_METHOD, "/api/cards/"),
        (READ_METHOD, "/api/cards/backlog"),
        (READ_METHOD, "/api/cards/daily-status"),
        (READ_METHOD, "/api/cards/draw"),
        (READ_METHOD, "/api/cards/{card_id}/conversation"),
        (READ_METHOD, "/api/users/me"),
        (READ_METHOD, "/api/users/me/data-export"),
        (READ_METHOD, "/api/users/gamification-summary"),
        (READ_METHOD, "/api/users/notifications"),
        (READ_METHOD, "/api/users/notifications/stats"),
        (READ_METHOD, "/api/users/{user_id}"),
        # Core modules (C1, C3, D1, D2, D3)
        (READ_METHOD, "/api/mediation/status"),
        (READ_METHOD, "/api/mediation/repair/status"),
        (READ_METHOD, "/api/cooldown/status"),
        (READ_METHOD, "/api/love-map/cards"),
        (READ_METHOD, "/api/love-map/notes"),
        (READ_METHOD, "/api/love-map/suggestions/shared-future"),
        (READ_METHOD, "/api/love-map/suggestions/shared-future/refinements"),
        (READ_METHOD, "/api/blueprint/"),
        (READ_METHOD, "/api/blueprint/date-suggestions"),
        (READ_METHOD, "/api/reports/weekly"),
    }
)

TEST_REF_MARKER_PATTERN = re.compile(
    r"^\s*#\s*READ_AUTHZ_MATRIX:\s*(GET)\s+(\S+)\s*$"
)


@dataclass(frozen=True)
class ReadAuthzMatrixViolation:
    method: str
    path: str
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_get_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in EXCLUDED_PATHS:
            continue

        methods = route.methods or set()
        for method in methods:
            normalized_method = str(method).upper().strip()
            if normalized_method == READ_METHOD:
                keys.add((normalized_method, route.path))

    return keys


def _inventory_owner_by_key(payload: dict[str, Any]) -> dict[tuple[str, str], str]:
    owner_by_key: dict[tuple[str, str], str] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("protocol") != "http":
            continue

        method = str(entry.get("method", "")).upper().strip()
        path = str(entry.get("path", "")).strip()
        owner_team = str(entry.get("owner_team", "")).strip()
        if method != READ_METHOD:
            continue
        if not path:
            continue
        owner_by_key[(method, path)] = owner_team

    return owner_by_key


def _load_test_ref_markers(test_ref_path: Path) -> set[tuple[str, str]]:
    markers: set[tuple[str, str]] = set()
    content = test_ref_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        match = TEST_REF_MARKER_PATTERN.match(line)
        if not match:
            continue
        markers.add((match.group(1).upper(), match.group(2).strip()))
    return markers


def collect_read_authorization_matrix_violations(
    *,
    app: FastAPI = fastapi_app,
    matrix_payload: dict[str, Any] | None = None,
    inventory_payload: dict[str, Any] | None = None,
    repo_root: Path = REPO_ROOT,
    critical_read_keys: set[tuple[str, str]] | None = None,
) -> list[ReadAuthzMatrixViolation]:
    payload = matrix_payload if matrix_payload is not None else _load_json(MATRIX_PATH)
    inventory = inventory_payload if inventory_payload is not None else _load_json(INVENTORY_PATH)
    critical_keys = set(critical_read_keys) if critical_read_keys is not None else set(CRITICAL_READ_KEYS)

    violations: list[ReadAuthzMatrixViolation] = []

    schema_version = payload.get("schema_version")
    if schema_version != MATRIX_SCHEMA_VERSION:
        violations.append(
            ReadAuthzMatrixViolation(
                method="*",
                path="*",
                reason="invalid_schema_version",
                details=(
                    f"read authorization matrix schema_version must be `{MATRIX_SCHEMA_VERSION}` "
                    f"(got `{schema_version}`)."
                ),
            )
        )

    entries = payload.get("entries")
    if not isinstance(entries, list):
        violations.append(
            ReadAuthzMatrixViolation(
                method="*",
                path="*",
                reason="invalid_entries",
                details="read authorization matrix `entries` must be a list.",
            )
        )
        return violations

    app_keys = _iter_get_route_keys(app)
    inventory_owner = _inventory_owner_by_key(inventory)
    matrix_keys: set[tuple[str, str]] = set()
    test_ref_marker_cache: dict[Path, set[tuple[str, str]]] = {}

    missing_critical_routes = sorted(critical_keys - app_keys, key=lambda item: item[1])
    for method, path in missing_critical_routes:
        violations.append(
            ReadAuthzMatrixViolation(
                method=method,
                path=path,
                reason="critical_route_missing_from_app",
                details="critical read route is not present in FastAPI app.",
            )
        )

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            violations.append(
                ReadAuthzMatrixViolation(
                    method="*",
                    path=f"entries[{index}]",
                    reason="invalid_entry",
                    details="entry must be an object.",
                )
            )
            continue

        method = str(entry.get("method", "")).upper().strip()
        path = str(entry.get("path", "")).strip()
        auth_mode = str(entry.get("auth_mode", "")).strip()
        subject_scope = str(entry.get("subject_scope", "")).strip()
        owner_team = str(entry.get("owner_team", "")).strip()
        test_ref = entry.get("test_ref")

        if method != READ_METHOD:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method or "*",
                    path=path or "*",
                    reason="invalid_method",
                    details=f"method must be `{READ_METHOD}`.",
                )
            )
            continue

        if not path.startswith("/"):
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path or "*",
                    reason="invalid_path",
                    details="path must start with '/'.",
                )
            )
            continue

        key = (method, path)
        if key in matrix_keys:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="duplicate_matrix_entry",
                    details="duplicate method/path in read authorization matrix.",
                )
            )
            continue
        matrix_keys.add(key)

        if key not in critical_keys:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="unexpected_noncritical_entry",
                    details="entry is not in critical read route set.",
                )
            )

        if auth_mode not in ALLOWED_AUTH_MODES:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="invalid_auth_mode",
                    details=f"auth_mode must be one of {sorted(ALLOWED_AUTH_MODES)}.",
                )
            )

        if subject_scope not in ALLOWED_SUBJECT_SCOPES:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="invalid_subject_scope",
                    details=(
                        "subject_scope must be one of "
                        f"{sorted(ALLOWED_SUBJECT_SCOPES)}."
                    ),
                )
            )

        if not owner_team:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="missing_owner_team",
                    details="owner_team must be a non-empty string.",
                )
            )

        if not isinstance(test_ref, str) or not test_ref.strip():
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="invalid_test_ref",
                    details="test_ref must be a non-empty repository-relative path.",
                )
            )
        else:
            test_path = repo_root / test_ref
            if not test_path.exists():
                violations.append(
                    ReadAuthzMatrixViolation(
                        method=method,
                        path=path,
                        reason="missing_test_ref_file",
                        details=f"test_ref file not found: {test_ref}",
                    )
                )
            else:
                if test_path not in test_ref_marker_cache:
                    test_ref_marker_cache[test_path] = _load_test_ref_markers(test_path)
                if key not in test_ref_marker_cache[test_path]:
                    violations.append(
                        ReadAuthzMatrixViolation(
                            method=method,
                            path=path,
                            reason="missing_test_ref_marker",
                            details=(
                                f"test_ref file must contain marker "
                                f"`# READ_AUTHZ_MATRIX: {method} {path}`."
                            ),
                        )
                    )

        inventory_owner_team = inventory_owner.get(key)
        if inventory_owner_team is None:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="missing_inventory_entry",
                    details="method/path is not present in docs/security/api-inventory.json GET entries.",
                )
            )
        elif owner_team and owner_team != inventory_owner_team:
            violations.append(
                ReadAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="owner_team_mismatch",
                    details=(
                        f"matrix owner_team `{owner_team}` does not match "
                        f"inventory owner_team `{inventory_owner_team}`."
                    ),
                )
            )

    missing_matrix_keys = sorted(critical_keys - matrix_keys, key=lambda item: item[1])
    for method, path in missing_matrix_keys:
        violations.append(
            ReadAuthzMatrixViolation(
                method=method,
                path=path,
                reason="missing_matrix_entry",
                details="critical read route is missing from read authorization matrix.",
            )
        )

    stale_matrix_keys = sorted(matrix_keys - app_keys, key=lambda item: item[1])
    for method, path in stale_matrix_keys:
        violations.append(
            ReadAuthzMatrixViolation(
                method=method,
                path=path,
                reason="stale_matrix_entry",
                details="read authorization matrix contains route not present in FastAPI app.",
            )
        )

    return violations


def run_policy_check() -> int:
    violations = collect_read_authorization_matrix_violations()
    if not violations:
        print("[read-authz-matrix] ok: critical read endpoint coverage satisfied")
        return 0

    print("[read-authz-matrix] failed:", file=sys.stderr)
    for item in violations:
        print(
            f"  - method={item.method} path={item.path} "
            f"reason={item.reason} details={item.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
