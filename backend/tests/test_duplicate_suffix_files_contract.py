import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_duplicate_suffix_files.py"


class DuplicateSuffixFilesContractTests(unittest.TestCase):
    def test_script_enforces_suffix_pattern(self) -> None:
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("git", text)
        self.assertIn("ls-files", text)
        self.assertIn("--others", text)
        self.assertIn("--exclude-standard", text)
        self.assertIn("duplicate_suffix_file", text)
        self.assertIn(" 2", text)


if __name__ == "__main__":
    unittest.main()
