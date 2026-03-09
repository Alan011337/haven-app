import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_ai_eval_scenario_matrix_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_ai_eval_scenario_matrix_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class AiEvalScenarioMatrixContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_ai_eval_scenario_matrix_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_required_cuj_stage(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["scenarios"] = [item for item in payload["scenarios"] if item.get("cuj_stage") != "unlock"]
        violations = _MODULE.collect_ai_eval_scenario_matrix_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_required_cuj_stage" for v in violations))

    def test_policy_rejects_missing_test_ref_file(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["scenarios"][0]["automated_test_refs"] = ["backend/tests/not-found.py"]
        violations = _MODULE.collect_ai_eval_scenario_matrix_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_test_ref_file" for v in violations))


if __name__ == "__main__":
    unittest.main()
