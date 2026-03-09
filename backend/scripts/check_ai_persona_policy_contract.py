#!/usr/bin/env python3
"""Policy-as-code gate for AI persona engine contract (P1-H)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-persona-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "ai-persona-policy"
REQUIRED_POLICY_MARKERS = {"AI-POL-01", "AI-POL-02", "AI-POL-03"}
REQUIRED_STRATEGY_MARKERS = {
    "relationship_weather_inference",
    "conflict_to_deescalation_guidance",
    "repair_signal_amplification",
}
REQUIRED_RUNTIME_OUTPUT_GUARDRAIL_MARKERS = {
    "non_impersonation_runtime_assertion",
    "partner_identity_claim_rewrite",
    "direct_love_phrase_rewrite",
}


@dataclass(frozen=True)
class AIPersonaPolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_ai_persona_policy_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AIPersonaPolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AIPersonaPolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    persona_id = str(policy.get("persona_id", "")).strip()
    if persona_id != "third_party_observer_v1":
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_persona_id",
                "persona_id must be `third_party_observer_v1`.",
            )
        )

    immutable_policies = policy.get("immutable_policies")
    if not isinstance(immutable_policies, list) or not immutable_policies:
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_immutable_policies",
                "immutable_policies must be non-empty list.",
            )
        )
    else:
        marker_set = {str(item) for item in immutable_policies}
        missing_markers = sorted(REQUIRED_POLICY_MARKERS - marker_set)
        if missing_markers:
            violations.append(
                AIPersonaPolicyViolation(
                    "missing_immutable_policy_marker",
                    "missing immutable policy markers: " + ", ".join(missing_markers),
                )
            )

    dynamic_context = policy.get("dynamic_context_injection")
    if not isinstance(dynamic_context, dict):
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_dynamic_context_injection",
                "dynamic_context_injection must be object.",
            )
        )
    else:
        if not isinstance(dynamic_context.get("enabled_by_default"), bool):
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_enabled_by_default",
                    "dynamic_context_injection.enabled_by_default must be boolean.",
                )
            )

        if dynamic_context.get("feature_flag") != "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED":
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_feature_flag",
                    "dynamic_context_injection.feature_flag must be "
                    "`AI_DYNAMIC_CONTEXT_INJECTION_ENABLED`.",
                )
            )

        strategy = dynamic_context.get("strategy")
        if not isinstance(strategy, list) or not strategy:
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_dynamic_context_strategy",
                    "dynamic_context_injection.strategy must be non-empty list.",
                )
            )
        else:
            strategy_set = {str(item) for item in strategy}
            missing_strategy = sorted(REQUIRED_STRATEGY_MARKERS - strategy_set)
            if missing_strategy:
                violations.append(
                    AIPersonaPolicyViolation(
                        "missing_strategy_marker",
                        "missing strategy markers: " + ", ".join(missing_strategy),
                    )
                )

    runtime_output_guardrail = policy.get("runtime_output_guardrail")
    if not isinstance(runtime_output_guardrail, dict):
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_runtime_output_guardrail",
                "runtime_output_guardrail must be object.",
            )
        )
    else:
        if not isinstance(runtime_output_guardrail.get("enabled_by_default"), bool):
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_runtime_guardrail_enabled_by_default",
                    "runtime_output_guardrail.enabled_by_default must be boolean.",
                )
            )
        if str(runtime_output_guardrail.get("version", "")).strip() != "v1":
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_runtime_guardrail_version",
                    "runtime_output_guardrail.version must be `v1`.",
                )
            )
        if runtime_output_guardrail.get("feature_flag") != "AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED":
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_runtime_guardrail_feature_flag",
                    "runtime_output_guardrail.feature_flag must be "
                    "`AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED`.",
                )
            )
        strategy = runtime_output_guardrail.get("strategy")
        if not isinstance(strategy, list) or not strategy:
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_runtime_guardrail_strategy",
                    "runtime_output_guardrail.strategy must be non-empty list.",
                )
            )
        else:
            strategy_set = {str(item) for item in strategy}
            missing_strategy = sorted(REQUIRED_RUNTIME_OUTPUT_GUARDRAIL_MARKERS - strategy_set)
            if missing_strategy:
                violations.append(
                    AIPersonaPolicyViolation(
                        "missing_runtime_guardrail_marker",
                        "missing runtime guardrail markers: " + ", ".join(missing_strategy),
                    )
                )
        if runtime_output_guardrail.get("fallback_behavior") != "sanitize_output_and_keep_third_party_observer_voice":
            violations.append(
                AIPersonaPolicyViolation(
                    "invalid_runtime_guardrail_fallback_behavior",
                    "runtime_output_guardrail.fallback_behavior must be "
                    "`sanitize_output_and_keep_third_party_observer_voice`.",
                )
            )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(
            AIPersonaPolicyViolation(
                "invalid_references",
                "references must be non-empty object.",
            )
        )
    else:
        for key, rel_path in references.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    AIPersonaPolicyViolation(
                        "invalid_reference_path",
                        f"references.{key} must be path string.",
                    )
                )
                continue

            abs_path = REPO_ROOT / rel_path
            if not abs_path.exists():
                violations.append(
                    AIPersonaPolicyViolation(
                        "missing_reference_file",
                        f"references.{key} file not found: {rel_path}",
                    )
                )

    if isinstance(references, dict):
        policy_notice_path = references.get("ai_policy_notice")
        if isinstance(policy_notice_path, str) and policy_notice_path.strip():
            policy_notice_text = _read_text(REPO_ROOT / policy_notice_path)
            for marker in sorted(REQUIRED_POLICY_MARKERS):
                if marker not in policy_notice_text:
                    violations.append(
                        AIPersonaPolicyViolation(
                            "missing_ai_policy_notice_marker",
                            f"ai policy notice missing marker `{marker}`.",
                        )
                    )

        prompt_source_path = references.get("prompt_source")
        if isinstance(prompt_source_path, str) and prompt_source_path.strip():
            prompt_text = _read_text(REPO_ROOT / prompt_source_path)
            for marker_text in ("不冒充伴侶", "危機一致化", "關係教練邊界"):
                if marker_text not in prompt_text:
                    violations.append(
                        AIPersonaPolicyViolation(
                            "missing_prompt_policy_text",
                            f"prompt source missing text `{marker_text}`.",
                        )
                    )

        persona_service_path = references.get("persona_service")
        if isinstance(persona_service_path, str) and persona_service_path.strip():
            persona_service_text = _read_text(REPO_ROOT / persona_service_path)
            for marker_text in (
                "PERSONA_ID",
                "build_dynamic_context_injection",
                "build_analysis_messages",
                "apply_persona_output_guardrails",
                "relationship_weather",
            ):
                if marker_text not in persona_service_text:
                    violations.append(
                        AIPersonaPolicyViolation(
                            "missing_persona_service_marker",
                            f"persona service missing marker `{marker_text}`.",
                        )
                    )

        analysis_service_path = references.get("analysis_service")
        if isinstance(analysis_service_path, str) and analysis_service_path.strip():
            analysis_service_text = _read_text(REPO_ROOT / analysis_service_path)
            if "build_analysis_messages" not in analysis_service_text:
                violations.append(
                    AIPersonaPolicyViolation(
                        "missing_analysis_service_integration",
                        "analysis service must call `build_analysis_messages`.",
                    )
                )
            if "apply_persona_output_guardrails" not in analysis_service_text:
                violations.append(
                    AIPersonaPolicyViolation(
                        "missing_analysis_persona_guardrail_integration",
                        "analysis service must call `apply_persona_output_guardrails`.",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_ai_persona_policy_contract_violations()
    if not violations:
        print("[ai-persona-policy-contract] ok: ai persona policy contract satisfied")
        return 0
    print("[ai-persona-policy-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
