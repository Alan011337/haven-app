"""CP-04: Tests for store enforcement hooks contract."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def test_store_enforcement_script_passes():
    result = subprocess.run(
        ["python3", "scripts/check_store_enforcement_hooks_contract.py"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"


def test_store_compliance_matrix_exists():
    matrix_path = REPO_ROOT / "docs" / "security" / "store-compliance-matrix.json"
    assert matrix_path.exists()
    data = json.loads(matrix_path.read_text())
    assert data["artifact_kind"] == "store-compliance-matrix"


def test_store_compliance_matrix_has_platforms():
    matrix_path = REPO_ROOT / "docs" / "security" / "store-compliance-matrix.json"
    data = json.loads(matrix_path.read_text())
    platforms = data.get("platforms", {})
    assert "ios_app_store" in platforms
    assert "google_play" in platforms


def test_grace_policy_exists():
    policy_path = REPO_ROOT / "docs" / "security" / "billing-grace-account-hold-policy.json"
    assert policy_path.exists()
    data = json.loads(policy_path.read_text())
    providers = data.get("providers", {})
    for provider in ("stripe", "google_play", "app_store"):
        assert provider in providers, f"Missing provider: {provider}"


def test_billing_transitions_have_webhook_markers():
    from app.services.billing_transitions import WEBHOOK_EVENT_TO_STATE

    required_events = {
        "customer.subscription.deleted",
        "customer.subscription.trial_will_end",
        "googleplay.subscription.on_hold",
        "googleplay.subscription.recovered",
        "appstore.subscription.billing_retry",
        "appstore.subscription.recovered",
    }
    available_events = {str(event_name) for event_name in WEBHOOK_EVENT_TO_STATE.keys()}
    missing_events = sorted(required_events - available_events)
    assert not missing_events, f"Missing webhook event mappings: {missing_events}"


def test_entitlement_parity_test_exists():
    assert (BACKEND_ROOT / "tests" / "test_billing_entitlement_parity.py").exists()
