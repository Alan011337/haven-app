import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SCRIPT_PATH = REPO_ROOT / "frontend" / "scripts" / "summarize-e2e-result.mjs"


class FrontendE2ESummaryScriptTests(unittest.TestCase):
    def _run_script(
        self,
        *,
        log_content: str,
        exit_code: str = "1",
        with_markdown: bool = False,
    ) -> tuple[dict, str]:
        node_bin = shutil.which("node")
        if not node_bin:
            self.skipTest("node is required to run summarize-e2e-result.mjs")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            log_path = tmp_path / "e2e.log"
            summary_path = tmp_path / "summary.json"
            markdown_path = tmp_path / "summary.md"
            log_path.write_text(log_content, encoding="utf-8")

            command = [
                node_bin,
                str(SCRIPT_PATH),
                "--log-path",
                str(log_path),
                "--exit-code",
                exit_code,
                "--summary-path",
                str(summary_path),
                "--summary-title",
                "Frontend e2e smoke",
            ]
            if with_markdown:
                command.extend(
                    [
                        "--markdown-summary-path",
                        str(markdown_path),
                    ]
                )

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
                msg=f"script failed: stdout={result.stdout}\nstderr={result.stderr}",
            )
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            markdown = (
                markdown_path.read_text(encoding="utf-8")
                if with_markdown and markdown_path.exists()
                else ""
            )
            return payload, markdown

    def test_classifies_missing_browser(self) -> None:
        payload, _ = self._run_script(
            log_content="[playwright-preflight] chromium executable not found.",
            exit_code="1",
        )
        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["result"], "fail")
        self.assertEqual(payload["classification"], "missing_browser")

    def test_classifies_browser_download_network_failure(self) -> None:
        payload, _ = self._run_script(
            log_content="Error: getaddrinfo ENOTFOUND cdn.playwright.dev",
            exit_code="1",
        )
        self.assertEqual(payload["classification"], "browser_download_network")

    def test_classifies_app_unreachable(self) -> None:
        payload, _ = self._run_script(
            log_content="Error: ECONNREFUSED while opening page",
            exit_code="1",
        )
        self.assertEqual(payload["classification"], "app_unreachable")

    def test_classifies_cuj_assertion_timeout(self) -> None:
        payload, _ = self._run_script(
            log_content="Timed out 15000ms waiting for expect(locator).toHaveURL",
            exit_code="1",
        )
        self.assertEqual(payload["classification"], "cuj_assertion_timeout")

    def test_classifies_e2e_process_timeout(self) -> None:
        payload, _ = self._run_script(
            log_content="[e2e-timeout] frontend e2e exceeded 420s; sending SIGTERM.",
            exit_code="124",
        )
        self.assertEqual(payload["classification"], "e2e_process_timeout")

    def test_classifies_generic_runtime_failure(self) -> None:
        payload, _ = self._run_script(
            log_content="AssertionError: expected true to equal false",
            exit_code="1",
        )
        self.assertEqual(payload["classification"], "test_or_runtime_failure")

    def test_pass_result_uses_none_classification(self) -> None:
        payload, _ = self._run_script(
            log_content="all tests passed",
            exit_code="0",
        )
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(payload["classification"], "none")

    def test_unavailable_result_when_exit_code_is_invalid(self) -> None:
        payload, _ = self._run_script(
            log_content="no exit code available",
            exit_code="not-a-number",
        )
        self.assertEqual(payload["result"], "unavailable")
        self.assertEqual(payload["classification"], "pre_e2e_step_failure")

    def test_writes_markdown_summary(self) -> None:
        payload, markdown = self._run_script(
            log_content="Error: getaddrinfo ENOTFOUND cdn.playwright.dev",
            exit_code="1",
            with_markdown=True,
        )
        self.assertEqual(payload["classification"], "browser_download_network")
        self.assertIn("### Frontend e2e smoke", markdown)
        self.assertIn("- classification: `browser_download_network`", markdown)


if __name__ == "__main__":
    unittest.main()
