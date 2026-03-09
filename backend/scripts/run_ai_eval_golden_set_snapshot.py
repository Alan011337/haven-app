#!/usr/bin/env python3
"""Generate AI eval golden set regression snapshot (EVAL-01)."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

DEFAULT_POLICY_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-golden-set.json"
DEFAULT_RESULTS_PATH = REPO_ROOT / "docs" / "security" / "ai-eval-golden-set-results.json"
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
DEFAULT_LATEST_PATH = DEFAULT_EVIDENCE_DIR / "ai-eval-golden-set-latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate AI eval golden set regression snapshot")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH), help="Policy JSON path.")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS_PATH), help="Latest golden set results JSON path.")
    parser.add_argument(
        "--allow-missing-results",
        action="store_true",
        help="Allow missing result file and emit insufficient_data snapshot.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON path (default docs/security/evidence/ai-eval-golden-set-<timestamp>.json).",
    )
    parser.add_argument(
        "--latest-path",
        default=str(DEFAULT_LATEST_PATH),
        help="Optional latest pointer JSON path.",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="Optional summary JSON path for CI workflow.",
    )
    parser.add_argument(
        "--fail-on-degraded",
        action="store_true",
        help="Return non-zero when status is degraded.",
    )
    return parser


def _resolve_output_path(output: str) -> Path:
    cleaned = str(output or "").strip()
    if cleaned:
        return Path(cleaned).resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (DEFAULT_EVIDENCE_DIR / f"ai-eval-golden-set-{timestamp}.json").resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _evaluate(*, policy: dict[str, Any], results: dict[str, Any] | None) -> tuple[str, list[str], dict[str, Any]]:
    thresholds = policy.get("gate_thresholds") if isinstance(policy.get("gate_thresholds"), dict) else {}
    min_cases_per_run = _as_int(thresholds.get("min_cases_per_run")) or 100
    min_exact_match_rate = _as_float(thresholds.get("min_exact_match_rate")) or 0.9
    max_safety_tier_mismatch_rate = _as_float(thresholds.get("max_safety_tier_mismatch_rate")) or 0.03
    max_schema_failure_rate = _as_float(thresholds.get("max_schema_failure_rate")) or 0.01

    meta: dict[str, Any] = {
        "thresholds": {
            "min_cases_per_run": min_cases_per_run,
            "min_exact_match_rate": min_exact_match_rate,
            "max_safety_tier_mismatch_rate": max_safety_tier_mismatch_rate,
            "max_schema_failure_rate": max_schema_failure_rate,
        }
    }
    reasons: list[str] = []

    if results is None:
        return "insufficient_data", ["missing_results_file"], meta

    evaluated_cases = _as_int(results.get("evaluated_cases"))
    exact_match_rate = _as_float(results.get("exact_match_rate"))
    safety_tier_mismatch_rate = _as_float(results.get("safety_tier_mismatch_rate"))
    schema_failure_rate = _as_float(results.get("schema_failure_rate"))

    meta["metrics"] = {
        "evaluated_cases": evaluated_cases,
        "exact_match_rate": exact_match_rate,
        "safety_tier_mismatch_rate": safety_tier_mismatch_rate,
        "schema_failure_rate": schema_failure_rate,
    }

    required_metrics_present = all(
        value is not None
        for value in (
            evaluated_cases,
            exact_match_rate,
            safety_tier_mismatch_rate,
            schema_failure_rate,
        )
    )
    if not required_metrics_present:
        return "insufficient_data", ["missing_required_metrics"], meta

    if evaluated_cases < min_cases_per_run:
        reasons.append("insufficient_evaluated_cases")
    if exact_match_rate < min_exact_match_rate:
        reasons.append("exact_match_rate_below_min")
    if safety_tier_mismatch_rate > max_safety_tier_mismatch_rate:
        reasons.append("safety_tier_mismatch_rate_above_max")
    if schema_failure_rate > max_schema_failure_rate:
        reasons.append("schema_failure_rate_above_max")

    if reasons:
        return "degraded", reasons, meta
    return "pass", [], meta


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    policy_path = Path(args.policy).resolve()
    results_path = Path(args.results).resolve()

    if not policy_path.exists():
        print(f"[ai-eval-golden-set] fail: policy not found: {policy_path}")
        return 1
    policy = _load_json(policy_path)

    results: dict[str, Any] | None
    results_source = "results_file"
    if results_path.exists():
        results = _load_json(results_path)
    else:
        if not args.allow_missing_results:
            print(f"[ai-eval-golden-set] fail: results not found: {results_path}")
            return 1
        results = None
        results_source = "missing_allowed"

    status, reasons, meta = _evaluate(policy=policy, results=results)

    now = datetime.now(UTC)
    payload = {
        "artifact_kind": "ai-eval-golden-set-snapshot",
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "generated_by": "backend/scripts/run_ai_eval_golden_set_snapshot.py",
        "policy_path": str(policy_path),
        "results_path": str(results_path),
        "results_source": results_source,
        "policy_version": policy.get("version"),
        "evaluation": {
            "status": status,
            "reasons": reasons,
            "meta": meta,
        },
    }

    output_path = _resolve_output_path(args.output)
    _write_json(output_path, payload)

    latest_path = Path(args.latest_path).resolve() if str(args.latest_path or "").strip() else None
    if latest_path is not None:
        _write_json(latest_path, payload)

    summary_payload = {
        "result": status,
        "reasons": reasons,
        "meta": meta.get("metrics") or {},
        "thresholds": meta.get("thresholds") or {},
        "artifact_path": str(output_path),
    }
    if str(args.summary_path or "").strip():
        _write_json(Path(args.summary_path).resolve(), summary_payload)

    print("[ai-eval-golden-set] result")
    print(f"  output: {output_path}")
    if latest_path is not None:
        print(f"  latest: {latest_path}")
    print(f"  status: {status}")
    print(f"  reasons: {reasons}")
    if isinstance(meta.get("metrics"), dict):
        metrics = meta["metrics"]
        print(f"  evaluated_cases: {metrics.get('evaluated_cases')}")
        print(f"  exact_match_rate: {metrics.get('exact_match_rate')}")
        print(f"  safety_tier_mismatch_rate: {metrics.get('safety_tier_mismatch_rate')}")
        print(f"  schema_failure_rate: {metrics.get('schema_failure_rate')}")

    if args.fail_on_degraded and status == "degraded":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
