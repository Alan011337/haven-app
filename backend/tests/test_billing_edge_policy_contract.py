"""CP-03: Tests for billing edge-policy contract."""
from __future__ import annotations

import subprocess
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def test_billing_edge_policy_script_passes():
    result = subprocess.run(
        ["python3", "scripts/check_billing_edge_policy_contract.py"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"


def test_billing_router_has_idempotency_key():
    source = (BACKEND_ROOT / "app" / "api" / "routers" / "billing.py").read_text()
    assert "Idempotency-Key" in source


def test_billing_transition_model_has_state_transitions():
    from app.services.billing_transitions import ALLOWED_TRANSITIONS

    normalized_states = {
        (state.strip().upper() if isinstance(state, str) else state) for state in ALLOWED_TRANSITIONS.keys()
    }
    for state in ("TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD", "CANCELED"):
        assert state in normalized_states, f"Missing state transition node: {state}"


def test_billing_transition_model_has_store_webhook_events():
    from app.services.billing_transitions import WEBHOOK_EVENT_TO_STATE

    for event_name in (
        "customer.subscription.deleted",
        "googleplay.subscription.on_hold",
        "googleplay.subscription.recovered",
        "appstore.subscription.billing_retry",
        "appstore.subscription.recovered",
    ):
        assert event_name in WEBHOOK_EVENT_TO_STATE, f"Missing webhook event mapping: {event_name}"


def test_billing_router_has_async_mode_flag():
    router_source = (BACKEND_ROOT / "app" / "api" / "routers" / "billing.py").read_text()
    settings_source = (BACKEND_ROOT / "app" / "core" / "settings_domains.py").read_text()
    assert (
        "BILLING_STRIPE_WEBHOOK_ASYNC_MODE" in router_source
        or "BILLING_STRIPE_WEBHOOK_ASYNC_MODE" in settings_source
    )


def test_billing_router_has_reconciliation():
    source = (BACKEND_ROOT / "app" / "api" / "routers" / "billing.py").read_text()
    assert "reconciliation" in source


def test_required_billing_test_suites_exist():
    required = [
        "tests/test_billing_webhook_security.py",
        "tests/test_billing_idempotency_api.py",
        "tests/test_billing_authorization_matrix.py",
        "tests/test_billing_entitlement_parity.py",
    ]
    for test in required:
        assert (BACKEND_ROOT / test).exists(), f"Missing: {test}"
