#!/usr/bin/env python3
"""CP-02: Validate admin least-privilege runtime contract.

Checks:
1. CS_ADMIN_WRITE_EMAILS config exists in Settings
2. require_admin_write dependency exists in deps.py
3. Write-level admin endpoints use CurrentAdminWriteUser (not CurrentAdminUser)
4. All admin endpoints are protected by require_admin_user base dependency
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"

FAILURES: list[str] = []


def _check_config_has_write_emails() -> None:
    config_path = BACKEND_ROOT / "app" / "core" / "config.py"
    settings_impl_path = BACKEND_ROOT / "app" / "core" / "_settings_impl.py"
    config_source = config_path.read_text()
    settings_impl_source = settings_impl_path.read_text()

    if "CS_ADMIN_WRITE_EMAILS" not in config_source and "CS_ADMIN_WRITE_EMAILS" not in settings_impl_source:
        FAILURES.append("core settings missing CS_ADMIN_WRITE_EMAILS setting")


def _check_deps_has_write_dependency() -> None:
    deps_path = BACKEND_ROOT / "app" / "api" / "deps.py"
    source = deps_path.read_text()
    for required in ("require_admin_write", "CurrentAdminWriteUser"):
        if required not in source:
            FAILURES.append(f"deps.py missing {required}")


def _check_admin_write_endpoints() -> None:
    admin_path = BACKEND_ROOT / "app" / "api" / "routers" / "admin.py"
    source = admin_path.read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        # Find functions with POST decorator (write endpoints)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                attr_name = decorator.func.attr
                if attr_name == "post":
                    # Verify the function uses CurrentAdminWriteUser
                    func_source = ast.get_source_segment(source, node)
                    if func_source and "CurrentAdminWriteUser" not in func_source:
                        FAILURES.append(
                            f"admin.py:{node.name} is POST but uses CurrentAdminUser "
                            f"instead of CurrentAdminWriteUser"
                        )


def _check_base_dependency_on_router() -> None:
    admin_path = BACKEND_ROOT / "app" / "api" / "routers" / "admin.py"
    source = admin_path.read_text()
    if "require_admin_user" not in source:
        FAILURES.append("admin.py missing require_admin_user base dependency on router")


def main() -> int:
    _check_config_has_write_emails()
    _check_deps_has_write_dependency()
    _check_admin_write_endpoints()
    _check_base_dependency_on_router()

    if FAILURES:
        print("CP-02 admin least-privilege contract FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("CP-02 admin least-privilege contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
