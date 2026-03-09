from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateNoiseContractTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=BACKEND_ROOT,
            text=True,
            capture_output=True,
        )

    def test_fail_on_required_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            orchestration = Path(td) / "orchestration.json"
            output = Path(td) / "noise.json"
            orchestration.write_text(
                json.dumps(
                    {
                        "components": [
                            {"name": "required_component", "required": True, "status": "skipped"},
                            {"name": "optional_component", "required": False, "status": "skipped"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            proc = self._run(
                "scripts/summarize_release_gate_noise.py",
                "--orchestration-summary",
                str(orchestration),
                "--output",
                str(output),
                "--fail-on-required-skipped",
            )
            self.assertEqual(proc.returncode, 1, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "fail")
            self.assertIn("required_components_skipped", payload["reasons"])


if __name__ == "__main__":
    unittest.main()
