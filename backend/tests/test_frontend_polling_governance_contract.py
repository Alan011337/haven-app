import importlib.util
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_frontend_polling_governance_contract.py"
SPEC = importlib.util.spec_from_file_location("check_frontend_polling_governance_contract", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)  # type: ignore[arg-type]


class FrontendPollingGovernanceContractTests(unittest.TestCase):
    def test_polling_governance_contract_passes(self) -> None:
        self.assertEqual(MODULE.collect_violations(), [])


if __name__ == "__main__":
    unittest.main()
