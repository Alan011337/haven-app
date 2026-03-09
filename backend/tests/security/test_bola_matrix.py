import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ENDPOINT_MATRIX_PATH = REPO_ROOT / "docs" / "security" / "endpoint-authorization-matrix.json"
READ_MATRIX_PATH = REPO_ROOT / "docs" / "security" / "read-authorization-matrix.json"


class BolaMatrixSmokeTests(unittest.TestCase):
    def test_core_write_routes_exist_in_endpoint_matrix(self) -> None:
        payload = json.loads(ENDPOINT_MATRIX_PATH.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        write_keys = {(entry.get("method"), entry.get("path")) for entry in entries if isinstance(entry, dict)}

        required = {
            ("POST", "/api/journals/"),
            ("POST", "/api/cards/respond"),
            ("POST", "/api/card-decks/respond/{session_id}"),
            ("POST", "/api/users/events/cuj"),
            ("POST", "/api/users/events/core-loop"),
            ("POST", "/api/billing/state-change"),
            ("POST", "/api/billing/webhooks/stripe"),
        }
        missing = sorted(required - write_keys)
        self.assertEqual(missing, [], f"missing endpoint authz matrix rows: {missing}")

    def test_core_read_routes_exist_in_read_matrix(self) -> None:
        payload = json.loads(READ_MATRIX_PATH.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        read_keys = {(entry.get("method"), entry.get("path")) for entry in entries if isinstance(entry, dict)}

        required = {
            ("GET", "/api/users/{user_id}"),
            ("GET", "/api/cards/{card_id}/conversation"),
            ("GET", "/api/card-decks/history"),
            ("GET", "/api/billing/reconciliation"),
        }
        missing = sorted(required - read_keys)
        self.assertEqual(missing, [], f"missing read authz matrix rows: {missing}")

    def test_all_matrix_test_refs_exist(self) -> None:
        payload = json.loads(ENDPOINT_MATRIX_PATH.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        missing_paths: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            test_ref = str(entry.get("test_ref") or "").strip()
            if not test_ref:
                continue
            path = REPO_ROOT / test_ref
            if not path.exists():
                missing_paths.append(test_ref)
        self.assertEqual(missing_paths, [], f"missing matrix test files: {missing_paths}")

    def test_path_param_mutating_routes_have_deny_marker(self) -> None:
        payload = json.loads(ENDPOINT_MATRIX_PATH.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        missing: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            method = str(entry.get("method") or "").strip().upper()
            path = str(entry.get("path") or "").strip()
            auth_mode = str(entry.get("auth_mode") or "").strip()
            test_ref = str(entry.get("test_ref") or "").strip()
            if auth_mode != "authenticated":
                continue
            if "{" not in path:
                continue
            if not test_ref:
                missing.append(f"{method} {path} -> missing test_ref")
                continue
            test_path = REPO_ROOT / test_ref
            if not test_path.exists():
                missing.append(f"{method} {path} -> missing file {test_ref}")
                continue
            marker = f"# AUTHZ_DENY_MATRIX: {method} {path}"
            content = test_path.read_text(encoding="utf-8")
            if marker not in content:
                missing.append(f"{method} {path} -> {test_ref}")

        self.assertEqual(missing, [], f"path-param routes missing deny marker: {missing}")


if __name__ == "__main__":
    unittest.main()
