from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run-test-profile.sh"
REQUIREMENTS_DEV_PATH = BACKEND_ROOT / "requirements-dev.txt"


def test_run_test_profile_script_exists() -> None:
    assert SCRIPT_PATH.exists()
    assert SCRIPT_PATH.stat().st_mode & 0o111, "run-test-profile.sh must be executable"


def test_run_test_profile_contains_required_profiles() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    for profile in ("smoke", "fast", "runtime", "unit", "contract", "safety", "full"):
        assert profile in source, f"Missing profile branch: {profile}"


def test_run_test_profile_fast_profile_covers_runtime_contracts() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "tests/test_health_endpoint.py" in source
    assert "tests/test_notification_outbox.py" in source
    assert "tests/test_billing_edge_policy_contract.py" in source
    assert "tests/test_event_tracking_privacy_contract.py" in source
    assert "tests/test_feature_flag_governance_contract.py" in source
    assert "tests/test_frontend_idempotency_helper_contract.py" in source
    assert "tests/test_frontend_timeline_loadmore_guard_contract.py" in source
    assert "scripts/pytest_guard.py" in source


def test_run_test_profile_smoke_profile_targets_hot_paths() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "smoke)" in source
    assert "ruff check . --select F821,F841,E9" in source
    assert "tests/test_ai_router_runtime.py" in source
    assert "tests/test_security_gate_contract.py" in source


def test_requirements_dev_includes_ruff_for_test_profiles() -> None:
    requirements = REQUIREMENTS_DEV_PATH.read_text(encoding="utf-8")
    assert "ruff==" in requirements


def test_run_test_profile_runtime_profile_targets_observability_contracts() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "runtime)" in source
    assert "tests/test_structured_logging_contract.py" in source
    assert "tests/test_timeline_runtime_metrics.py" in source
    assert "tests/test_timeline_runtime_alert_gate_script.py" in source
    assert "tests/test_notification_outbox_health_snapshot_script.py" in source
    assert "tests/test_router_registration_contract.py" in source
