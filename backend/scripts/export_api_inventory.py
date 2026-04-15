#!/usr/bin/env python3
"""Export and validate API inventory derived from FastAPI routes."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute, WebSocketRoute

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCHEMA_VERSION = "1.1.0"
ARTIFACT_KIND = "api-inventory"
GENERATED_BY = "backend/scripts/export_api_inventory.py"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"
EXCLUDED_HTTP_PATHS = frozenset(
    {
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
    }
)
DATA_SENSITIVITY_VALUES = frozenset(
    {
        "public",
        "account_sensitive",
        "relationship_sensitive",
        "billing_sensitive",
        "operational",
    }
)
OWNER_BY_TAG = {
    "admin": "backend-core",
    "auth": "backend-auth",
    "billing": "backend-billing",
    "users": "backend-core",
    "journals": "backend-core",
    "cards": "backend-core",
    "card-decks": "backend-core",
    "reports": "backend-core",
}
RUNBOOK_BY_PATH_PREFIX = (
    ("/api/users/me/data", "docs/security/data-rights-fire-drill.md"),
    ("/api/billing", "docs/p0-execution-protocol.md#p0-d-billing-correctness-foundation"),
    ("/api/card-decks", "docs/p0-execution-protocol.md#p0-b-security-gate-v1-owaspbola"),
    ("/api/cards", "docs/p0-execution-protocol.md#p0-b-security-gate-v1-owaspbola"),
    ("/api/journals", "docs/p0-execution-protocol.md#p0-b-security-gate-v1-owaspbola"),
    ("/api/users/notifications", "docs/p0-execution-protocol.md#p0-b-security-gate-v1-owaspbola"),
    ("/api/users", "docs/p0-execution-protocol.md#p0-b-security-gate-v1-owaspbola"),
    ("/api/auth", "docs/p0-execution-protocol.md#p0-b-security-gate-v1-owaspbola"),
    ("/health", "docs/p0-execution-protocol.md#p0-a-release-gate-baseline"),
    ("/ws/", "docs/security/abuse-budget-policy.md"),
)
_CACHED_APP: FastAPI | None = None
_CACHED_CURRENT_USER_DEPENDENCY: Any | None = None


def _load_runtime_dependencies() -> tuple[FastAPI, Any]:
    global _CACHED_APP
    global _CACHED_CURRENT_USER_DEPENDENCY
    if _CACHED_APP is not None and _CACHED_CURRENT_USER_DEPENDENCY is not None:
        return _CACHED_APP, _CACHED_CURRENT_USER_DEPENDENCY
    from app.api.deps import get_current_user  # noqa: PLC0415
    from app.main import app as fastapi_app  # noqa: PLC0415

    _CACHED_APP = fastapi_app
    _CACHED_CURRENT_USER_DEPENDENCY = get_current_user
    return _CACHED_APP, _CACHED_CURRENT_USER_DEPENDENCY


def _resolve_data_sensitivity(*, path: str, protocol: str) -> str:
    if protocol == "websocket" or path.startswith("/ws/"):
        return "relationship_sensitive"
    if path.startswith("/api/billing"):
        return "billing_sensitive"
    if path == "/api/love-map/essentials/heart-profile":
        return "relationship_sensitive"
    if path.startswith("/api/users/me/data"):
        return "relationship_sensitive"
    if path.startswith("/api/journals"):
        return "relationship_sensitive"
    if path.startswith("/api/cards"):
        return "relationship_sensitive"
    if path.startswith("/api/card-decks"):
        return "relationship_sensitive"
    if path.startswith("/api/reports"):
        return "relationship_sensitive"
    if path.startswith("/api/auth") or path.startswith("/api/users"):
        return "account_sensitive"
    if path == "/" or path.startswith("/health"):
        return "operational"
    return "public"


def _resolve_owner_team(*, path: str, tags: list[str], protocol: str) -> str:
    if protocol == "websocket" or path.startswith("/ws/"):
        return "backend-realtime"
    for tag in tags:
        owner = OWNER_BY_TAG.get(tag)
        if owner:
            return owner
    if path == "/" or path.startswith("/health"):
        return "backend-platform"
    return "backend-platform"


def _resolve_runbook_ref(*, path: str, protocol: str) -> str:
    target = path
    if protocol == "websocket" and target == "/ws/{user_id}":
        target = "/ws/"
    for prefix, ref in RUNBOOK_BY_PATH_PREFIX:
        if target.startswith(prefix):
            return ref
    return "docs/p0-execution-protocol.md"


def _resolve_route_metadata(*, path: str, tags: list[str], protocol: str) -> dict[str, str]:
    return {
        "owner_team": _resolve_owner_team(path=path, tags=tags, protocol=protocol),
        "runbook_ref": _resolve_runbook_ref(path=path, protocol=protocol),
        "data_sensitivity": _resolve_data_sensitivity(path=path, protocol=protocol),
    }


def _iter_dependency_calls(dependant: Any) -> Iterable[Any]:
    for dependency in getattr(dependant, "dependencies", []):
        call = getattr(dependency, "call", None)
        if callable(call):
            yield call
        yield from _iter_dependency_calls(dependency)


def _resolve_auth_policy(route: APIRoute, *, current_user_dependency: Any) -> str:
    dependency_calls = set(_iter_dependency_calls(route.dependant))
    return "authenticated" if current_user_dependency in dependency_calls else "public"


def _normalize_http_methods(route: APIRoute) -> list[str]:
    methods = route.methods or set()
    return sorted(method for method in methods if method not in {"HEAD", "OPTIONS"})


def _route_endpoint_name(route: BaseRoute) -> str:
    endpoint = getattr(route, "endpoint", None)
    module = getattr(endpoint, "__module__", "")
    name = getattr(endpoint, "__name__", "")
    if module and name:
        return f"{module}.{name}"
    return str(name or module or "unknown")


def build_inventory_entries(app: FastAPI, *, current_user_dependency: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path in EXCLUDED_HTTP_PATHS:
                continue
            methods = _normalize_http_methods(route)
            if not methods:
                continue
            auth_policy = _resolve_auth_policy(route, current_user_dependency=current_user_dependency)
            endpoint_name = _route_endpoint_name(route)
            tags = sorted(route.tags or [])
            metadata = _resolve_route_metadata(path=route.path, tags=tags, protocol="http")
            for method in methods:
                entries.append(
                    {
                        "protocol": "http",
                        "path": route.path,
                        "method": method,
                        "name": route.name,
                        "tags": tags,
                        "endpoint": endpoint_name,
                        "auth_policy": auth_policy,
                        **metadata,
                    }
                )
            continue

        if isinstance(route, WebSocketRoute):
            metadata = _resolve_route_metadata(path=route.path, tags=[], protocol="websocket")
            entries.append(
                {
                    "protocol": "websocket",
                    "path": route.path,
                    "method": "WEBSOCKET",
                    "name": route.name,
                    "tags": [],
                    "endpoint": _route_endpoint_name(route),
                    "auth_policy": "custom",
                    **metadata,
                }
            )

    entries.sort(key=lambda item: (item["protocol"], item["path"], item["method"]))
    return entries


def validate_inventory(entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for index, entry in enumerate(entries):
        protocol = entry.get("protocol")
        path = entry.get("path")
        method = entry.get("method")
        auth_policy = entry.get("auth_policy")
        owner_team = entry.get("owner_team")
        runbook_ref = entry.get("runbook_ref")
        data_sensitivity = entry.get("data_sensitivity")

        if protocol not in {"http", "websocket"}:
            errors.append(f"entries[{index}].protocol must be http|websocket")
        if not isinstance(path, str) or not path.startswith("/"):
            errors.append(f"entries[{index}].path must be an absolute path")
        if not isinstance(method, str) or not method:
            errors.append(f"entries[{index}].method must be a non-empty string")
        if auth_policy not in {"public", "authenticated", "custom"}:
            errors.append(
                f"entries[{index}].auth_policy must be public|authenticated|custom"
            )
        if not isinstance(owner_team, str) or not owner_team.strip():
            errors.append(f"entries[{index}].owner_team must be a non-empty string")
        if not isinstance(runbook_ref, str) or not runbook_ref.startswith("docs/"):
            errors.append(f"entries[{index}].runbook_ref must be a docs/* path")
        if data_sensitivity not in DATA_SENSITIVITY_VALUES:
            errors.append(
                f"entries[{index}].data_sensitivity must be one of {sorted(DATA_SENSITIVITY_VALUES)}"
            )

        key = (str(protocol), str(path), str(method))
        if key in seen_keys:
            errors.append(f"duplicate route entry: protocol={protocol} path={path} method={method}")
        seen_keys.add(key)

    return errors


def build_inventory_payload(
    *,
    app: FastAPI | None = None,
    current_user_dependency: Any | None = None,
) -> dict[str, Any]:
    if app is None or current_user_dependency is None:
        app, current_user_dependency = _load_runtime_dependencies()
    entries = build_inventory_entries(app, current_user_dependency=current_user_dependency)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "generated_by": GENERATED_BY,
        "entries": entries,
    }


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _check_snapshot(output_path: Path, expected_payload: dict[str, Any]) -> int:
    if not output_path.exists():
        print(f"[api-inventory] missing snapshot: {output_path}", file=sys.stderr)
        return 1

    current_text = output_path.read_text(encoding="utf-8")
    expected_text = _canonical_json(expected_payload)
    if current_text == expected_text:
        print(f"[api-inventory] check ok: {output_path}")
        return 0

    diff = "\n".join(
        difflib.unified_diff(
            current_text.splitlines(),
            expected_text.splitlines(),
            fromfile=str(output_path),
            tofile="generated",
            lineterm="",
        )
    )
    print("[api-inventory] snapshot mismatch:", file=sys.stderr)
    if diff:
        print(diff, file=sys.stderr)
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export/check API inventory snapshot.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Snapshot path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write generated inventory snapshot to --output.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify --output matches generated inventory snapshot.",
    )
    parser.add_argument(
        "--emit-timings",
        action="store_true",
        help="Print timing breakdown for dependency loading and snapshot generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    load_started = time.monotonic()
    app, current_user_dependency = _load_runtime_dependencies()
    load_elapsed = time.monotonic() - load_started

    payload_started = time.monotonic()
    payload = build_inventory_payload(app=app, current_user_dependency=current_user_dependency)
    payload_elapsed = time.monotonic() - payload_started
    entries = payload["entries"]
    validation_errors = validate_inventory(entries)
    if validation_errors:
        print("[api-inventory] validation failed:", file=sys.stderr)
        for item in validation_errors:
            print(f"  - {item}", file=sys.stderr)
        return 1

    output_path: Path = args.output.resolve()
    rendered = _canonical_json(payload)

    if args.write:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"[api-inventory] wrote snapshot: {output_path}")

    if args.check:
        result = _check_snapshot(output_path, payload)
        if args.emit_timings:
            print(
                "[api-inventory] timings "
                f"load_dependencies={load_elapsed:.3f}s "
                f"build_payload={payload_elapsed:.3f}s "
                f"total={time.monotonic() - started:.3f}s"
            )
        return result

    if not args.write:
        print(rendered, end="")
    if args.emit_timings:
        print(
            "[api-inventory] timings "
            f"load_dependencies={load_elapsed:.3f}s "
            f"build_payload={payload_elapsed:.3f}s "
            f"total={time.monotonic() - started:.3f}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
