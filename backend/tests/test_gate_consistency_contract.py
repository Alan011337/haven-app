import importlib.util
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_gate_consistency_contract.py"
SPEC = importlib.util.spec_from_file_location("check_gate_consistency_contract", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)  # type: ignore[arg-type]


class GateConsistencyContractTests(unittest.TestCase):
    def test_no_contract_violations(self) -> None:
        violations = MODULE.collect_contract_violations()
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
