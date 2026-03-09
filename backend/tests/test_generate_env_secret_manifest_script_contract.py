import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "generate_env_secret_manifest.py"


class GenerateEnvSecretManifestScriptContractTests(unittest.TestCase):
    def test_script_references_expected_sources(self) -> None:
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("docs/ops/env-secrets-manifest.json", text)
        self.assertIn("backend/scripts/check_env.py", text)
        self.assertIn("frontend/scripts/check-env.mjs", text)
        self.assertIn("_extract_backend_optional_keys", text)
        self.assertIn('"backend_optional_documented"', text)
        self.assertIn('"runtime_switches"', text)
        self.assertIn('"sensitive_backend_optional"', text)


if __name__ == "__main__":
    unittest.main()
