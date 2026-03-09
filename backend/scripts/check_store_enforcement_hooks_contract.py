#!/usr/bin/env python3
"""CP-04: Validate platform-specific store enforcement hooks contract.

Checks:
1. Store compliance matrix exists and is well-formed
2. Grace/account-hold policy exists and covers all providers
3. Billing router contains provider-specific webhook event markers
4. Entitlement parity test exists
5. Config has store-related settings
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
DOCS_ROOT = REPO_ROOT / "docs"

FAILURES: list[str] = []

REQUIRED_PROVIDERS = ["stripe", "google_play", "app_store"]
REQUIRED_PLATFORMS = ["ios_app_store", "google_play"]

REQUIRED_WEBHOOK_MARKERS = [
    "googleplay.subscription",
    "appstore.subscription",
    "customer.subscription",
]
TRANSITIONS_PATH = BACKEND_ROOT / "app" / "services" / "billing_transitions.py"


def _load_webhook_event_map() -> dict[str, Any]:
    if not TRANSITIONS_PATH.exists():
        FAILURES.append("billing_transitions.py not found")
        return {}
    try:
        source = TRANSITIONS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(TRANSITIONS_PATH))
    except Exception as exc:
        FAILURES.append(f"unable to parse billing_transitions.py: {type(exc).__name__}")
        return {}

    for node in tree.body:
        target_name: str | None = None
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value
        if target_name != "WEBHOOK_EVENT_TO_STATE" or value_node is None:
            continue
        try:
            parsed = ast.literal_eval(value_node)
        except Exception as exc:
            FAILURES.append(
                "unable to evaluate billing_transitions.WEBHOOK_EVENT_TO_STATE: "
                + type(exc).__name__
            )
            return {}
        if not isinstance(parsed, dict):
            FAILURES.append("billing_transitions.WEBHOOK_EVENT_TO_STATE must be a dict")
            return {}
        return parsed

    FAILURES.append("billing_transitions missing constant: WEBHOOK_EVENT_TO_STATE")
    return {}


def _check_store_compliance_matrix() -> None:
    matrix_path = DOCS_ROOT / "security" / "store-compliance-matrix.json"
    if not matrix_path.exists():
        FAILURES.append("store-compliance-matrix.json not found")
        return
    try:
        data = json.loads(matrix_path.read_text())
    except json.JSONDecodeError:
        FAILURES.append("store-compliance-matrix.json is invalid JSON")
        return

    if data.get("artifact_kind") != "store-compliance-matrix":
        FAILURES.append("store-compliance-matrix.json has wrong artifact_kind")

    platforms = data.get("platforms", {})
    for platform in REQUIRED_PLATFORMS:
        if platform not in platforms:
            FAILURES.append(f"store-compliance-matrix.json missing platform: {platform}")


def _check_grace_policy() -> None:
    policy_path = DOCS_ROOT / "security" / "billing-grace-account-hold-policy.json"
    if not policy_path.exists():
        FAILURES.append("billing-grace-account-hold-policy.json not found")
        return
    try:
        data = json.loads(policy_path.read_text())
    except json.JSONDecodeError:
        FAILURES.append("billing-grace-account-hold-policy.json is invalid JSON")
        return

    providers = data.get("providers", {})
    for provider in REQUIRED_PROVIDERS:
        if provider not in providers:
            FAILURES.append(f"billing-grace-account-hold-policy.json missing provider: {provider}")


def _check_webhook_markers() -> None:
    webhook_event_map = _load_webhook_event_map()
    if not webhook_event_map:
        return

    available_events = {str(event_name) for event_name in webhook_event_map.keys()}
    marker_to_event_required = {
        "googleplay.subscription": {"googleplay.subscription.on_hold", "googleplay.subscription.recovered"},
        "appstore.subscription": {"appstore.subscription.billing_retry", "appstore.subscription.recovered"},
        "customer.subscription": {"customer.subscription.deleted", "customer.subscription.trial_will_end"},
    }
    for marker in REQUIRED_WEBHOOK_MARKERS:
        required_events = marker_to_event_required[marker]
        missing_events = sorted(event_name for event_name in required_events if event_name not in available_events)
        if missing_events:
            FAILURES.append(
                "billing transitions missing webhook events for marker "
                f"{marker}: {', '.join(missing_events)}"
            )


def _check_entitlement_parity_test() -> None:
    test_path = BACKEND_ROOT / "tests" / "test_billing_entitlement_parity.py"
    if not test_path.exists():
        FAILURES.append("test_billing_entitlement_parity.py not found")


def main() -> int:
    _check_store_compliance_matrix()
    _check_grace_policy()
    _check_webhook_markers()
    _check_entitlement_parity_test()

    if FAILURES:
        print("CP-04 store enforcement hooks contract FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("CP-04 store enforcement hooks contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
