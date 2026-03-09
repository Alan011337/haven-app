import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_ai_quality_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_ai_quality_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class AIQualitySnapshotScriptTests(unittest.TestCase):
    def test_script_writes_snapshot_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "baseline.json"
            current_path = Path(tmpdir) / "current.json"
            output_path = Path(tmpdir) / "snapshot.json"

            base_payload = {
                "schema_compliance_rate": 99.95,
                "hallucination_proxy_rate": 0.02,
                "avg_tokens_per_analysis": 850.0,
                "estimated_cost_usd_per_active_couple": 0.9,
            }
            current_payload = {
                "schema_compliance_rate": 99.92,
                "hallucination_proxy_rate": 0.03,
                "avg_tokens_per_analysis": 900.0,
                "estimated_cost_usd_per_active_couple": 1.1,
            }
            base_path.write_text(json.dumps(base_payload), encoding="utf-8")
            current_path.write_text(json.dumps(current_payload), encoding="utf-8")

            argv = [
                "run_ai_quality_snapshot.py",
                "--baseline",
                str(base_path),
                "--current",
                str(current_path),
                "--output",
                str(output_path),
            ]
            with patch.object(sys, "argv", argv):
                exit_code = _MODULE.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            snapshot = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["artifact_kind"], "ai-quality-snapshot")
            self.assertEqual(snapshot["evaluation"]["result"], "pass")

    def test_script_can_fallback_to_baseline_when_current_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "baseline.json"
            output_path = Path(tmpdir) / "snapshot.json"
            base_payload = {
                "schema_compliance_rate": 99.95,
                "hallucination_proxy_rate": 0.02,
                "avg_tokens_per_analysis": 850.0,
                "estimated_cost_usd_per_active_couple": 0.9,
            }
            base_path.write_text(json.dumps(base_payload), encoding="utf-8")

            argv = [
                "run_ai_quality_snapshot.py",
                "--baseline",
                str(base_path),
                "--allow-missing-current",
                "--output",
                str(output_path),
            ]
            with patch.object(sys, "argv", argv):
                exit_code = _MODULE.main()

            self.assertEqual(exit_code, 0)
            snapshot = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["current_source"], "baseline_fallback")

    def test_script_writes_latest_pointer_when_latest_path_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "baseline.json"
            current_path = Path(tmpdir) / "current.json"
            output_path = Path(tmpdir) / "snapshot-timestamped.json"
            latest_path = Path(tmpdir) / "snapshot-latest.json"

            base_payload = {
                "schema_compliance_rate": 99.95,
                "hallucination_proxy_rate": 0.02,
                "avg_tokens_per_analysis": 850.0,
                "estimated_cost_usd_per_active_couple": 0.9,
            }
            current_payload = {
                "schema_compliance_rate": 99.91,
                "hallucination_proxy_rate": 0.03,
                "avg_tokens_per_analysis": 900.0,
                "estimated_cost_usd_per_active_couple": 1.1,
            }
            base_path.write_text(json.dumps(base_payload), encoding="utf-8")
            current_path.write_text(json.dumps(current_payload), encoding="utf-8")

            argv = [
                "run_ai_quality_snapshot.py",
                "--baseline",
                str(base_path),
                "--current",
                str(current_path),
                "--output",
                str(output_path),
                "--latest-path",
                str(latest_path),
            ]
            with patch.object(sys, "argv", argv):
                exit_code = _MODULE.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertTrue(latest_path.exists())
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))
            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual(output_payload["artifact_kind"], "ai-quality-snapshot")
            self.assertEqual(latest_payload["artifact_kind"], "ai-quality-snapshot")
            self.assertEqual(
                output_payload["evaluation"]["result"],
                latest_payload["evaluation"]["result"],
            )


if __name__ == "__main__":
    unittest.main()
