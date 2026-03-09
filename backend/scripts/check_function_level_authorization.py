#!/usr/bin/env python3
"""Policy-as-code checks for function-level authorization on privileged routes."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app as fastapi_app  # noqa: E402

PRIVILEGED_PATH_PREFIXES = (
    "/api/admin",
    "/api/ops",
    "/api/internal",
)
PRIVILEGED_TAGS = frozenset({"admin", "ops", "internal"})
ADMIN_GUARD_NAMES = frozenset(
    {
        "require_admin_user",
        "require_operator_user",
        "require_internal_operator",
    }
)
EXCLUDED_PATHS = frozenset({"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"})


@dataclass(frozen=True)
class FunctionAuthzViolation:
    path: str
    methods: tuple[str, ...]
    reason: str
    details: str


def _iter_dependency_calls(dependant: Any) -> Iterable[Callable[..., Any]]:
    for dependency in getattr(dependant, "dependencies", []):
        call = getattr(dependency, "call", None)
        if callable(call):
            yield call
        yield from _iter_dependency_calls(dependency)


def _resolve_call_name(call: Callable[..., Any]) -> str:
    name = getattr(call, "__name__", "")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return call.__class__.__name__


def _method_list(route: APIRoute) -> tuple[str, ...]:
    methods = route.methods or set()
    normalized = sorted(method for method in methods if method not in {"HEAD", "OPTIONS"})
    return tuple(normalized)


def _is_privileged_route(route: APIRoute) -> bool:
    if route.path in EXCLUDED_PATHS:
        return False
    if any(route.path.startswith(prefix) for prefix in PRIVILEGED_PATH_PREFIXES):
        return True
    route_tags = {str(tag).strip().lower() for tag in (route.tags or [])}
    return bool(route_tags & PRIVILEGED_TAGS)


def collect_function_level_authz_violations(
    app: FastAPI = fastapi_app,
) -> list[FunctionAuthzViolation]:
    violations: list[FunctionAuthzViolation] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not _is_privileged_route(route):
            continue

        methods = _method_list(route)
        if not methods:
            continue

        call_names = {_resolve_call_name(call) for call in _iter_dependency_calls(route.dependant)}
        admin_guards = sorted(name for name in call_names if name in ADMIN_GUARD_NAMES)

        if not admin_guards:
            violations.append(
                FunctionAuthzViolation(
                    path=route.path,
                    methods=methods,
                    reason="missing_admin_guard",
                    details=(
                        "Privileged route must depend on one of "
                        f"{sorted(ADMIN_GUARD_NAMES)}."
                    ),
                )
            )

    return violations


def run_policy_check(app: FastAPI = fastapi_app) -> int:
    violations = collect_function_level_authz_violations(app)
    if not violations:
        print("[function-authz] ok: privileged route policy satisfied")
        return 0

    print("[function-authz] failed:", file=sys.stderr)
    for item in violations:
        print(
            f"  - path={item.path} methods={list(item.methods)} reason={item.reason} details={item.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
