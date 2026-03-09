import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

INVENTORY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "export_api_inventory.py"
_SPEC = importlib.util.spec_from_file_location("export_api_inventory", INVENTORY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load inventory script from {INVENTORY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class ApiInventoryContractTests(unittest.TestCase):
    def test_inventory_has_no_duplicate_route_keys(self) -> None:
        payload = _MODULE.build_inventory_payload()
        entries = payload["entries"]
        keys = [
            (entry["protocol"], entry["path"], entry["method"])
            for entry in entries
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_inventory_auth_policy_for_critical_endpoints(self) -> None:
        payload = _MODULE.build_inventory_payload()
        entries = payload["entries"]
        index = {
            (entry["protocol"], entry["path"], entry["method"]): entry
            for entry in entries
        }

        self.assertEqual(
            index[("http", "/api/billing/state-change", "POST")]["auth_policy"],
            "authenticated",
        )
        self.assertEqual(
            index[("http", "/api/billing/state-change", "POST")]["owner_team"],
            "backend-billing",
        )
        self.assertEqual(
            index[("http", "/api/billing/state-change", "POST")]["data_sensitivity"],
            "billing_sensitive",
        )
        self.assertEqual(
            index[("http", "/api/users/me/data", "DELETE")]["auth_policy"],
            "authenticated",
        )
        self.assertEqual(
            index[("http", "/api/users/me/data", "DELETE")]["runbook_ref"],
            "docs/security/data-rights-fire-drill.md",
        )
        self.assertEqual(
            index[("http", "/api/users/me/data", "DELETE")]["data_sensitivity"],
            "relationship_sensitive",
        )
        self.assertEqual(
            index[("http", "/api/billing/webhooks/stripe", "POST")]["auth_policy"],
            "public",
        )
        self.assertEqual(
            index[("http", "/api/billing/webhooks/stripe", "POST")]["owner_team"],
            "backend-billing",
        )

    def test_inventory_includes_owner_runbook_and_sensitivity_contract(self) -> None:
        payload = _MODULE.build_inventory_payload()
        entries = payload["entries"]

        for entry in entries:
            self.assertIsInstance(entry.get("owner_team"), str)
            self.assertTrue(entry["owner_team"])
            self.assertIsInstance(entry.get("runbook_ref"), str)
            self.assertTrue(entry["runbook_ref"].startswith("docs/"))
            self.assertIn(
                entry.get("data_sensitivity"),
                _MODULE.DATA_SENSITIVITY_VALUES,
            )

    def test_inventory_matches_snapshot_file(self) -> None:
        snapshot_path = REPO_ROOT / "docs" / "security" / "api-inventory.json"
        self.assertTrue(snapshot_path.exists(), f"Missing inventory snapshot: {snapshot_path}")

        expected_payload = _MODULE.build_inventory_payload()
        snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot_payload, expected_payload)


if __name__ == "__main__":
    unittest.main()
