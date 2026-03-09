from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "build_gate_orchestration_summary.py"

_SPEC = importlib.util.spec_from_file_location("build_gate_orchestration_summary", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class GateOrchestrationSummaryScriptTests(unittest.TestCase):
    def test_main_builds_pass_summary_with_optional_missing_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            required_summary = tmp / "required.json"
            required_summary.write_text(
                json.dumps({"result": "pass", "reasons": []}),
                encoding="utf-8",
            )
            output = tmp / "out.json"
            rc = _MODULE.main(
                [
                    "--mode",
                    "release-local",
                    "--output",
                    str(output),
                    "--component",
                    f"security,{required_summary},required",
                    "--component",
                    f"e2e,{tmp / 'missing-e2e.json'},optional",
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_result"], "pass")
            self.assertEqual(len(payload["components"]), 2)

    def test_main_marks_fail_when_component_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            broken_summary = tmp / "broken.json"
            broken_summary.write_text("{not-json}", encoding="utf-8")
            output = tmp / "out.json"
            rc = _MODULE.main(
                [
                    "--output",
                    str(output),
                    "--component",
                    f"security,{broken_summary},required",
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_result"], "fail")

    def test_main_require_pass_returns_non_zero_for_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = tmp / "out.json"
            rc = _MODULE.main(
                [
                    "--output",
                    str(output),
                    "--require-pass",
                    "--component",
                    f"required_missing,{tmp / 'missing.json'},required",
                ]
            )
            self.assertEqual(rc, 1)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_result"], "degraded")


if __name__ == "__main__":
    unittest.main()
