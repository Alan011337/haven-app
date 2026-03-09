#!/usr/bin/env python3
"""Policy-as-code gate for AI eval framework contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-framework.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "ai-eval-framework"


@dataclass(frozen=True)
class AiEvalFrameworkViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_ai_eval_framework_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AiEvalFrameworkViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AiEvalFrameworkViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AiEvalFrameworkViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AiEvalFrameworkViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    suites = policy.get("cuj_suites")
    if not isinstance(suites, list) or not suites:
        violations.append(AiEvalFrameworkViolation("invalid_cuj_suites", "cuj_suites must be non-empty list."))
        suites = []

    auto_count = 0
    human_count = 0
    for idx, suite in enumerate(suites):
        if not isinstance(suite, dict):
            violations.append(AiEvalFrameworkViolation("invalid_suite_entry", f"cuj_suites[{idx}] must be object."))
            continue
        for key in ("id", "type", "entry", "gate"):
            if not str(suite.get(key, "")).strip():
                violations.append(AiEvalFrameworkViolation("missing_suite_field", f"cuj_suites[{idx}].{key} required."))
        suite_type = suite.get("type")
        if suite_type == "auto":
            auto_count += 1
        elif suite_type == "human":
            human_count += 1
        else:
            violations.append(
                AiEvalFrameworkViolation("invalid_suite_type", f"cuj_suites[{idx}].type must be auto or human.")
            )
        entry = suite.get("entry")
        if isinstance(entry, str) and entry.strip() and not (REPO_ROOT / entry).exists():
            violations.append(
                AiEvalFrameworkViolation("missing_suite_entry_file", f"cuj_suites[{idx}].entry not found: {entry}")
            )

    minimum = policy.get("minimum_requirements")
    if not isinstance(minimum, dict):
        violations.append(
            AiEvalFrameworkViolation("invalid_minimum_requirements", "minimum_requirements must be object.")
        )
    else:
        required_auto = minimum.get("auto_suites_required")
        required_human = minimum.get("human_suites_required")
        if not isinstance(required_auto, int) or required_auto < 1:
            violations.append(
                AiEvalFrameworkViolation("invalid_auto_requirement", "auto_suites_required must be positive int.")
            )
        if not isinstance(required_human, int) or required_human < 1:
            violations.append(
                AiEvalFrameworkViolation("invalid_human_requirement", "human_suites_required must be positive int.")
            )
        if isinstance(required_auto, int) and auto_count < required_auto:
            violations.append(
                AiEvalFrameworkViolation("insufficient_auto_suites", f"found {auto_count}, requires {required_auto}.")
            )
        if isinstance(required_human, int) and human_count < required_human:
            violations.append(
                AiEvalFrameworkViolation("insufficient_human_suites", f"found {human_count}, requires {required_human}.")
            )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(AiEvalFrameworkViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    AiEvalFrameworkViolation("invalid_reference_path", f"references.{key} must be path.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    AiEvalFrameworkViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_ai_eval_framework_contract_violations()
    if not violations:
        print("[ai-eval-framework-contract] ok: ai eval framework contract satisfied")
        return 0
    print("[ai-eval-framework-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
