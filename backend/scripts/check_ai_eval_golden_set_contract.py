#!/usr/bin/env python3
"""Policy-as-code gate for AI eval golden set contract (EVAL-01)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-golden-set.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "ai-eval-golden-set"
MIN_CASES = 100
MAX_CASES = 500


@dataclass(frozen=True)
class AIEvalGoldenSetViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_ai_eval_golden_set_violations(
    *,
    payload: dict[str, Any] | None = None,
) -> list[AIEvalGoldenSetViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AIEvalGoldenSetViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AIEvalGoldenSetViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AIEvalGoldenSetViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    version = str(policy.get("version", "")).strip()
    if not version:
        violations.append(
            AIEvalGoldenSetViolation("missing_version", "version is required.")
        )

    total_cases = policy.get("total_cases")
    if not isinstance(total_cases, int):
        violations.append(
            AIEvalGoldenSetViolation("invalid_total_cases_type", "total_cases must be integer.")
        )
        total_cases = None
    elif total_cases < MIN_CASES or total_cases > MAX_CASES:
        violations.append(
            AIEvalGoldenSetViolation(
                "invalid_total_cases_range",
                f"total_cases must be between {MIN_CASES} and {MAX_CASES}.",
            )
        )

    case_ids = policy.get("case_ids")
    if not isinstance(case_ids, list) or not case_ids:
        violations.append(
            AIEvalGoldenSetViolation("invalid_case_ids", "case_ids must be non-empty list.")
        )
    else:
        cleaned_ids: list[str] = []
        for index, raw_id in enumerate(case_ids):
            case_id = str(raw_id or "").strip()
            if not case_id:
                violations.append(
                    AIEvalGoldenSetViolation(
                        "empty_case_id",
                        f"case_ids[{index}] is empty.",
                    )
                )
                continue
            cleaned_ids.append(case_id)
        if len(set(cleaned_ids)) != len(cleaned_ids):
            violations.append(
                AIEvalGoldenSetViolation(
                    "duplicate_case_id",
                    "case_ids must be unique.",
                )
            )
        if isinstance(total_cases, int) and len(case_ids) != total_cases:
            violations.append(
                AIEvalGoldenSetViolation(
                    "case_count_mismatch",
                    "len(case_ids) must equal total_cases.",
                )
            )

    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        violations.append(
            AIEvalGoldenSetViolation(
                "invalid_coverage",
                "coverage must be object.",
            )
        )
    else:
        for key in ("cuj_stage_counts", "threat_class_counts", "language_counts"):
            value = coverage.get(key)
            if not isinstance(value, dict) or not value:
                violations.append(
                    AIEvalGoldenSetViolation(
                        "invalid_coverage_bucket",
                        f"coverage.{key} must be non-empty object.",
                    )
                )

    thresholds = policy.get("gate_thresholds")
    if not isinstance(thresholds, dict):
        violations.append(
            AIEvalGoldenSetViolation(
                "invalid_gate_thresholds",
                "gate_thresholds must be object.",
            )
        )
    else:
        min_cases_per_run = thresholds.get("min_cases_per_run")
        if not isinstance(min_cases_per_run, int) or min_cases_per_run < MIN_CASES:
            violations.append(
                AIEvalGoldenSetViolation(
                    "invalid_min_cases_per_run",
                    f"gate_thresholds.min_cases_per_run must be integer >= {MIN_CASES}.",
                )
            )
        for metric_key in (
            "min_exact_match_rate",
            "max_safety_tier_mismatch_rate",
            "max_schema_failure_rate",
        ):
            value = thresholds.get(metric_key)
            if not isinstance(value, (int, float)):
                violations.append(
                    AIEvalGoldenSetViolation(
                        "invalid_threshold_type",
                        f"gate_thresholds.{metric_key} must be number.",
                    )
                )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(
            AIEvalGoldenSetViolation(
                "invalid_references",
                "references must be non-empty object.",
            )
        )
    else:
        for key, rel_path in references.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    AIEvalGoldenSetViolation(
                        "invalid_reference_path",
                        f"references.{key} must be non-empty path string.",
                    )
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    AIEvalGoldenSetViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {rel_path}",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_ai_eval_golden_set_violations()
    if not violations:
        print("[ai-eval-golden-set-contract] ok: ai eval golden set contract satisfied")
        return 0

    print("[ai-eval-golden-set-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
