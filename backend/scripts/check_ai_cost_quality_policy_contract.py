#!/usr/bin/env python3
"""Policy-as-code gate for AI cost/quality monitor contract (P1-I)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-cost-quality-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "ai-cost-quality-policy"


@dataclass(frozen=True)
class AICostQualityPolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_ai_cost_quality_policy_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AICostQualityPolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AICostQualityPolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AICostQualityPolicyViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AICostQualityPolicyViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    thresholds = policy.get("thresholds")
    if not isinstance(thresholds, dict):
        violations.append(
            AICostQualityPolicyViolation("invalid_thresholds", "thresholds must be object.")
        )
    else:
        schema_min = _as_float(thresholds.get("schema_compliance_min"))
        if schema_min is None or schema_min <= 0 or schema_min > 100:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_schema_compliance_min",
                    "thresholds.schema_compliance_min must be > 0 and <= 100.",
                )
            )

        hallucination_max = _as_float(thresholds.get("hallucination_proxy_max"))
        if hallucination_max is None or hallucination_max <= 0 or hallucination_max > 1:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_hallucination_proxy_max",
                    "thresholds.hallucination_proxy_max must be > 0 and <= 1.",
                )
            )

        drift_score_max = _as_float(thresholds.get("drift_score_max"))
        if drift_score_max is None or drift_score_max <= 0 or drift_score_max > 1:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_drift_score_max",
                    "thresholds.drift_score_max must be > 0 and <= 1.",
                )
            )

        cost_max = _as_float(thresholds.get("cost_usd_per_active_couple_max"))
        if cost_max is None or cost_max <= 0:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_cost_max",
                    "thresholds.cost_usd_per_active_couple_max must be > 0.",
                )
            )

        token_budget = thresholds.get("token_budget_daily")
        if not isinstance(token_budget, int) or token_budget <= 0:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_token_budget_daily",
                    "thresholds.token_budget_daily must be positive integer.",
                )
            )

    drift_detection = policy.get("drift_detection")
    if not isinstance(drift_detection, dict):
        violations.append(
            AICostQualityPolicyViolation(
                "invalid_drift_detection",
                "drift_detection must be object.",
            )
        )
    else:
        if drift_detection.get("mode") != "relative_delta_average":
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_drift_mode",
                    "drift_detection.mode must be `relative_delta_average`.",
                )
            )
        if drift_detection.get("fallback_behavior") != "degrade_but_do_not_block_journal_write":
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_fallback_behavior",
                    "drift_detection.fallback_behavior must be "
                    "`degrade_but_do_not_block_journal_write`.",
                )
            )
        critical_multiplier = _as_float(drift_detection.get("critical_multiplier"))
        if critical_multiplier is None or critical_multiplier <= 1.0:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_drift_critical_multiplier",
                    "drift_detection.critical_multiplier must be > 1.0.",
                )
            )

    budget_guardrails = policy.get("budget_guardrails")
    if not isinstance(budget_guardrails, dict):
        violations.append(
            AICostQualityPolicyViolation(
                "invalid_budget_guardrails",
                "budget_guardrails must be object.",
            )
        )
    else:
        if budget_guardrails.get("enforcement_mode") not in {"observe_only", "enforced"}:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_enforcement_mode",
                    "budget_guardrails.enforcement_mode must be observe_only|enforced.",
                )
            )
        actions = budget_guardrails.get("on_breach")
        if not isinstance(actions, list) or not actions:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_on_breach_actions",
                    "budget_guardrails.on_breach must be non-empty list.",
                )
            )
        gate_mode = str(budget_guardrails.get("request_class_gate_mode", "")).strip().lower()
        if gate_mode not in {"observe_only", "deterministic"}:
            violations.append(
                AICostQualityPolicyViolation(
                    "invalid_request_class_gate_mode",
                    "budget_guardrails.request_class_gate_mode must be observe_only|deterministic.",
                )
            )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(AICostQualityPolicyViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in references.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    AICostQualityPolicyViolation(
                        "invalid_reference_path",
                        f"references.{key} must be path string.",
                    )
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    AICostQualityPolicyViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {rel_path}",
                    )
                )

        service_path = references.get("service")
        if isinstance(service_path, str) and service_path.strip():
            service_text = _read_text(REPO_ROOT / service_path)
            for marker in ("AIQualityThresholds", "calculate_relative_drift_score", "evaluate_quality_gate"):
                if marker not in service_text:
                    violations.append(
                        AICostQualityPolicyViolation(
                            "missing_service_marker",
                            f"service missing marker `{marker}`.",
                        )
                    )

        snapshot_script_path = references.get("snapshot_script")
        if isinstance(snapshot_script_path, str) and snapshot_script_path.strip():
            snapshot_script_text = _read_text(REPO_ROOT / snapshot_script_path)
            for marker in ("evaluate_quality_gate", "ai-quality-snapshot", "thresholds"):
                if marker not in snapshot_script_text:
                    violations.append(
                        AICostQualityPolicyViolation(
                            "missing_snapshot_script_marker",
                            f"snapshot script missing marker `{marker}`.",
                        )
                    )

        drift_detector_path = references.get("drift_detector_script")
        if isinstance(drift_detector_path, str) and drift_detector_path.strip():
            drift_detector_text = _read_text(REPO_ROOT / drift_detector_path)
            for marker in ("ai-eval-drift-detector", "drift_score_max", "degrade_but_do_not_block_journal_write"):
                if marker not in drift_detector_text:
                    violations.append(
                        AICostQualityPolicyViolation(
                            "missing_drift_detector_marker",
                            f"drift detector script missing marker `{marker}`.",
                        )
                    )

    return violations


def run_policy_check() -> int:
    violations = collect_ai_cost_quality_policy_contract_violations()
    if not violations:
        print("[ai-cost-quality-policy-contract] ok: ai cost/quality policy contract satisfied")
        return 0

    print("[ai-cost-quality-policy-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
