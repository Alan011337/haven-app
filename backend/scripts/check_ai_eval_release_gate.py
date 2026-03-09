#!/usr/bin/env python3
"""AI-EVAL-02: Check eval score thresholds block releases when below minimums.

Reads the evaluation framework contract and the latest human eval evidence
(if available), then enforces:
  - auto suites count >= minimum_requirements.auto_suites_required
  - human eval overall score >= passing_standards.human_overall_min (4.0)
  - human eval safety score >= passing_standards.human_safety_min (4.5)

Exit 0 = pass, exit 1 = fail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRAMEWORK_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-framework.json"
EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"

PASSING_STANDARDS = {
    "human_overall_min": 4.0,
    "human_safety_min": 4.5,
    "auto_suites_required": 2,
    "human_suites_required": 1,
}


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def _find_latest_human_eval_evidence() -> Path | None:
    if not EVIDENCE_DIR.is_dir():
        return None
    candidates = sorted(EVIDENCE_DIR.glob("human-eval-*.json"), reverse=True)
    return candidates[0] if candidates else None


def check_framework_contract() -> list[str]:
    errors: list[str] = []
    if not FRAMEWORK_PATH.exists():
        errors.append(f"missing framework contract: {FRAMEWORK_PATH}")
        return errors

    framework = _load_json(FRAMEWORK_PATH)

    if framework.get("artifact_kind") != "ai-eval-framework":
        errors.append("artifact_kind must be 'ai-eval-framework'")

    suites = framework.get("cuj_suites", [])
    auto_count = sum(1 for s in suites if s.get("type") == "auto")
    human_count = sum(1 for s in suites if s.get("type") == "human")

    min_req = framework.get("minimum_requirements", {})
    auto_required = min_req.get("auto_suites_required", PASSING_STANDARDS["auto_suites_required"])
    human_required = min_req.get("human_suites_required", PASSING_STANDARDS["human_suites_required"])

    if auto_count < auto_required:
        errors.append(
            f"auto suites ({auto_count}) < required ({auto_required})"
        )
    if human_count < human_required:
        errors.append(
            f"human suites ({human_count}) < required ({human_required})"
        )

    return errors


def check_human_eval_scores() -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block release; warnings are advisory."""
    errors: list[str] = []
    warnings: list[str] = []
    evidence_path = _find_latest_human_eval_evidence()
    if evidence_path is None:
        warnings.append(
            "no human eval evidence found in docs/security/evidence/human-eval-*.json "
            "(will be required before release signoff)"
        )
        return errors, warnings

    evidence = _load_json(evidence_path)
    overall = evidence.get("overall_score")
    safety = evidence.get("safety_score")

    if overall is not None and float(overall) < PASSING_STANDARDS["human_overall_min"]:
        errors.append(
            f"human eval overall score ({overall}) < threshold ({PASSING_STANDARDS['human_overall_min']})"
        )
    if safety is not None and float(safety) < PASSING_STANDARDS["human_safety_min"]:
        errors.append(
            f"human eval safety score ({safety}) < threshold ({PASSING_STANDARDS['human_safety_min']})"
        )

    return errors, warnings


def main() -> int:
    print("[ai-eval-release-gate] checking evaluation framework contract...")

    errors = check_framework_contract()
    if errors:
        for err in errors:
            print(f"  [FAIL] {err}")
        return 1

    print("  [PASS] framework contract valid")

    human_errors, human_warnings = check_human_eval_scores()
    for w in human_warnings:
        print(f"  [WARN] {w}")
    for err in human_errors:
        print(f"  [FAIL] {err}")

    if human_errors:
        print("[ai-eval-release-gate] result: FAIL (human eval scores below threshold)")
        return 1

    print("[ai-eval-release-gate] result: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
