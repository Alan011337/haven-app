#!/usr/bin/env python3
"""Generate AI eval scenario matrix snapshot summary (EVAL-03)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-scenario-matrix.json"
SNAPSHOT_SCHEMA_VERSION = "v1"
SNAPSHOT_ARTIFACT_KIND = "ai-eval-scenario-matrix-snapshot"
REQUIRED_CUJ_STAGES = ("bind", "ritual", "journal", "unlock")
REQUIRED_THREAT_CLASSES = ("prompt_injection", "safety_crisis", "provider_outage")


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_matrix(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_snapshot(*, matrix: dict[str, Any]) -> dict[str, Any]:
    scenarios = matrix.get("scenarios") if isinstance(matrix.get("scenarios"), list) else []
    stage_counts = Counter()
    threat_counts = Counter()
    gate_counts = Counter()

    for item in scenarios:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("cuj_stage") or "").strip()
        threat = str(item.get("threat_class") or "").strip()
        gate = str(item.get("release_gate") or "").strip()
        if stage:
            stage_counts[stage] += 1
        if threat:
            threat_counts[threat] += 1
        if gate:
            gate_counts[gate] += 1

    missing_stages = sorted(stage for stage in REQUIRED_CUJ_STAGES if stage_counts.get(stage, 0) < 1)
    missing_threat_classes = sorted(
        threat for threat in REQUIRED_THREAT_CLASSES if threat_counts.get(threat, 0) < 1
    )
    reasons: list[str] = []
    if missing_stages:
        reasons.append("missing_required_cuj_stage")
    if missing_threat_classes:
        reasons.append("missing_required_threat_class")
    if len(scenarios) < 6:
        reasons.append("insufficient_scenario_count")

    result = "pass" if not reasons else "degraded"
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "artifact_kind": SNAPSHOT_ARTIFACT_KIND,
        "generated_at": _iso_now(),
        "result": result,
        "reasons": reasons,
        "meta": {
            "scenario_count": len(scenarios),
            "required_cuj_stages": list(REQUIRED_CUJ_STAGES),
            "required_threat_classes": list(REQUIRED_THREAT_CLASSES),
            "missing_cuj_stages": missing_stages,
            "missing_threat_classes": missing_threat_classes,
            "by_cuj_stage": dict(sorted(stage_counts.items())),
            "by_threat_class": dict(sorted(threat_counts.items())),
            "by_release_gate": dict(sorted(gate_counts.items())),
        },
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate AI eval scenario matrix snapshot")
    parser.add_argument(
        "--matrix",
        default=str(MATRIX_PATH),
        help="Path to ai-eval-scenario-matrix policy JSON",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output snapshot JSON path",
    )
    parser.add_argument(
        "--allow-degraded",
        action="store_true",
        help="Allow degraded snapshot without non-zero exit code",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    matrix_path = Path(args.matrix).resolve()
    output_path = Path(args.output).resolve()
    matrix = _load_matrix(matrix_path)
    snapshot = _build_snapshot(matrix=matrix)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

    print("[ai-eval-scenario-matrix] result")
    print(f"  output: {output_path}")
    print(f"  result: {snapshot['result']}")
    print(f"  reasons: {', '.join(snapshot['reasons']) if snapshot['reasons'] else 'none'}")

    if snapshot["result"] == "degraded" and not args.allow_degraded:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
