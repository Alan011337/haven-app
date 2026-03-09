import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_encryption_posture_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_encryption_posture_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class EncryptionPostureContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_encryption_posture_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_tls_requirement(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["transport_security"]["tls_required"] = False
        violations = _MODULE.collect_encryption_posture_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_transport_requirement" for v in violations))

    def test_policy_rejects_hsts_age_too_small(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["transport_security"]["hsts_min_max_age_seconds"] = 100
        violations = _MODULE.collect_encryption_posture_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "invalid_hsts_min_age" for v in violations))

    def test_policy_rejects_missing_field_level_encryption_requirement(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["data_at_rest"]["field_level_encryption_required"] = False
        violations = _MODULE.collect_encryption_posture_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_at_rest_requirement" for v in violations))


if __name__ == "__main__":
    unittest.main()
