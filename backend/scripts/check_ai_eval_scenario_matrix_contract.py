#!/usr/bin/env python3
"""Policy-as-code gate for AI evaluation scenario matrix (EVAL-03)."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-scenario-matrix.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "ai-eval-scenario-matrix"
ALLOWED_CUJ_STAGES = frozenset({"bind", "ritual", "journal", "unlock", "cross_flow"})
ALLOWED_RISK_TIERS = frozenset({"low", "medium", "high", "critical"})
ALLOWED_THREAT_CLASSES = frozenset(
    {
        "prompt_injection",
        "safety_crisis",
        "schema_drift",
        "hallucination",
        "provider_outage",
        "cost_regression",
        "persona_drift",
    }
)
REQUIRED_CUJ_STAGES = frozenset({"bind", "ritual", "journal", "unlock"})
REQUIRED_THREAT_CLASSES = frozenset({"prompt_injection", "safety_crisis", "provider_outage"})
SCENARIO_ID_PATTERN = re.compile(r"^[a-z0-9_]{8,80}$")


@dataclass(frozen=True)
class AiEvalScenarioMatrixViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_clean_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def collect_ai_eval_scenario_matrix_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AiEvalScenarioMatrixViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AiEvalScenarioMatrixViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AiEvalScenarioMatrixViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AiEvalScenarioMatrixViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    scenarios = policy.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        violations.append(
            AiEvalScenarioMatrixViolation(
                "invalid_scenarios",
                "scenarios must be non-empty list.",
            )
        )
        scenarios = []

    seen_ids: set[str] = set()
    stages_covered: set[str] = set()
    threat_classes_covered: set[str] = set()

    for idx, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "invalid_scenario_entry",
                    f"scenarios[{idx}] must be object.",
                )
            )
            continue

        scenario_id = _as_clean_str(scenario.get("scenario_id"))
        if not scenario_id:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "missing_scenario_id",
                    f"scenarios[{idx}].scenario_id required.",
                )
            )
        elif not SCENARIO_ID_PATTERN.fullmatch(scenario_id):
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "invalid_scenario_id",
                    f"scenarios[{idx}].scenario_id must match `{SCENARIO_ID_PATTERN.pattern}`.",
                )
            )
        elif scenario_id in seen_ids:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "duplicate_scenario_id",
                    f"duplicate scenario_id found: {scenario_id}",
                )
            )
        else:
            seen_ids.add(scenario_id)

        cuj_stage = _as_clean_str(scenario.get("cuj_stage"))
        if cuj_stage not in ALLOWED_CUJ_STAGES:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "invalid_cuj_stage",
                    f"scenarios[{idx}].cuj_stage must be one of {sorted(ALLOWED_CUJ_STAGES)}.",
                )
            )
        else:
            stages_covered.add(cuj_stage)

        threat_class = _as_clean_str(scenario.get("threat_class"))
        if threat_class not in ALLOWED_THREAT_CLASSES:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "invalid_threat_class",
                    f"scenarios[{idx}].threat_class must be one of {sorted(ALLOWED_THREAT_CLASSES)}.",
                )
            )
        else:
            threat_classes_covered.add(threat_class)

        risk_tier = _as_clean_str(scenario.get("risk_tier"))
        if risk_tier not in ALLOWED_RISK_TIERS:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "invalid_risk_tier",
                    f"scenarios[{idx}].risk_tier must be one of {sorted(ALLOWED_RISK_TIERS)}.",
                )
            )

        description = _as_clean_str(scenario.get("description"))
        expected_outcome = _as_clean_str(scenario.get("expected_outcome"))
        release_gate = _as_clean_str(scenario.get("release_gate"))
        if not description:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "missing_description",
                    f"scenarios[{idx}].description required.",
                )
            )
        if not expected_outcome:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "missing_expected_outcome",
                    f"scenarios[{idx}].expected_outcome required.",
                )
            )
        if not release_gate:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "missing_release_gate",
                    f"scenarios[{idx}].release_gate required.",
                )
            )

        refs = scenario.get("automated_test_refs")
        if not isinstance(refs, list) or not refs:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "invalid_automated_test_refs",
                    f"scenarios[{idx}].automated_test_refs must be non-empty list.",
                )
            )
        else:
            for ref_idx, ref in enumerate(refs):
                rel_path = _as_clean_str(ref)
                if not rel_path:
                    violations.append(
                        AiEvalScenarioMatrixViolation(
                            "invalid_test_ref_path",
                            f"scenarios[{idx}].automated_test_refs[{ref_idx}] must be non-empty path.",
                        )
                    )
                    continue
                if not (REPO_ROOT / rel_path).exists():
                    violations.append(
                        AiEvalScenarioMatrixViolation(
                            "missing_test_ref_file",
                            f"scenarios[{idx}].automated_test_refs[{ref_idx}] not found: {rel_path}",
                        )
                    )

    for required_stage in sorted(REQUIRED_CUJ_STAGES):
        if required_stage not in stages_covered:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "missing_required_cuj_stage",
                    f"required cuj_stage not covered: {required_stage}",
                )
            )

    for required_threat in sorted(REQUIRED_THREAT_CLASSES):
        if required_threat not in threat_classes_covered:
            violations.append(
                AiEvalScenarioMatrixViolation(
                    "missing_required_threat_class",
                    f"required threat_class not covered: {required_threat}",
                )
            )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(
            AiEvalScenarioMatrixViolation(
                "invalid_references",
                "references must be non-empty object.",
            )
        )
    else:
        for key, rel_path_raw in references.items():
            rel_path = _as_clean_str(rel_path_raw)
            if not rel_path:
                violations.append(
                    AiEvalScenarioMatrixViolation(
                        "invalid_reference_path",
                        f"references.{key} must be non-empty path.",
                    )
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    AiEvalScenarioMatrixViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {rel_path}",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_ai_eval_scenario_matrix_violations()
    if not violations:
        print("[ai-eval-scenario-matrix-contract] ok: ai eval scenario matrix contract satisfied")
        return 0

    print("[ai-eval-scenario-matrix-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
