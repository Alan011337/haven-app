#!/usr/bin/env python3
"""Policy-as-code gate for pricing experiment protocol (MON-04)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "pricing-experiment-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "pricing-experiment-policy"

REQUIRED_FLAGS = (
    "growth_ab_experiment_enabled",
    "growth_pricing_experiment_enabled",
)
REQUIRED_KILL_SWITCHES = (
    "disable_pricing_experiment",
)
REQUIRED_SUCCESS_METRICS = (
    "pricing.experiment.checkout_start_rate",
    "pricing.experiment.checkout_complete_rate",
    "pricing.experiment.trial_to_active_rate",
)
REQUIRED_GUARDRAIL_METRICS = (
    "pricing.experiment.refund_rate",
    "pricing.experiment.chargeback_rate",
    "pricing.experiment.p0_cuj_failure_rate",
    "pricing.experiment.support_ticket_rate",
)
REQUIRED_REFERENCES = (
    "plan_doc",
    "events_doc",
    "feature_flag_service",
    "allocator_service",
    "dry_run_script",
    "guardrail_snapshot_script",
    "guardrail_workflow",
)


@dataclass(frozen=True)
class PricingExperimentPolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def collect_pricing_experiment_policy_violations(
    *, payload: dict[str, Any] | None = None
) -> list[PricingExperimentPolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[PricingExperimentPolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            PricingExperimentPolicyViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            PricingExperimentPolicyViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    experiment_key = policy.get("experiment_key")
    if not isinstance(experiment_key, str) or not experiment_key.strip():
        violations.append(
            PricingExperimentPolicyViolation(
                "invalid_experiment_key",
                "experiment_key must be non-empty string.",
            )
        )

    feature_flags = policy.get("feature_flags")
    if not isinstance(feature_flags, dict):
        violations.append(
            PricingExperimentPolicyViolation("invalid_feature_flags", "feature_flags must be object.")
        )
    else:
        required_flags = set(_as_str_list(feature_flags.get("required")))
        for key in REQUIRED_FLAGS:
            if key not in required_flags:
                violations.append(
                    PricingExperimentPolicyViolation(
                        "missing_required_flag",
                        f"feature_flags.required missing `{key}`.",
                    )
                )
        required_kill_switches = set(_as_str_list(feature_flags.get("kill_switches")))
        for key in REQUIRED_KILL_SWITCHES:
            if key not in required_kill_switches:
                violations.append(
                    PricingExperimentPolicyViolation(
                        "missing_required_kill_switch",
                        f"feature_flags.kill_switches missing `{key}`.",
                    )
                )

    variants = policy.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        violations.append(
            PricingExperimentPolicyViolation(
                "invalid_variants",
                "variants must contain at least two weighted entries.",
            )
        )
    else:
        seen_control = False
        total_weight = 0
        for index, item in enumerate(variants):
            if not isinstance(item, dict):
                violations.append(
                    PricingExperimentPolicyViolation(
                        "invalid_variant",
                        f"variants[{index}] must be object.",
                    )
                )
                continue
            name = item.get("name")
            weight = item.get("weight")
            if not isinstance(name, str) or not name.strip():
                violations.append(
                    PricingExperimentPolicyViolation(
                        "invalid_variant_name",
                        f"variants[{index}].name must be non-empty string.",
                    )
                )
            elif name.strip() == "control":
                seen_control = True
            if not isinstance(weight, int) or weight <= 0:
                violations.append(
                    PricingExperimentPolicyViolation(
                        "invalid_variant_weight",
                        f"variants[{index}].weight must be positive integer.",
                    )
                )
            elif isinstance(weight, int):
                total_weight += weight
        if not seen_control:
            violations.append(
                PricingExperimentPolicyViolation(
                    "missing_control_variant",
                    "variants must include `control`.",
                )
            )
        if total_weight <= 0:
            violations.append(
                PricingExperimentPolicyViolation(
                    "invalid_variant_weights_total",
                    "variants total weight must be positive.",
                )
            )

    success_metrics = set(_as_str_list(policy.get("success_metrics")))
    for metric in REQUIRED_SUCCESS_METRICS:
        if metric not in success_metrics:
            violations.append(
                PricingExperimentPolicyViolation(
                    "missing_success_metric",
                    f"success_metrics missing `{metric}`.",
                )
            )

    guardrail_metrics = set(_as_str_list(policy.get("guardrail_metrics")))
    for metric in REQUIRED_GUARDRAIL_METRICS:
        if metric not in guardrail_metrics:
            violations.append(
                PricingExperimentPolicyViolation(
                    "missing_guardrail_metric",
                    f"guardrail_metrics missing `{metric}`.",
                )
            )

    guardrail_policy = policy.get("guardrail_policy")
    if not isinstance(guardrail_policy, dict):
        violations.append(
            PricingExperimentPolicyViolation("invalid_guardrail_policy", "guardrail_policy must be object.")
        )
    else:
        required_thresholds = (
            "refund_rate_max",
            "chargeback_rate_max",
            "p0_cuj_failure_rate_max",
            "support_ticket_rate_max",
        )
        for key in required_thresholds:
            value = guardrail_policy.get(key)
            if not isinstance(value, (float, int)) or float(value) <= 0:
                violations.append(
                    PricingExperimentPolicyViolation(
                        "invalid_guardrail_threshold",
                        f"guardrail_policy.{key} must be > 0.",
                    )
                )

    references = policy.get("references")
    if not isinstance(references, dict):
        violations.append(
            PricingExperimentPolicyViolation("invalid_references", "references must be object.")
        )
    else:
        for key in REQUIRED_REFERENCES:
            raw = references.get(key)
            if not isinstance(raw, str) or not raw.strip():
                violations.append(
                    PricingExperimentPolicyViolation(
                        "missing_reference",
                        f"references.{key} must be non-empty path.",
                    )
                )
                continue
            if not (REPO_ROOT / raw).exists():
                violations.append(
                    PricingExperimentPolicyViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {raw}",
                    )
                )

    feature_flag_service = references.get("feature_flag_service") if isinstance(references, dict) else None
    if isinstance(feature_flag_service, str) and feature_flag_service.strip():
        service_path = REPO_ROOT / feature_flag_service
        if service_path.exists():
            text = service_path.read_text(encoding="utf-8")
            for marker in (
                "growth_pricing_experiment_enabled",
                "disable_pricing_experiment",
            ):
                if marker not in text:
                    violations.append(
                        PricingExperimentPolicyViolation(
                            "missing_feature_flag_marker",
                            f"feature flag service missing marker `{marker}`.",
                        )
                    )

    allocator_service = references.get("allocator_service") if isinstance(references, dict) else None
    if isinstance(allocator_service, str) and allocator_service.strip():
        allocator_path = REPO_ROOT / allocator_service
        if allocator_path.exists():
            text = allocator_path.read_text(encoding="utf-8")
            for marker in (
                "evaluate_pricing_experiment_decision",
                "evaluate_pricing_experiment_guardrails",
            ):
                if marker not in text:
                    violations.append(
                        PricingExperimentPolicyViolation(
                            "missing_allocator_marker",
                            f"allocator service missing marker `{marker}`.",
                        )
                    )

    events_doc = references.get("events_doc") if isinstance(references, dict) else None
    if isinstance(events_doc, str) and events_doc.strip():
        events_path = REPO_ROOT / events_doc
        if events_path.exists():
            text = events_path.read_text(encoding="utf-8")
            for marker in (
                "growth.pricing.experiment.assigned.v1",
                "growth.pricing.experiment.checkout_started.v1",
                "growth.pricing.experiment.checkout_completed.v1",
                "growth.pricing.experiment.guardrail_triggered.v1",
            ):
                if marker not in text:
                    violations.append(
                        PricingExperimentPolicyViolation(
                            "missing_events_doc_marker",
                            f"events doc missing marker `{marker}`.",
                        )
                    )

    return violations


def run_policy_check() -> int:
    violations = collect_pricing_experiment_policy_violations()
    if not violations:
        print("[pricing-experiment-policy-contract] ok: pricing experiment policy contract satisfied")
        return 0
    print("[pricing-experiment-policy-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
