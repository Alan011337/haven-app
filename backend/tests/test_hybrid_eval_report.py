"""Tests for EVAL-05: hybrid eval report generation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
_SCRIPT_PATH = _SCRIPT_DIR / "run_hybrid_eval_report.py"

_spec = importlib.util.spec_from_file_location("run_hybrid_eval_report", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

generate_report = _mod.generate_report


class TestHybridEvalReport:
    def test_report_has_required_fields(self) -> None:
        report = generate_report()
        assert report["artifact_kind"] == "hybrid-eval-report"
        assert report["schema_version"] == "1.0.0"
        assert "generated_at" in report
        assert "auto_evaluation" in report
        assert "human_evaluation" in report
        assert "overall_status" in report
        assert "release_ready" in report

    def test_auto_section_has_golden_set(self) -> None:
        report = generate_report()
        auto = report["auto_evaluation"]
        assert "golden_set" in auto
        assert "available" in auto["golden_set"]

    def test_human_section_structure(self) -> None:
        report = generate_report()
        human = report["human_evaluation"]
        assert "available" in human
        assert "overall_score" in human
        assert "safety_score" in human

    def test_main_produces_output(self, tmp_path: Path) -> None:
        output = tmp_path / "report.json"
        exit_code = _mod.main(["--output", str(output)])
        assert isinstance(exit_code, int)
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["artifact_kind"] == "hybrid-eval-report"
