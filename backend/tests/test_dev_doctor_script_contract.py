import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "dev-doctor.sh"


class DevDoctorScriptContractTests(unittest.TestCase):
    def test_dev_doctor_script_exists_and_checks_core_prerequisites(self) -> None:
        self.assertTrue(SCRIPT_PATH.exists(), "scripts/dev-doctor.sh must exist")
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("check-worktree-materialization.py", text)
        self.assertIn("backend/scripts/check_env.py", text)
        self.assertIn("frontend", text)
        self.assertIn("check:env", text)


if __name__ == "__main__":
    unittest.main()

