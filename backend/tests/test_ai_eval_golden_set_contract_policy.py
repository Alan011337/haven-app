import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_ai_eval_golden_set_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_ai_eval_golden_set_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class AIEvalGoldenSetContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_ai_eval_golden_set_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_total_case_count_below_minimum(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["total_cases"] = 99
        violations = _MODULE.collect_ai_eval_golden_set_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("invalid_total_cases_range", reasons)

    def test_policy_rejects_duplicate_case_id(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["case_ids"][1] = payload["case_ids"][0]
        violations = _MODULE.collect_ai_eval_golden_set_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("duplicate_case_id", reasons)

    def test_policy_rejects_case_count_mismatch(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["case_ids"] = payload["case_ids"][:-1]
        violations = _MODULE.collect_ai_eval_golden_set_violations(payload=payload)
        reasons = {violation.reason for violation in violations}
        self.assertIn("case_count_mismatch", reasons)


if __name__ == "__main__":
    unittest.main()
