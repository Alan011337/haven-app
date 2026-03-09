import importlib.util
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_owasp_api_top10_mapping_contract.py"
_SPEC = importlib.util.spec_from_file_location(
    "check_owasp_api_top10_mapping_contract",
    POLICY_SCRIPT_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class OwaspApiTop10MappingContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_owasp_mapping_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_fails_when_alias_missing_canonical_reference(self) -> None:
        alias_path = _MODULE.ALIAS_PATH
        original = alias_path.read_text(encoding="utf-8")
        try:
            alias_path.write_text("alias-without-reference", encoding="utf-8")
            violations = _MODULE.collect_owasp_mapping_contract_violations()
            self.assertTrue(
                any(v.reason == "alias_missing_canonical_ref" for v in violations)
            )
        finally:
            alias_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
