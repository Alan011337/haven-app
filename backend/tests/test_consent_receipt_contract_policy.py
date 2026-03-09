import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_consent_receipt_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_consent_receipt_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class ConsentReceiptContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_consent_receipt_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_invalid_policy_version(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["policy_versions"]["terms_version"] = "1.0"
        violations = _MODULE.collect_consent_receipt_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "invalid_policy_version" for v in violations))

    def test_policy_rejects_missing_evidence_path(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["consent_events"][0]["evidence_path"] = "frontend/src/app/definitely-missing-file.tsx"
        violations = _MODULE.collect_consent_receipt_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_evidence_path_file" for v in violations))


if __name__ == "__main__":
    unittest.main()
