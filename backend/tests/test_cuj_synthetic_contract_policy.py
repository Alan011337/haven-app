import importlib.util
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_cuj_synthetic_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_cuj_synthetic_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class CujSyntheticContractTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_cuj_synthetic_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_failure_class_fragment_in_script(self) -> None:
        script_text = (BACKEND_ROOT.parent / "scripts" / "synthetics" / "run_cuj_synthetics.py").read_text(
            encoding="utf-8"
        )
        script_text = script_text.replace('"failure_class"', '"failure_cls"')
        violations = _MODULE.collect_cuj_synthetic_contract_violations(
            synthetic_script_text=script_text
        )
        self.assertTrue(any(v.reason == "missing_synthetic_script_fragment" for v in violations))

    def test_policy_rejects_missing_summary_step_in_workflow(self) -> None:
        workflow_text = (BACKEND_ROOT.parent / ".github" / "workflows" / "cuj-synthetics.yml").read_text(
            encoding="utf-8"
        )
        workflow_text = workflow_text.replace("name: CUJ synthetic summary", "name: CUJ summary")
        violations = _MODULE.collect_cuj_synthetic_contract_violations(
            workflow_text=workflow_text
        )
        self.assertTrue(any(v.reason == "missing_synthetic_workflow_fragment" for v in violations))

    def test_policy_rejects_missing_failure_class_routing_doc(self) -> None:
        alerts_doc = (BACKEND_ROOT.parent / "docs" / "sre" / "alerts.md").read_text(encoding="utf-8")
        alerts_doc = alerts_doc.replace("Failure Class Routing (Synthetic CUJ)", "Routing")
        violations = _MODULE.collect_cuj_synthetic_contract_violations(
            alerts_doc_text=alerts_doc
        )
        self.assertTrue(any(v.reason == "missing_alerts_doc_fragment" for v in violations))


if __name__ == "__main__":
    unittest.main()
