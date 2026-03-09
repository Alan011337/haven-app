import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_billing_grace_account_hold_policy_contract.py"
_SPEC = importlib.util.spec_from_file_location(
    "check_billing_grace_account_hold_policy_contract", POLICY_SCRIPT_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class BillingGraceAccountHoldPolicyContractTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_billing_grace_policy_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_provider(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["providers"].pop("google_play", None)
        violations = _MODULE.collect_billing_grace_policy_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_provider_policy" for v in violations))

    def test_policy_rejects_invalid_account_hold_state(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["providers"]["app_store"]["account_hold_state"] = "PAST_DUE"
        violations = _MODULE.collect_billing_grace_policy_violations(payload=payload)
        self.assertTrue(any(v.reason == "invalid_account_hold_state" for v in violations))

    def test_policy_rejects_missing_router_marker(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["references"]["billing_router"] = "backend/tests/test_billing_grace_account_hold_policy_contract.py"
        violations = _MODULE.collect_billing_grace_policy_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_router_marker" for v in violations))


if __name__ == "__main__":
    unittest.main()
