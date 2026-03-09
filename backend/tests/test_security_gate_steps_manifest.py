import importlib.util
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_security_gate_steps_manifest.py"
MANIFEST_PATH = BACKEND_ROOT / "scripts" / "security_gate_steps_manifest.json"

_SPEC = importlib.util.spec_from_file_location("check_security_gate_steps_manifest", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class SecurityGateStepsManifestTests(unittest.TestCase):
    def test_manifest_exists_and_has_required_keys(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists())
        payload = _MODULE._load_manifest()
        self.assertIn("schema_version", payload)
        self.assertIn("required_fast_steps", payload)
        self.assertIn("required_any_profile_steps", payload)
        self.assertIn("required_shared_contract_steps", payload)
        self.assertIn("required_full_only_steps", payload)
        self.assertIsInstance(payload["required_fast_steps"], list)
        self.assertIsInstance(payload["required_any_profile_steps"], list)
        self.assertIsInstance(payload["required_shared_contract_steps"], list)
        self.assertIsInstance(payload["required_full_only_steps"], list)

    def test_manifest_contract_script_passes(self) -> None:
        exit_code = _MODULE.main()
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
