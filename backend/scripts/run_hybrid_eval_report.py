#!/usr/bin/env python3
"""EVAL-05: Generate hybrid (auto + human) evaluation report per release.

Collects results from:
  - Golden set snapshot (auto)
  - Scenario matrix snapshot (auto)
  - Drift detector (auto)
  - Human eval evidence (human, if present)

Produces a single JSON artifact for release signoff.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
GOLDEN_SET_RESULTS = REPO_ROOT / "docs" / "security" / "ai-eval-golden-set-results.json"


def _load_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def _find_latest_evidence(prefix: str) -> dict | None:
    if not EVIDENCE_DIR.is_dir():
        return None
    candidates = sorted(EVIDENCE_DIR.glob(f"{prefix}*.json"), reverse=True)
    if not candidates:
        return None
    return _load_json_safe(candidates[0])


def _build_auto_section() -> dict:
    golden_set = _load_json_safe(GOLDEN_SET_RESULTS)
    scenario_matrix = _find_latest_evidence("ai-eval-scenario-matrix-snapshot")
    drift = _find_latest_evidence("ai-quality-snapshot")

    return {
        "golden_set": {
            "available": golden_set is not None,
            "case_count": len(golden_set.get("cases", [])) if golden_set else 0,
        },
        "scenario_matrix": {
            "available": scenario_matrix is not None,
        },
        "drift_detector": {
            "available": drift is not None,
        },
    }


def _build_human_section() -> dict:
    human_evidence = _find_latest_evidence("human-eval")
    if not human_evidence:
        return {
            "available": False,
            "overall_score": None,
            "safety_score": None,
            "sample_count": 0,
        }
    return {
        "available": True,
        "overall_score": human_evidence.get("overall_score"),
        "safety_score": human_evidence.get("safety_score"),
        "sample_count": human_evidence.get("sample_count", 0),
    }


def generate_report() -> dict:
    auto_section = _build_auto_section()
    human_section = _build_human_section()

    auto_pass = auto_section["golden_set"]["available"]
    return {
        "artifact_kind": "hybrid-eval-report",
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auto_evaluation": auto_section,
        "human_evaluation": human_section,
        "overall_status": "pass" if auto_pass else "degraded",
        "release_ready": auto_pass,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate hybrid eval report.")
    parser.add_argument("--output", default="/tmp/hybrid-eval-report.json")
    args = parser.parse_args(argv)

    report = generate_report()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"[hybrid-eval-report] written to {output_path}")
    print(f"[hybrid-eval-report] status: {report['overall_status']}")
    print(f"[hybrid-eval-report] release_ready: {report['release_ready']}")

    return 0 if report["release_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
