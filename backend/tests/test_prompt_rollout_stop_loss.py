"""Tests for AI-OPS-01: prompt rollout stop-loss guardrails."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
_SCRIPT_PATH = _SCRIPT_DIR / "check_prompt_rollout_stop_loss.py"

_spec = importlib.util.spec_from_file_location("check_prompt_rollout_stop_loss", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

check_policy = _mod.check_policy
REQUIRED_GUARDRAILS = _mod.REQUIRED_GUARDRAILS
REQUIRED_REFERENCES = _mod.REQUIRED_REFERENCES
PROMOTION_GATE_FIELDS = _mod.PROMOTION_GATE_FIELDS


class TestPromptRolloutStopLoss:
    def test_policy_passes_validation(self) -> None:
        errors = check_policy()
        assert errors == [], f"policy validation errors: {errors}"

    def test_required_guardrails_defined(self) -> None:
        assert "rollback_on_slo_degrade" in REQUIRED_GUARDRAILS
        assert "rollback_on_safety_regression" in REQUIRED_GUARDRAILS
        assert "rollback_on_prompt_abuse_spike" in REQUIRED_GUARDRAILS

    def test_required_references_defined(self) -> None:
        assert "canary_guard_script" in REQUIRED_REFERENCES
        assert "canary_workflow" in REQUIRED_REFERENCES
        assert "safety_tests" in REQUIRED_REFERENCES

    def test_promotion_gate_fields_defined(self) -> None:
        assert "health_slo_required" in PROMOTION_GATE_FIELDS
        assert "safety_regression_required" in PROMOTION_GATE_FIELDS
        assert "max_allowed_burn_rate" in PROMOTION_GATE_FIELDS


class TestMainEntrypoint:
    def test_main_exits_zero(self) -> None:
        result = _mod.main()
        assert result == 0
