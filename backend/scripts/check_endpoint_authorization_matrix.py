#!/usr/bin/env python3
"""Policy-as-code gate for endpoint authorization matrix coverage."""

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

from app.main import IDEMPOTENCY_EXEMPT_PATHS, app as fastapi_app  # noqa: E402

MATRIX_SCHEMA_VERSION = "1.0.0"
MATRIX_PATH = REPO_ROOT / "docs" / "security" / "endpoint-authorization-matrix.json"
INVENTORY_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
EXCLUDED_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"})
ALLOWED_AUTH_MODES = frozenset({"public", "authenticated"})
ALLOWED_IDEMPOTENCY_POLICIES = frozenset({"required", "exempt"})
ALLOWED_SUBJECT_SCOPES = frozenset(
    {
        "n/a",
        "credential_owner",
        "current_user",
        "admin_allowlist",
        "resource_owner",
        "pair_member",
        "session_participant",
        "notification_owner",
    }
)
TEST_REF_MARKER_PATTERN = re.compile(
    r"^\s*#\s*AUTHZ_MATRIX:\s*(POST|PUT|PATCH|DELETE)\s+(\S+)\s*$"
)
TEST_REF_DENY_MARKER_PATTERN = re.compile(
    r"^\s*#\s*AUTHZ_DENY_MATRIX:\s*(POST|PUT|PATCH|DELETE)\s+(\S+)\s*$"
)


@dataclass(frozen=True)
class EndpointAuthzMatrixViolation:
    method: str
    path: str
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_mutating_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in EXCLUDED_PATHS:
            continue

        methods = route.methods or set()
        for method in methods:
            normalized_method = str(method).upper().strip()
            if normalized_method in MUTATING_METHODS:
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
        if method not in MUTATING_METHODS:
            continue
        if not path:
            continue
        owner_by_key[(method, path)] = owner_team

    return owner_by_key


def _load_test_ref_markers(test_ref_path: Path) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    allow_markers: set[tuple[str, str]] = set()
    deny_markers: set[tuple[str, str]] = set()
    content = test_ref_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        match = TEST_REF_MARKER_PATTERN.match(line)
        if match:
            allow_markers.add((match.group(1).upper(), match.group(2).strip()))
            continue

        deny_match = TEST_REF_DENY_MARKER_PATTERN.match(line)
        if deny_match:
            deny_markers.add((deny_match.group(1).upper(), deny_match.group(2).strip()))

    return allow_markers, deny_markers


