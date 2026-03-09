import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_ai_eval_scenario_matrix_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_ai_eval_scenario_matrix_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class AiEvalScenarioMatrixSnapshotScriptTests(unittest.TestCase):
    def test_build_snapshot_passes_for_current_policy(self) -> None:
        matrix = json.loads(_MODULE.MATRIX_PATH.read_text(encoding="utf-8"))
        snapshot = _MODULE._build_snapshot(matrix=matrix)
        self.assertEqual(snapshot["result"], "pass")
        self.assertEqual(snapshot["reasons"], [])
        self.assertGreaterEqual(snapshot["meta"]["scenario_count"], 6)

    def test_snapshot_degraded_when_required_stage_missing(self) -> None:
        matrix = json.loads(_MODULE.MATRIX_PATH.read_text(encoding="utf-8"))
        matrix["scenarios"] = [item for item in matrix["scenarios"] if item.get("cuj_stage") != "unlock"]
        snapshot = _MODULE._build_snapshot(matrix=matrix)
        self.assertEqual(snapshot["result"], "degraded")
        self.assertIn("missing_required_cuj_stage", snapshot["reasons"])
        self.assertIn("unlock", snapshot["meta"]["missing_cuj_stages"])

    def test_main_writes_snapshot_and_returns_zero_when_allow_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            matrix_path = Path(tmp_dir) / "matrix.json"
            output_path = Path(tmp_dir) / "snapshot.json"
            matrix = json.loads(_MODULE.MATRIX_PATH.read_text(encoding="utf-8"))
            matrix["scenarios"] = []
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

            exit_code = _MODULE.main(
                [
                    "--matrix",
                    str(matrix_path),
                    "--output",
                    str(output_path),
                    "--allow-degraded",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "degraded")


if __name__ == "__main__":
    unittest.main()
