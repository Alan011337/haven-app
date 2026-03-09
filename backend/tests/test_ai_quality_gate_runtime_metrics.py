from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.services.ai import _is_request_class_quality_gate_red
from app.services.ai_router import ai_router_runtime_metrics


class AIQualityGateRuntimeMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_router_runtime_metrics.reset()
        self._snapshot_attr = "AI_QUALITY_GATE_SNAPSHOT_FILE"
        self._forced_attr = "AI_ROUTER_FORCE_QUALITY_GATE_RED_CLASSES"
        self._snapshot_original = getattr(settings, self._snapshot_attr, "")
        self._forced_original = getattr(settings, self._forced_attr, "")

    def tearDown(self) -> None:
        setattr(settings, self._snapshot_attr, self._snapshot_original)
        setattr(settings, self._forced_attr, self._forced_original)

    def test_quality_gate_red_increments_red_counter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            snapshot_path = Path(td) / "quality.json"
            snapshot_path.write_text(
                json.dumps({"request_class_gate": {"journal_analysis": "red"}}),
                encoding="utf-8",
            )
            setattr(settings, self._snapshot_attr, str(snapshot_path))
            setattr(settings, self._forced_attr, "")
            self.assertTrue(_is_request_class_quality_gate_red("journal_analysis"))
            counters = ai_router_runtime_metrics.snapshot()
            self.assertGreaterEqual(
                int(counters.get("ai_router_quality_gate_red_total_journal_analysis", 0)), 1
            )
            state = ai_router_runtime_metrics.state_snapshot()
            self.assertEqual(state.get("quality_gate_status_journal_analysis"), "red")

    def test_quality_gate_missing_snapshot_increments_missing_counter(self) -> None:
        setattr(settings, self._snapshot_attr, "/tmp/haven-missing-quality-gate.json")
        setattr(settings, self._forced_attr, "")
        self.assertFalse(_is_request_class_quality_gate_red("journal_analysis"))
        counters = ai_router_runtime_metrics.snapshot()
        self.assertGreaterEqual(
            int(counters.get("ai_router_quality_gate_missing_snapshot_total_journal_analysis", 0)),
            1,
        )


if __name__ == "__main__":
    unittest.main()
