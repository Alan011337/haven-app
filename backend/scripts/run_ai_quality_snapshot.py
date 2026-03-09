#!/usr/bin/env python3
"""Generate AI quality/cost drift snapshot evidence (P1-I baseline)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.ai_quality_monitor import AIQualityThresholds, evaluate_quality_gate

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

DEFAULT_BASELINE_PATH = REPO_ROOT / "docs" / "ai-safety" / "eval-baseline.json"
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
DEFAULT_LATEST_PATH = DEFAULT_EVIDENCE_DIR / "ai-quality-snapshot-latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _build_thresholds() -> AIQualityThresholds:
    return AIQualityThresholds(
        schema_compliance_min=_safe_float_env("AI_SCHEMA_COMPLIANCE_MIN", 99.9),
        hallucination_proxy_max=_safe_float_env("AI_HALLUCINATION_PROXY_MAX", 0.05),
        drift_score_max=_safe_float_env("AI_DRIFT_SCORE_MAX", 0.2),
        cost_usd_per_active_couple_max=_safe_float_env("AI_COST_MAX_USD_PER_ACTIVE_COUPLE", 1.5),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AI quality snapshot evidence")
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE_PATH),
        help="Path to baseline metrics JSON",
    )
    parser.add_argument(
        "--current",
        default="",
        help="Path to current metrics JSON. If missing and --allow-missing-current is set, baseline is reused.",
    )
    parser.add_argument(
        "--allow-missing-current",
        action="store_true",
        help="Allow current metrics path to be missing by reusing baseline metrics",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON path. Defaults to docs/security/evidence/ai-quality-snapshot-<timestamp>.json",
    )
    parser.add_argument(
        "--latest-path",
        default="",
        help=(
            "Optional path to also write latest snapshot pointer file. "
            "If omitted and --output is not provided, defaults to docs/security/evidence/ai-quality-snapshot-latest.json."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    baseline_path = Path(args.baseline).resolve()
    if not baseline_path.exists():
        print(f"[ai-quality-snapshot] fail: baseline not found: {baseline_path}")
        return 1
    baseline = _load_json(baseline_path)

    current_source = "current_file"
    if args.current:
        current_path = Path(args.current).resolve()
        if not current_path.exists():
            if not args.allow_missing_current:
                print(f"[ai-quality-snapshot] fail: current metrics not found: {current_path}")
                return 1
            current = dict(baseline)
            current_source = "baseline_fallback"
        else:
            current = _load_json(current_path)
    else:
        if not args.allow_missing_current:
            print("[ai-quality-snapshot] fail: --current is required unless --allow-missing-current is set")
            return 1
        current = dict(baseline)
        current_source = "baseline_fallback"

    thresholds = _build_thresholds()
    evaluation = evaluate_quality_gate(
        baseline=baseline,
        current=current,
        thresholds=thresholds,
    )

    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = DEFAULT_EVIDENCE_DIR / f"ai-quality-snapshot-{timestamp}.json"

    if args.latest_path:
        latest_path: Path | None = Path(args.latest_path).resolve()
    elif not args.output:
        latest_path = DEFAULT_LATEST_PATH
    else:
        latest_path = None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "artifact_kind": "ai-quality-snapshot",
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "baseline_path": str(baseline_path),
        "current_source": current_source,
        "thresholds": {
            "schema_compliance_min": thresholds.schema_compliance_min,
            "hallucination_proxy_max": thresholds.hallucination_proxy_max,
            "drift_score_max": thresholds.drift_score_max,
            "cost_usd_per_active_couple_max": thresholds.cost_usd_per_active_couple_max,
        },
        "baseline": baseline,
        "current": current,
        "evaluation": evaluation,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print("[ai-quality-snapshot] result")
    print(f"  output: {output_path}")
    if latest_path is not None:
        print(f"  latest: {latest_path}")
    print(f"  evaluation_result: {evaluation['result']}")
    print(f"  drift_score: {evaluation['drift_score']}")
    print(f"  degraded_reasons: {evaluation['degraded_reasons']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
