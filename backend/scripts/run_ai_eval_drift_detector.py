#!/usr/bin/env python3
"""Generate AI eval drift detector evidence from latest quality snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

DEFAULT_SNAPSHOT_PATH = REPO_ROOT / "docs" / "security" / "evidence" / "ai-quality-snapshot-latest.json"
DEFAULT_POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-cost-quality-policy.json"
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
DEFAULT_LATEST_PATH = DEFAULT_EVIDENCE_DIR / "ai-eval-drift-latest.json"
DEFAULT_CRITICAL_MULTIPLIER = 1.5


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate AI eval drift detector evidence")
    parser.add_argument(
        "--snapshot",
        default=str(DEFAULT_SNAPSHOT_PATH),
        help="Path to ai-quality-snapshot evidence JSON.",
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY_PATH),
        help="Path to ai-cost-quality-policy JSON.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON path. Defaults to docs/security/evidence/ai-eval-drift-<timestamp>.json",
    )
    parser.add_argument(
        "--latest-path",
        default=str(DEFAULT_LATEST_PATH),
        help="Path to write latest drift detector pointer file.",
    )
    parser.add_argument(
        "--critical-multiplier",
        type=float,
        default=DEFAULT_CRITICAL_MULTIPLIER,
        help="Critical threshold multiplier over drift_score_max (default 1.5).",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="Optional summary output JSON path for CI workflow consumption.",
    )
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Return exit code 1 on degraded/critical result.",
    )
    return parser


def _resolve_output_path(output: str) -> Path:
    cleaned = str(output or "").strip()
    if cleaned:
        return Path(cleaned).resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (DEFAULT_EVIDENCE_DIR / f"ai-eval-drift-{timestamp}.json").resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _evaluate_drift(
    *,
    drift_score: float,
    drift_score_max: float,
    critical_multiplier: float,
) -> tuple[str, list[str], dict[str, float]]:
    drift_score_critical = drift_score_max * critical_multiplier
    reasons: list[str] = []
    result = "pass"
    if drift_score > drift_score_critical:
        result = "critical"
        reasons.append("drift_score_above_critical")
    elif drift_score > drift_score_max:
        result = "degraded"
        reasons.append("drift_score_above_max")
    return result, reasons, {
        "drift_score_max": drift_score_max,
        "drift_score_critical": drift_score_critical,
        "critical_multiplier": critical_multiplier,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot).resolve()
    policy_path = Path(args.policy).resolve()

    if not snapshot_path.exists():
        print(f"[ai-eval-drift] fail: snapshot not found: {snapshot_path}")
        return 1
    if not policy_path.exists():
        print(f"[ai-eval-drift] fail: policy not found: {policy_path}")
        return 1
    if args.critical_multiplier <= 1.0:
        print("[ai-eval-drift] fail: --critical-multiplier must be > 1.0")
        return 1

    snapshot = _load_json(snapshot_path)
    policy = _load_json(policy_path)

    evaluation = snapshot.get("evaluation")
    if not isinstance(evaluation, dict):
        print("[ai-eval-drift] fail: snapshot missing evaluation object")
        return 1

    drift_score = _as_float(evaluation.get("drift_score"))
    if drift_score is None:
        print("[ai-eval-drift] fail: snapshot evaluation.drift_score missing/invalid")
        return 1

    policy_thresholds = policy.get("thresholds")
    snapshot_thresholds = snapshot.get("thresholds")
    drift_score_max = None
    if isinstance(policy_thresholds, dict):
        drift_score_max = _as_float(policy_thresholds.get("drift_score_max"))
    if drift_score_max is None and isinstance(snapshot_thresholds, dict):
        drift_score_max = _as_float(snapshot_thresholds.get("drift_score_max"))
    if drift_score_max is None or drift_score_max <= 0:
        print("[ai-eval-drift] fail: drift_score_max missing/invalid from policy+snapshot")
        return 1

    result, reasons, thresholds = _evaluate_drift(
        drift_score=drift_score,
        drift_score_max=drift_score_max,
        critical_multiplier=float(args.critical_multiplier),
    )

    now = datetime.now(UTC)
    payload = {
        "artifact_kind": "ai-eval-drift-detector",
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "generated_by": "backend/scripts/run_ai_eval_drift_detector.py",
        "source": {
            "snapshot_path": str(snapshot_path),
            "snapshot_generated_at": snapshot.get("generated_at"),
            "policy_path": str(policy_path),
            "policy_schema_version": policy.get("schema_version"),
        },
        "detector": {
            "mode": "relative_delta_average",
            "fallback_behavior": "degrade_but_do_not_block_journal_write",
        },
        "thresholds": thresholds,
        "evaluation": {
            "result": result,
            "alert_open": result in {"degraded", "critical"},
            "reasons": reasons,
            "drift_score": drift_score,
            "source_evaluation_result": evaluation.get("result"),
            "source_degraded_reasons": evaluation.get("degraded_reasons") or [],
        },
    }

    output_path = _resolve_output_path(args.output)
    _write_json(output_path, payload)

    latest_path = Path(args.latest_path).resolve() if str(args.latest_path or "").strip() else None
    if latest_path is not None:
        _write_json(latest_path, payload)

    summary_payload = {
        "result": result,
        "reasons": reasons,
        "meta": {
            "drift_score": drift_score,
            "drift_score_max": thresholds["drift_score_max"],
            "drift_score_critical": thresholds["drift_score_critical"],
            "critical_multiplier": thresholds["critical_multiplier"],
            "source_evaluation_result": evaluation.get("result"),
        },
        "artifact_path": str(output_path),
    }
    if str(args.summary_path or "").strip():
        _write_json(Path(args.summary_path).resolve(), summary_payload)

    print("[ai-eval-drift] result")
    print(f"  output: {output_path}")
    if latest_path is not None:
        print(f"  latest: {latest_path}")
    print(f"  result: {result}")
    print(f"  drift_score: {drift_score}")
    print(f"  drift_score_max: {thresholds['drift_score_max']}")
    print(f"  drift_score_critical: {thresholds['drift_score_critical']}")
    print(f"  reasons: {reasons}")

    if bool(args.fail_on_alert) and result in {"degraded", "critical"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
