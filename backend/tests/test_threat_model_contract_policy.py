import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_threat_model_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_threat_model_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class ThreatModelContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_threat_model_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_invalid_stride_label(self) -> None:
        payload = json.loads(_MODULE.THREAT_MODEL_PATH.read_text(encoding="utf-8"))
        payload["threats"][0]["stride"] = "invalid_stride"
        violations = _MODULE.collect_threat_model_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "invalid_stride_label" for v in violations))

    def test_policy_rejects_missing_control_reference_file(self) -> None:
        payload = json.loads(_MODULE.THREAT_MODEL_PATH.read_text(encoding="utf-8"))
        payload["control_references"]["bad"] = "docs/security/not-found.json"
        violations = _MODULE.collect_threat_model_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_reference_file" for v in violations))


if __name__ == "__main__":
    unittest.main()
