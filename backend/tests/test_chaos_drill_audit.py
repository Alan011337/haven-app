import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_chaos_drill_audit.py"
SPEC = importlib.util.spec_from_file_location("run_chaos_drill_audit", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ChaosDrillAuditTests(unittest.TestCase):
    def test_run_chaos_drill_writes_evidence_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload, json_path, md_path = MODULE.run_chaos_drill(
                evidence_dir=Path(tmp_dir),
                now_utc=datetime(2026, 2, 23, 4, 0, tzinfo=UTC),
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["artifact_kind"], MODULE.ARTIFACT_KIND)
            self.assertEqual(loaded["generated_by"], MODULE.GENERATED_BY)
            self.assertEqual(loaded["contract_mode"], MODULE.CONTRACT_MODE)
            self.assertTrue(loaded["dry_run"])
            self.assertEqual(loaded["checks_total"], len(MODULE.REQUIRED_CHECKS))
            self.assertEqual(payload["checks_total"], len(MODULE.REQUIRED_CHECKS))

    def test_required_drills_and_checks_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload, _, _ = MODULE.run_chaos_drill(
                evidence_dir=Path(tmp_dir),
                now_utc=datetime(2026, 2, 23, 4, 0, tzinfo=UTC),
            )
            self.assertEqual(payload["required_drills"], list(MODULE.REQUIRED_DRILLS))
            self.assertEqual(payload["required_checks"], list(MODULE.REQUIRED_CHECKS))
            self.assertEqual(sorted(item["name"] for item in payload["results"]), sorted(MODULE.REQUIRED_CHECKS))


if __name__ == "__main__":
    unittest.main()
