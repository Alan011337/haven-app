import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import APIRouter, FastAPI

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_endpoint_authorization_matrix.py"
_SPEC = importlib.util.spec_from_file_location("check_endpoint_authorization_matrix", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class EndpointAuthorizationMatrixPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_endpoint_authorization_matrix_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_mutating_route_entry(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.post("/api/test/mutate")
        def create_test_item() -> dict:
            return {"ok": True}

        app.include_router(router)

        matrix_payload = {
            "schema_version": _MODULE.MATRIX_SCHEMA_VERSION,
            "entries": [],
        }
        inventory_payload = {"entries": []}

        violations = _MODULE.collect_endpoint_authorization_matrix_violations(
            app=app,
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )

        self.assertTrue(any(v.reason == "missing_matrix_entry" for v in violations))

    def test_policy_rejects_owner_team_mismatch_with_inventory(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.post("/api/test/mutate")
        def create_test_item() -> dict:
            return {"ok": True}

        app.include_router(router)

        matrix_payload = {
            "schema_version": _MODULE.MATRIX_SCHEMA_VERSION,
            "entries": [
                {
                    "method": "POST",
                    "path": "/api/test/mutate",
                    "auth_mode": "authenticated",
                    "subject_scope": "current_user",
                    "owner_team": "backend-core",
                    "test_ref": "backend/tests/test_endpoint_authorization_matrix_policy.py",
                }
            ],
        }
        inventory_payload = {
            "entries": [
                {
                    "protocol": "http",
                    "method": "POST",
                    "path": "/api/test/mutate",
                    "owner_team": "backend-security",
                }
            ]
        }

        violations = _MODULE.collect_endpoint_authorization_matrix_violations(
            app=app,
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )

        self.assertTrue(any(v.reason == "owner_team_mismatch" for v in violations))

    def test_policy_rejects_missing_test_ref_marker(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.post("/api/test/mutate")
        def create_test_item() -> dict:
            return {"ok": True}

        app.include_router(router)

        matrix_payload = {
            "schema_version": _MODULE.MATRIX_SCHEMA_VERSION,
            "entries": [
                {
                    "method": "POST",
                    "path": "/api/test/mutate",
                    "auth_mode": "authenticated",
                    "subject_scope": "current_user",
                    "owner_team": "backend-core",
                    "test_ref": "tests/fake_authz_file.py",
                }
            ],
        }
        inventory_payload = {
            "entries": [
                {
                    "protocol": "http",
                    "method": "POST",
                    "path": "/api/test/mutate",
                    "owner_team": "backend-core",
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            fake_test_ref = repo_root / "tests" / "fake_authz_file.py"
            fake_test_ref.parent.mkdir(parents=True, exist_ok=True)
            fake_test_ref.write_text("# no authz marker here\n", encoding="utf-8")

            violations = _MODULE.collect_endpoint_authorization_matrix_violations(
                app=app,
                matrix_payload=matrix_payload,
                inventory_payload=inventory_payload,
                repo_root=repo_root,
            )

        self.assertTrue(any(v.reason == "missing_test_ref_marker" for v in violations))

    def test_policy_rejects_missing_test_ref_deny_marker_for_path_parameter_route(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.delete("/api/test/items/{item_id}")
        def delete_test_item(item_id: str) -> dict:
            return {"ok": True, "item_id": item_id}

        app.include_router(router)

        matrix_payload = {
            "schema_version": _MODULE.MATRIX_SCHEMA_VERSION,
            "entries": [
                {
                    "method": "DELETE",
                    "path": "/api/test/items/{item_id}",
                    "auth_mode": "authenticated",
                    "subject_scope": "resource_owner",
                    "owner_team": "backend-core",
                    "test_ref": "tests/fake_authz_file.py",
                }
            ],
        }
        inventory_payload = {
            "entries": [
                {
                    "protocol": "http",
                    "method": "DELETE",
                    "path": "/api/test/items/{item_id}",
                    "owner_team": "backend-core",
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            fake_test_ref = repo_root / "tests" / "fake_authz_file.py"
            fake_test_ref.parent.mkdir(parents=True, exist_ok=True)
            fake_test_ref.write_text(
                "# AUTHZ_MATRIX: DELETE /api/test/items/{item_id}\n",
                encoding="utf-8",
            )

            violations = _MODULE.collect_endpoint_authorization_matrix_violations(
                app=app,
                matrix_payload=matrix_payload,
                inventory_payload=inventory_payload,
                repo_root=repo_root,
            )

        self.assertTrue(any(v.reason == "missing_test_ref_deny_marker" for v in violations))

    def test_policy_requires_explicit_exempt_idempotency_policy_for_exempt_route(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.post("/api/auth/token")
        def issue_token() -> dict:
            return {"ok": True}

        app.include_router(router)

        matrix_payload = {
            "schema_version": _MODULE.MATRIX_SCHEMA_VERSION,
            "entries": [
                {
                    "method": "POST",
                    "path": "/api/auth/token",
                    "auth_mode": "public",
                    "subject_scope": "credential_owner",
                    "owner_team": "backend-auth",
                    "test_ref": "backend/tests/test_auth_token_endpoint_security.py",
                }
            ],
        }
        inventory_payload = {
            "entries": [
                {
                    "protocol": "http",
                    "method": "POST",
                    "path": "/api/auth/token",
                    "owner_team": "backend-auth",
                }
            ]
        }

        violations = _MODULE.collect_endpoint_authorization_matrix_violations(
            app=app,
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )
        self.assertTrue(any(v.reason == "missing_exempt_idempotency_policy" for v in violations))

    def test_policy_rejects_exempt_idempotency_policy_on_non_exempt_route(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.post("/api/test/mutate")
        def create_test_item() -> dict:
            return {"ok": True}

        app.include_router(router)

        matrix_payload = {
            "schema_version": _MODULE.MATRIX_SCHEMA_VERSION,
            "entries": [
                {
                    "method": "POST",
                    "path": "/api/test/mutate",
                    "auth_mode": "authenticated",
                    "subject_scope": "current_user",
                    "owner_team": "backend-core",
                    "idempotency_policy": "exempt",
                    "test_ref": "backend/tests/test_endpoint_authorization_matrix_policy.py",
                }
            ],
        }
        inventory_payload = {
            "entries": [
                {
                    "protocol": "http",
                    "method": "POST",
                    "path": "/api/test/mutate",
                    "owner_team": "backend-core",
                }
            ]
        }

        violations = _MODULE.collect_endpoint_authorization_matrix_violations(
            app=app,
            matrix_payload=matrix_payload,
            inventory_payload=inventory_payload,
        )
        self.assertTrue(any(v.reason == "unexpected_exempt_idempotency_policy" for v in violations))


if __name__ == "__main__":
    unittest.main()
