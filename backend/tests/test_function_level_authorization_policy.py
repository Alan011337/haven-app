import importlib.util
import sys
import unittest
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_function_level_authorization.py"
_SPEC = importlib.util.spec_from_file_location("check_function_level_authorization", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def get_current_user_stub() -> dict:
    return {"id": "u1"}


def require_admin_user(current_user: dict = Depends(get_current_user_stub)) -> dict:
    return current_user


class FunctionLevelAuthorizationPolicyTests(unittest.TestCase):
    def test_policy_passes_when_no_privileged_routes_exist(self) -> None:
        app = FastAPI()
        router = APIRouter()

        @router.get("/api/users/me")
        def read_me() -> dict:
            return {"ok": True}

        app.include_router(router)
        violations = _MODULE.collect_function_level_authz_violations(app)
        self.assertEqual(violations, [])

    def test_policy_rejects_privileged_path_without_admin_guard(self) -> None:
        app = FastAPI()
        router = APIRouter(prefix="/api/admin")

        @router.get("/users")
        def admin_list_users() -> dict:
            return {"ok": True}

        app.include_router(router)
        violations = _MODULE.collect_function_level_authz_violations(app)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, "/api/admin/users")
        self.assertEqual(violations[0].reason, "missing_admin_guard")

    def test_policy_rejects_privileged_tag_without_admin_guard(self) -> None:
        app = FastAPI()
        router = APIRouter(tags=["admin"])

        @router.post("/api/users/promote")
        def promote_user() -> dict:
            return {"ok": True}

        app.include_router(router)
        violations = _MODULE.collect_function_level_authz_violations(app)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, "/api/users/promote")
        self.assertEqual(violations[0].reason, "missing_admin_guard")

    def test_policy_accepts_privileged_route_with_admin_guard(self) -> None:
        app = FastAPI()
        router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin_user)])

        @router.delete("/users/{user_id}")
        def admin_delete_user(user_id: str) -> dict:
            return {"id": user_id}

        app.include_router(router)
        violations = _MODULE.collect_function_level_authz_violations(app)
        self.assertEqual(violations, [])

    def test_policy_handles_callable_dependency_without_name_attribute(self) -> None:
        app = FastAPI()
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
        router = APIRouter(
            prefix="/api/admin",
            dependencies=[Depends(require_admin_user), Depends(oauth2_scheme)],
        )

        @router.post("/sessions/revoke")
        def revoke_sessions() -> dict:
            return {"ok": True}

        app.include_router(router)
        violations = _MODULE.collect_function_level_authz_violations(app)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
