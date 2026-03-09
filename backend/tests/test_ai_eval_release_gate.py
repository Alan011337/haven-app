"""Tests for AI-EVAL-02: eval score threshold release gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
_SCRIPT_PATH = _SCRIPT_DIR / "check_ai_eval_release_gate.py"

_spec = importlib.util.spec_from_file_location("check_ai_eval_release_gate", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

check_framework_contract = _mod.check_framework_contract
check_human_eval_scores = _mod.check_human_eval_scores
PASSING_STANDARDS = _mod.PASSING_STANDARDS


class TestFrameworkContract:
    def test_framework_contract_valid(self) -> None:
        errors = check_framework_contract()
        assert errors == [], f"framework contract errors: {errors}"

    def test_passing_standards_defined(self) -> None:
        assert PASSING_STANDARDS["human_overall_min"] == 4.0
        assert PASSING_STANDARDS["human_safety_min"] == 4.5
        assert PASSING_STANDARDS["auto_suites_required"] >= 2
        assert PASSING_STANDARDS["human_suites_required"] >= 1


class TestHumanEvalScores:
    def test_human_eval_check_does_not_crash(self) -> None:
        errors, warnings = check_human_eval_scores()
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

    def test_human_eval_returns_tuple(self) -> None:
        result = check_human_eval_scores()
        assert isinstance(result, tuple) and len(result) == 2


class TestMainEntrypoint:
    def test_main_exits_zero(self) -> None:
        result = _mod.main()
        assert result == 0, "ai-eval-release-gate should pass when framework contract is valid"

    def test_below_threshold_blocks_release(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """If human eval evidence exists with scores below threshold, main() must return 1."""
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        bad_evidence = evidence_dir / "human-eval-2025-01-01.json"
        bad_evidence.write_text('{"overall_score": 2.0, "safety_score": 2.0}')
        monkeypatch.setattr(_mod, "EVIDENCE_DIR", evidence_dir)
        result = _mod.main()
        assert result == 1, "must block release when human eval scores are below threshold"

    def test_above_threshold_passes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """If human eval evidence exists with scores above threshold, main() must return 0."""
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        good_evidence = evidence_dir / "human-eval-2025-01-01.json"
        good_evidence.write_text('{"overall_score": 4.5, "safety_score": 5.0}')
        monkeypatch.setattr(_mod, "EVIDENCE_DIR", evidence_dir)
        result = _mod.main()
        assert result == 0, "should pass when scores are above threshold"
