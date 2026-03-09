"""CP-02: Tests for admin least-privilege enforcement contract."""
from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def test_config_has_cs_admin_write_emails():
    config_source = (BACKEND_ROOT / "app" / "core" / "config.py").read_text()
    settings_impl_source = (BACKEND_ROOT / "app" / "core" / "_settings_impl.py").read_text()
    assert "CS_ADMIN_WRITE_EMAILS" in config_source or "CS_ADMIN_WRITE_EMAILS" in settings_impl_source


def test_deps_has_require_admin_write():
    source = (BACKEND_ROOT / "app" / "api" / "deps.py").read_text()
    assert "require_admin_write" in source
    assert "CurrentAdminWriteUser" in source


def test_admin_unbind_uses_write_user():
    source = (BACKEND_ROOT / "app" / "api" / "routers" / "admin.py").read_text()
    # The unbind endpoint should use CurrentAdminWriteUser
    assert "CurrentAdminWriteUser" in source

    # Parse AST and verify post endpoints use write user
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr == "post":
                    func_source = ast.get_source_segment(source, node)
                    assert func_source is not None
                    assert "CurrentAdminWriteUser" in func_source, (
                        f"POST endpoint {node.name} should use CurrentAdminWriteUser"
                    )


def test_admin_read_endpoints_use_base_admin():
    source = (BACKEND_ROOT / "app" / "api" / "routers" / "admin.py").read_text()
    # GET endpoints should use CurrentAdminUser (read-only)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr == "get":
                    func_source = ast.get_source_segment(source, node)
                    assert func_source is not None
                    assert "CurrentAdminUser" in func_source, (
                        f"GET endpoint {node.name} should use CurrentAdminUser"
                    )


def test_admin_router_has_base_dependency():
    source = (BACKEND_ROOT / "app" / "api" / "routers" / "admin.py").read_text()
    assert "require_admin_user" in source


def test_check_admin_least_privilege_script_passes():
    import subprocess
    result = subprocess.run(
        ["python3", "scripts/check_admin_least_privilege.py"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"
