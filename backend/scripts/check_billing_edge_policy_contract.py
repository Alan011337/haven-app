#!/usr/bin/env python3
"""CP-03: Validate billing edge-policy coverage contract.

Checks:
1. Billing router has idempotency enforcement
2. Webhook signature verification is present
3. Async webhook mode flag exists
4. Reconciliation endpoint exists
5. Required test suites exist with minimum coverage breadth
6. Grace period / account hold state machine is complete
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"

FAILURES: list[str] = []

REQUIRED_BILLING_TESTS = [
    "tests/test_billing_webhook_security.py",
    "tests/test_billing_idempotency_api.py",
    "tests/test_billing_authorization_matrix.py",
    "tests/test_billing_entitlement_parity.py",
    "tests/test_billing_console_drift_audit.py",
    "tests/test_billing_grace_account_hold_policy_contract.py",
]

REQUIRED_ROUTER_MARKERS = [
    "Idempotency-Key",
    "_verify_stripe_signature_or_raise",
    "BILLING_STRIPE_WEBHOOK_SECRET",
    "BillingLedgerEntry",
    "reconciliation",
]

REQUIRED_LIFECYCLE_STATES = {"TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD", "CANCELED"}
REQUIRED_WEBHOOK_EVENTS = {
    "invoice.paid",
    "invoice.payment_failed",
    "googleplay.subscription.on_hold",
    "googleplay.subscription.recovered",
    "appstore.subscription.billing_retry",
    "appstore.subscription.recovered",
    "customer.subscription.deleted",
}

TRANSITIONS_PATH = BACKEND_ROOT / "app" / "services" / "billing_transitions.py"


def _load_transition_constants() -> dict[str, Any]:
    if not TRANSITIONS_PATH.exists():
        FAILURES.append("billing_transitions.py not found")
        return {}
    try:
        source = TRANSITIONS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(TRANSITIONS_PATH))
    except Exception as exc:
        FAILURES.append(f"unable to parse billing_transitions.py: {type(exc).__name__}")
        return {}

    wanted = {
        "ALLOWED_TRANSITIONS",
        "STATE_FOR_ACTION",
        "WEBHOOK_EVENT_TO_STATE",
        "WEBHOOK_ALLOWED_FROM_STATES",
    }
    extracted: dict[str, Any] = {}
    for node in tree.body:
        target_name: str | None = None
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value
        if target_name not in wanted or value_node is None:
            continue
        try:
            extracted[target_name] = ast.literal_eval(value_node)
        except Exception as exc:
            FAILURES.append(
                f"unable to evaluate billing_transitions.{target_name}: {type(exc).__name__}"
            )
    for key in wanted:
        if key not in extracted:
            FAILURES.append(f"billing_transitions missing constant: {key}")
    return extracted


def _check_router_markers() -> None:
    billing_path = BACKEND_ROOT / "app" / "api" / "routers" / "billing.py"
    if not billing_path.exists():
        FAILURES.append("billing.py not found")
        return
    source = billing_path.read_text()
    for marker in REQUIRED_ROUTER_MARKERS:
        if marker not in source:
            FAILURES.append(f"billing.py missing marker: {marker}")


def _check_test_suites_exist() -> None:
    for test_path in REQUIRED_BILLING_TESTS:
        full_path = BACKEND_ROOT / test_path
        if not full_path.exists():
            FAILURES.append(f"Missing required test: {test_path}")


def _check_state_machine_completeness() -> None:
    constants = _load_transition_constants()
    if not constants:
        return
    ALLOWED_TRANSITIONS = constants.get("ALLOWED_TRANSITIONS", {})
    STATE_FOR_ACTION = constants.get("STATE_FOR_ACTION", {})
    WEBHOOK_EVENT_TO_STATE = constants.get("WEBHOOK_EVENT_TO_STATE", {})
    WEBHOOK_ALLOWED_FROM_STATES = constants.get("WEBHOOK_ALLOWED_FROM_STATES", {})

    normalized_allowed_states = {
        (state.strip().upper() if isinstance(state, str) else state)
        for state in getattr(ALLOWED_TRANSITIONS, "keys", lambda: [])()
    }
    missing_lifecycle_states = sorted(
        state for state in REQUIRED_LIFECYCLE_STATES if state not in normalized_allowed_states
    )
    if missing_lifecycle_states:
        FAILURES.append(
            "billing transitions missing lifecycle states: " + ", ".join(missing_lifecycle_states)
        )

    for action_name, target_state in getattr(STATE_FOR_ACTION, "items", lambda: [])():
        if action_name == "ENTER_ACCOUNT_HOLD" and str(target_state or "").upper() != "GRACE_PERIOD":
            FAILURES.append("ENTER_ACCOUNT_HOLD must map to GRACE_PERIOD")

    missing_webhook_events = sorted(
        event_name
        for event_name in REQUIRED_WEBHOOK_EVENTS
        if event_name not in getattr(WEBHOOK_EVENT_TO_STATE, "keys", lambda: [])()
    )
    if missing_webhook_events:
        FAILURES.append(
            "billing webhook transition map missing events: " + ", ".join(missing_webhook_events)
        )

    for event_name in REQUIRED_WEBHOOK_EVENTS:
        allowed_from_states = WEBHOOK_ALLOWED_FROM_STATES.get(event_name) if isinstance(WEBHOOK_ALLOWED_FROM_STATES, dict) else None
        if not isinstance(allowed_from_states, set):
            FAILURES.append(f"billing webhook allowed-from state map missing for event: {event_name}")
            continue
        normalized_event_states: set[Optional[str]] = set()
        for raw_state in allowed_from_states:
            if raw_state is None:
                normalized_event_states.add(None)
            else:
                normalized_event_states.add(str(raw_state).strip().upper())
        if "CANCELED" not in normalized_event_states and event_name not in {
            "customer.subscription.trial_will_end",
            "invoice.paid",
            "invoice.payment_failed",
            "googleplay.subscription.on_hold",
            "googleplay.subscription.recovered",
            "appstore.subscription.billing_retry",
            "appstore.subscription.recovered",
        }:
            FAILURES.append(f"billing webhook allowed-from states should include CANCELED: {event_name}")


def _check_async_mode_support() -> None:
    billing_path = BACKEND_ROOT / "app" / "api" / "routers" / "billing.py"
    settings_domain_path = BACKEND_ROOT / "app" / "core" / "settings_domains.py"
    if not billing_path.exists():
        return
    billing_source = billing_path.read_text()
    settings_source = settings_domain_path.read_text() if settings_domain_path.exists() else ""
    marker_present = (
        "BILLING_STRIPE_WEBHOOK_ASYNC_MODE" in billing_source
        or "BILLING_STRIPE_WEBHOOK_ASYNC_MODE" in settings_source
    )
    if not marker_present:
        FAILURES.append("billing async webhook mode flag marker missing in router/settings domain")


def main() -> int:
    _check_router_markers()
    _check_test_suites_exist()
    _check_state_machine_completeness()
    _check_async_mode_support()

    if FAILURES:
        print("CP-03 billing edge-policy contract FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("CP-03 billing edge-policy contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
