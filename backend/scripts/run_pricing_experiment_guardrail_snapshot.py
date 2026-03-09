#!/usr/bin/env python3
"""Generate pricing experiment guardrail snapshot evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pricing_experiment_runtime import (  # noqa: E402
    evaluate_pricing_experiment_guardrails,
    pricing_experiment_runtime_metrics,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "security" / "evidence"
DEFAULT_LATEST_PATH = DEFAULT_OUTPUT_DIR / "pricing-experiment-guardrail-latest.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate pricing experiment guardrail snapshot evidence.")
    parser.add_argument(
        "--metrics-path",
        default="",
        help=(
            "Optional JSON path containing metric values. Supports direct map "
            "or object with `metrics` field."
        ),
    )
    parser.add_argument(
        "--allow-missing-metrics",
        action="store_true",
        help="Allow missing metrics path and emit insufficient_data snapshot.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON path. Defaults to docs/security/evidence/pricing-experiment-guardrail-<timestamp>.json",
    )
    parser.add_argument(
        "--latest-path",
        default=str(DEFAULT_LATEST_PATH),
        help="Path to also write latest snapshot pointer file.",
    )
    parser.add_argument(
        "--fail-on-triggered",
        action="store_true",
        help="Return exit code 1 when guardrail status is triggered.",
    )
    return parser


def _load_metrics_map(*, metrics_path: str, allow_missing_metrics: bool) -> dict[str, Any]:
    path_value = str(metrics_path or "").strip()
    if not path_value:
        return {}

    path = Path(path_value).resolve()
    if not path.exists():
        if allow_missing_metrics:
            return {}
        raise FileNotFoundError(f"metrics file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        nested = raw.get("metrics")
        if isinstance(nested, dict):
            return nested
        return raw
    return {}


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _resolve_output_path(output: str) -> Path:
    cleaned = str(output or "").strip()
    if cleaned:
        return Path(cleaned).resolve()
    return (DEFAULT_OUTPUT_DIR / f"pricing-experiment-guardrail-{_timestamp()}.json").resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        metric_values = _load_metrics_map(
            metrics_path=args.metrics_path,
            allow_missing_metrics=bool(args.allow_missing_metrics),
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[pricing-experiment-guardrail] fail: {exc}")
        return 1

    evaluation = evaluate_pricing_experiment_guardrails(metric_values=metric_values)
    now = datetime.now(UTC)

    payload = {
        "artifact_kind": "pricing-experiment-guardrail-snapshot",
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "generated_by": "backend/scripts/run_pricing_experiment_guardrail_snapshot.py",
        "metrics": metric_values,
        "evaluation": evaluation,
        "runtime_snapshot": pricing_experiment_runtime_metrics.snapshot(),
    }

    output_path = _resolve_output_path(args.output)
    _write_json(output_path, payload)
    latest_path = Path(args.latest_path).resolve() if str(args.latest_path).strip() else None
    if latest_path is not None:
        _write_json(latest_path, payload)

    print("[pricing-experiment-guardrail] result")
    print(f"  output: {output_path}")
    if latest_path is not None:
        print(f"  latest: {latest_path}")
    print(f"  status: {evaluation.get('status')}")
    print(f"  breaches: {len(evaluation.get('breaches') or [])}")
    print(f"  missing_metrics: {len(evaluation.get('missing_metrics') or [])}")

    if bool(args.fail_on_triggered) and str(evaluation.get("status") or "").strip().lower() == "triggered":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
