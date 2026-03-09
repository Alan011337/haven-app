import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SCRIPT_PATH = REPO_ROOT / "frontend" / "scripts" / "check-e2e-summary-schema.mjs"


def _valid_payload() -> dict:
    return {
        "schema_version": "v1",
        "result": "fail",
        "exit_code": 1,
        "classification": "browser_download_network",
        "log_available": True,
        "next_action": "Check DNS/network egress to cdn.playwright.dev or pre-seed browser cache.",
    }


class FrontendE2ESummarySchemaGateScriptTests(unittest.TestCase):
    def _run_script(self, payload: dict, *, required_schema_version: str = "v1") -> subprocess.CompletedProcess:
        node_bin = shutil.which("node")
        if not node_bin:
            self.skipTest("node is required to run check-e2e-summary-schema.mjs")

        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            summary_path.write_text(json.dumps(payload), encoding="utf-8")
            command = [
                node_bin,
                str(SCRIPT_PATH),
                "--summary-path",
                str(summary_path),
                "--required-schema-version",
                required_schema_version,
            ]
            return subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )

    def test_passes_valid_payload(self) -> None:
        result = self._run_script(_valid_payload())
        self.assertEqual(result.returncode, 0, msg=f"stderr={result.stderr}\nstdout={result.stdout}")
        self.assertIn("pass", result.stdout)

    def test_fails_when_schema_version_mismatch(self) -> None:
        payload = _valid_payload()
        payload["schema_version"] = "v2"
        result = self._run_script(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema_version mismatch", result.stderr)

    def test_fails_when_required_key_missing(self) -> None:
        payload = _valid_payload()
        payload.pop("classification")
        result = self._run_script(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required key: classification", result.stderr)

    def test_fails_on_invalid_result_value(self) -> None:
        payload = _valid_payload()
        payload["result"] = "degraded"
        result = self._run_script(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid result value", result.stderr)


if __name__ == "__main__":
    unittest.main()
