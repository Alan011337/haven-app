#!/usr/bin/env python3
"""Policy-as-code gate for billing grace/account-hold entitlement rules."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "billing-grace-account-hold-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "billing-grace-account-hold-policy"
REQUIRED_PROVIDERS = ("stripe", "google_play", "app_store")
REQUIRED_PROVIDER_FIELDS = (
    "account_hold_event",
    "account_hold_state",
    "recover_event",
    "recover_state",
    "cancel_event",
    "cancel_state",
)
REQUIRED_ENTITLEMENT_STATES = ("TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD", "CANCELED")
REQUIRED_REFERENCES = (
    "billing_router",
    "billing_webhook_tests",
    "billing_idempotency_tests",
    "billing_doc",
)


@dataclass(frozen=True)
class BillingGracePolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_billing_grace_policy_violations(
    *, payload: dict[str, Any] | None = None
) -> list[BillingGracePolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[BillingGracePolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            BillingGracePolicyViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            BillingGracePolicyViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    providers = policy.get("providers")
    if not isinstance(providers, dict):
        violations.append(BillingGracePolicyViolation("invalid_providers", "providers must be object."))
    else:
        for provider_name in REQUIRED_PROVIDERS:
            provider_policy = providers.get(provider_name)
            if not isinstance(provider_policy, dict):
                violations.append(
                    BillingGracePolicyViolation(
                        "missing_provider_policy",
                        f"providers.{provider_name} must be object.",
                    )
                )
                continue
            for field in REQUIRED_PROVIDER_FIELDS:
                value = provider_policy.get(field)
                if not isinstance(value, str) or not value.strip():
                    violations.append(
                        BillingGracePolicyViolation(
                            "missing_provider_field",
                            f"providers.{provider_name}.{field} must be non-empty string.",
                        )
                    )
            if provider_policy.get("account_hold_state") != "GRACE_PERIOD":
                violations.append(
                    BillingGracePolicyViolation(
                        "invalid_account_hold_state",
                        f"providers.{provider_name}.account_hold_state must be GRACE_PERIOD.",
                    )
                )
            if provider_policy.get("recover_state") != "ACTIVE":
                violations.append(
                    BillingGracePolicyViolation(
                        "invalid_recover_state",
                        f"providers.{provider_name}.recover_state must be ACTIVE.",
                    )
                )
            if provider_policy.get("cancel_state") != "CANCELED":
                violations.append(
                    BillingGracePolicyViolation(
                        "invalid_cancel_state",
                        f"providers.{provider_name}.cancel_state must be CANCELED.",
                    )
                )

    entitlement_rules = policy.get("entitlement_rules")
    if not isinstance(entitlement_rules, dict):
        violations.append(
            BillingGracePolicyViolation("invalid_entitlement_rules", "entitlement_rules must be object.")
        )
    else:
        allowed_states = entitlement_rules.get("allowed_states")
        if not isinstance(allowed_states, list):
            violations.append(
                BillingGracePolicyViolation(
                    "invalid_allowed_states",
                    "entitlement_rules.allowed_states must be list.",
                )
            )
        else:
            normalized_states = {str(item).strip() for item in allowed_states}
            missing_states = [state for state in REQUIRED_ENTITLEMENT_STATES if state not in normalized_states]
            if missing_states:
                violations.append(
                    BillingGracePolicyViolation(
                        "missing_allowed_states",
                        "entitlement_rules.allowed_states missing: " + ", ".join(missing_states),
                    )
                )

        if entitlement_rules.get("account_hold_state") != "GRACE_PERIOD":
            violations.append(
                BillingGracePolicyViolation(
                    "invalid_account_hold_rule_state",
                    "entitlement_rules.account_hold_state must be GRACE_PERIOD.",
                )
            )
        if entitlement_rules.get("recovery_state") != "ACTIVE":
            violations.append(
                BillingGracePolicyViolation(
                    "invalid_recovery_rule_state",
                    "entitlement_rules.recovery_state must be ACTIVE.",
                )
            )
        if entitlement_rules.get("cancellation_state") != "CANCELED":
            violations.append(
                BillingGracePolicyViolation(
                    "invalid_cancellation_rule_state",
                    "entitlement_rules.cancellation_state must be CANCELED.",
                )
            )

    references = policy.get("references")
    if not isinstance(references, dict):
        violations.append(BillingGracePolicyViolation("invalid_references", "references must be object."))
    else:
        for key in REQUIRED_REFERENCES:
            ref_path = references.get(key)
            if not isinstance(ref_path, str) or not ref_path.strip():
                violations.append(
                    BillingGracePolicyViolation(
                        "missing_reference",
                        f"references.{key} must be non-empty path.",
                    )
                )
                continue
            if not (REPO_ROOT / ref_path).exists():
                violations.append(
                    BillingGracePolicyViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {ref_path}",
                    )
                )

    router_path = references.get("billing_router") if isinstance(references, dict) else None
    if isinstance(router_path, str) and router_path.strip():
        router_file = REPO_ROOT / router_path
        if router_file.exists():
            router_text = router_file.read_text(encoding="utf-8")
            for marker in (
                "googleplay.subscription.on_hold",
                "googleplay.subscription.recovered",
                "appstore.subscription.billing_retry",
                "appstore.subscription.recovered",
                "ENTER_ACCOUNT_HOLD",
            ):
                if marker not in router_text:
                    violations.append(
                        BillingGracePolicyViolation(
                            "missing_router_marker",
                            f"billing router must contain marker: {marker}",
                        )
                    )

    return violations


def run_policy_check() -> int:
    violations = collect_billing_grace_policy_violations()
    if not violations:
        print("[billing-grace-policy-contract] ok: billing grace/account-hold policy contract satisfied")
        return 0
    print("[billing-grace-policy-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
