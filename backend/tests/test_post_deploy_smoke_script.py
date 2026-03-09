from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_post_deploy_smoke.py"

class PostDeploySmokeScriptTests(unittest.TestCase):
    @staticmethod
    def _load_script_module():
        spec = importlib.util.spec_from_file_location("run_post_deploy_smoke", SCRIPT_PATH)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive path
            raise RuntimeError("unable to load run_post_deploy_smoke module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_fails_when_base_url_unreachable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "summary.json"
            proc = self._run("--base-url", "http://127.0.0.1:9", "--output", str(output))
            self.assertNotEqual(proc.returncode, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "fail")

    def test_passes_when_health_and_domains_respond(self) -> None:
        module = self._load_script_module()

        def _mock_request_json(*, path: str, method: str, **_kwargs):
            if path == "/health":
                return 200, {"status": "ok"}
            if path == "/health/slo":
                return (
                    200,
                    {
                        "sli": {
                            "notification_runtime": {"status": "ok"},
                            "dynamic_content_runtime": {"status": "ok"},
                        },
                        "checks": {"notification_outbox_depth": {"status": "ok"}},
                    },
                )
            if method.upper() == "POST":
                return 422, {"detail": "validation"}
            return 401, {"detail": "unauthorized"}

        with tempfile.TemporaryDirectory() as td:
            inventory_path = Path(td) / "inventory.json"
            output = Path(td) / "summary.json"
            inventory_path.write_text(
                json.dumps(
                    {
                        "artifact_kind": "api-inventory",
                        "schema_version": "v1",
                        "entries": [
                            {"method": "POST", "path": "/api/auth/token"},
                            {"method": "GET", "path": "/api/journals"},
                            {"method": "GET", "path": "/api/cards"},
                            {"method": "GET", "path": "/api/memory/timeline"},
                            {"method": "GET", "path": "/api/notifications"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(module, "_request_json", side_effect=_mock_request_json):
                rc = module.main(
                    [
                        "--base-url",
                        "http://127.0.0.1:9999",
                        "--inventory",
                        str(inventory_path),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")
            self.assertEqual(len(payload.get("failures", [])), 0)


if __name__ == "__main__":
    unittest.main()
