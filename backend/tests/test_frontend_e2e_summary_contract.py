import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SUMMARY_SCRIPT_PATH = REPO_ROOT / "frontend" / "scripts" / "summarize-e2e-result.mjs"

ALLOWED_RESULTS = {"pass", "fail", "unavailable"}
ALLOWED_CLASSIFICATIONS = {
    "none",
    "pre_e2e_step_failure",
    "missing_browser",
    "browser_download_network",
    "app_unreachable",
    "e2e_process_timeout",
    "cuj_assertion_timeout",
    "test_or_runtime_failure",
}


class FrontendE2ESummaryContractTests(unittest.TestCase):
    def _run_summary_script(self, *, log_content: str, exit_code: str) -> dict:
        node_bin = shutil.which("node")
        if not node_bin:
            self.skipTest("node is required to run summarize-e2e-result.mjs")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            log_path = tmp_path / "e2e.log"
            summary_path = tmp_path / "summary.json"
            log_path.write_text(log_content, encoding="utf-8")

            command = [
                node_bin,
                str(SUMMARY_SCRIPT_PATH),
                "--log-path",
                str(log_path),
                "--exit-code",
                exit_code,
                "--summary-path",
                str(summary_path),
                "--summary-title",
                "Frontend e2e smoke",
            ]
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"summary script failed: stdout={result.stdout}\nstderr={result.stderr}",
            )
            return json.loads(summary_path.read_text(encoding="utf-8"))

    def test_payload_schema_contract(self) -> None:
        payload = self._run_summary_script(
            log_content="Error: getaddrinfo ENOTFOUND cdn.playwright.dev",
            exit_code="1",
        )
        self.assertEqual(
            set(payload.keys()),
            {
                "schema_version",
                "result",
                "exit_code",
                "classification",
                "log_available",
                "next_action",
            },
        )
        self.assertEqual(payload["schema_version"], "v1")
        self.assertIn(payload["result"], ALLOWED_RESULTS)
        self.assertIn(payload["classification"], ALLOWED_CLASSIFICATIONS)
        self.assertIsInstance(payload["log_available"], bool)
        self.assertIsInstance(payload["next_action"], str)
        self.assertIsInstance(payload["exit_code"], int)

    def test_pass_payload_contract(self) -> None:
        payload = self._run_summary_script(
            log_content="all tests passed",
            exit_code="0",
        )
        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(payload["classification"], "none")
        self.assertEqual(payload["exit_code"], 0)

    def test_unavailable_payload_contract(self) -> None:
        payload = self._run_summary_script(
            log_content="missing exit code",
            exit_code="nan",
        )
        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["result"], "unavailable")
        self.assertEqual(payload["classification"], "pre_e2e_step_failure")
        self.assertIsNone(payload["exit_code"])


if __name__ == "__main__":
    unittest.main()