def collect_endpoint_authorization_matrix_violations(
    *,
    app: FastAPI = fastapi_app,
    matrix_payload: dict[str, Any] | None = None,
    inventory_payload: dict[str, Any] | None = None,
    repo_root: Path = REPO_ROOT,
) -> list[EndpointAuthzMatrixViolation]:
    payload = matrix_payload if matrix_payload is not None else _load_json(MATRIX_PATH)
    inventory = inventory_payload if inventory_payload is not None else _load_json(INVENTORY_PATH)

    violations: list[EndpointAuthzMatrixViolation] = []

    schema_version = payload.get("schema_version")
    if schema_version != MATRIX_SCHEMA_VERSION:
        violations.append(
            EndpointAuthzMatrixViolation(
                method="*",
                path="*",
                reason="invalid_schema_version",
                details=(
                    f"endpoint matrix schema_version must be `{MATRIX_SCHEMA_VERSION}` "
                    f"(got `{schema_version}`)."
                ),
            )
        )

    entries = payload.get("entries")
    if not isinstance(entries, list):
        violations.append(
            EndpointAuthzMatrixViolation(
                method="*",
                path="*",
                reason="invalid_entries",
                details="endpoint authorization matrix `entries` must be a list.",
            )
        )
        return violations

    app_keys = _iter_mutating_route_keys(app)
    inventory_owner = _inventory_owner_by_key(inventory)
    matrix_keys: set[tuple[str, str]] = set()
    test_ref_marker_cache: dict[Path, tuple[set[tuple[str, str]], set[tuple[str, str]]]] = {}

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            violations.append(
                EndpointAuthzMatrixViolation(
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
        idempotency_policy = str(entry.get("idempotency_policy", "")).strip().lower()
        test_ref = entry.get("test_ref")

        if method not in MUTATING_METHODS:
            violations.append(
                EndpointAuthzMatrixViolation(
                    method=method or "*",
                    path=path or "*",
                    reason="invalid_method",
                    details=f"method must be one of {sorted(MUTATING_METHODS)}.",
                )
            )
            continue

        if not path.startswith("/"):
            violations.append(
                EndpointAuthzMatrixViolation(
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
                EndpointAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="duplicate_matrix_entry",
                    details="duplicate method/path in endpoint authorization matrix.",
                )
            )
            continue
        matrix_keys.add(key)

        if auth_mode not in ALLOWED_AUTH_MODES:
            violations.append(
                EndpointAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="invalid_auth_mode",
                    details=f"auth_mode must be one of {sorted(ALLOWED_AUTH_MODES)}.",
                )
            )

        is_idempotency_exempt = path in IDEMPOTENCY_EXEMPT_PATHS
        if is_idempotency_exempt:
            if idempotency_policy != "exempt":
                violations.append(
                    EndpointAuthzMatrixViolation(
                        method=method,
                        path=path,
                        reason="missing_exempt_idempotency_policy",
                        details=(
                            "idempotency_policy must be `exempt` for routes in "
                            "IDEMPOTENCY_EXEMPT_PATHS."
                        ),
                    )
                )
        elif idempotency_policy:
            if idempotency_policy not in ALLOWED_IDEMPOTENCY_POLICIES:
                violations.append(
                    EndpointAuthzMatrixViolation(
                        method=method,
                        path=path,
                        reason="invalid_idempotency_policy",
                        details=(
                            "idempotency_policy must be one of "
                            f"{sorted(ALLOWED_IDEMPOTENCY_POLICIES)}."
                        ),
                    )
                )
            elif idempotency_policy == "exempt":
                violations.append(
                    EndpointAuthzMatrixViolation(
                        method=method,
                        path=path,
                        reason="unexpected_exempt_idempotency_policy",
                        details=(
                            "idempotency_policy cannot be `exempt` for routes not in "
                            "IDEMPOTENCY_EXEMPT_PATHS."
                        ),
                    )
                )

        if subject_scope not in ALLOWED_SUBJECT_SCOPES:
            violations.append(
                EndpointAuthzMatrixViolation(
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
                EndpointAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="missing_owner_team",
                    details="owner_team must be a non-empty string.",
                )
            )

        if not isinstance(test_ref, str) or not test_ref.strip():
            violations.append(
                EndpointAuthzMatrixViolation(
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
                    EndpointAuthzMatrixViolation(
                        method=method,
                        path=path,
                        reason="missing_test_ref_file",
                        details=f"test_ref file not found: {test_ref}",
                    )
                )
            else:
                if test_path not in test_ref_marker_cache:
                    test_ref_marker_cache[test_path] = _load_test_ref_markers(test_path)
                allow_markers, deny_markers = test_ref_marker_cache[test_path]
                if key not in allow_markers:
                    violations.append(
                        EndpointAuthzMatrixViolation(
                            method=method,
                            path=path,
                            reason="missing_test_ref_marker",
                            details=(
                                f"test_ref file must contain marker "
                                f"`# AUTHZ_MATRIX: {method} {path}`."
                            ),
                        )
                    )
                if "{" in path and auth_mode == "authenticated" and key not in deny_markers:
                    violations.append(
                        EndpointAuthzMatrixViolation(
                            method=method,
                            path=path,
                            reason="missing_test_ref_deny_marker",
                            details=(
                                f"test_ref file must contain deny marker "
                                f"`# AUTHZ_DENY_MATRIX: {method} {path}` for path tampering coverage."
                            ),
                        )
                    )

        inventory_owner_team = inventory_owner.get(key)
        if inventory_owner_team is None:
            violations.append(
                EndpointAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="missing_inventory_entry",
                    details=(
                        "method/path is not present in docs/security/api-inventory.json "
                        "mutating HTTP entries."
                    ),
                )
            )
        elif owner_team and owner_team != inventory_owner_team:
            violations.append(
                EndpointAuthzMatrixViolation(
                    method=method,
                    path=path,
                    reason="owner_team_mismatch",
                    details=(
                        f"matrix owner_team `{owner_team}` does not match "
                        f"inventory owner_team `{inventory_owner_team}`."
                    ),
                )
            )

    missing_matrix_keys = sorted(app_keys - matrix_keys, key=lambda item: (item[1], item[0]))
    for method, path in missing_matrix_keys:
        violations.append(
            EndpointAuthzMatrixViolation(
                method=method,
                path=path,
                reason="missing_matrix_entry",
                details="mutating route is missing from endpoint authorization matrix.",
            )
        )

    stale_matrix_keys = sorted(matrix_keys - app_keys, key=lambda item: (item[1], item[0]))
    for method, path in stale_matrix_keys:
        violations.append(
            EndpointAuthzMatrixViolation(
                method=method,
                path=path,
                reason="stale_matrix_entry",
                details="endpoint authorization matrix contains route not present in FastAPI app.",
            )
        )

    return violations


def run_policy_check() -> int:
    violations = collect_endpoint_authorization_matrix_violations()
    if not violations:
        print("[endpoint-authz-matrix] ok: mutating endpoint coverage satisfied")
        return 0

    print("[endpoint-authz-matrix] failed:", file=sys.stderr)
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
