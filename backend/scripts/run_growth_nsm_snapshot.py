#!/usr/bin/env python3
"""Generate Growth NSM (WRM) snapshot evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import SQLModel, Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import engine  # noqa: E402
from app.services.growth_nsm_runtime import (  # noqa: E402
    DEFAULT_MIN_EVENTS,
    DEFAULT_MIN_PAIRS,
    DEFAULT_TARGET_WRM_ACTIVE_PAIR_RATE,
    DEFAULT_WINDOW_DAYS,
    build_growth_nsm_snapshot,
    evaluate_growth_nsm_snapshot,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "growth" / "evidence"
DEFAULT_LATEST_PATH = DEFAULT_OUTPUT_DIR / "wrm-snapshot-latest.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Growth NSM WRM snapshot evidence.")
    parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS, help="Rolling window in days.")
    parser.add_argument(
        "--min-events",
        type=int,
        default=DEFAULT_MIN_EVENTS,
        help="Minimum eligible event count before evaluation leaves insufficient-data.",
    )
    parser.add_argument(
        "--min-pairs",
        type=int,
        default=DEFAULT_MIN_PAIRS,
        help="Minimum active pair count before evaluation leaves insufficient-data.",
    )
    parser.add_argument(
        "--target-wrm-active-pair-rate",
        type=float,
        default=DEFAULT_TARGET_WRM_ACTIVE_PAIR_RATE,
        help="Target active pair WRM conversion rate.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON path. Defaults to docs/growth/evidence/wrm-snapshot-<timestamp>.json",
    )
    parser.add_argument(
        "--latest-path",
        default=str(DEFAULT_LATEST_PATH),
        help="Path to also write latest snapshot pointer JSON.",
    )
    parser.add_argument(
        "--fail-on-degraded",
        action="store_true",
        help="Return exit code 1 when evaluation result is degraded.",
    )
    return parser


def parse_args() -> argparse.Namespace:
    return _build_parser().parse_args()


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        snapshot = build_growth_nsm_snapshot(session=session, window_days=args.window_days)
    evaluation = evaluate_growth_nsm_snapshot(
        snapshot,
        min_events=args.min_events,
        min_pairs=args.min_pairs,
        target_wrm_active_pair_rate=args.target_wrm_active_pair_rate,
    )

    now = datetime.now(UTC)
    return {
        "artifact_kind": "growth-nsm-snapshot",
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "generated_by": "backend/scripts/run_growth_nsm_snapshot.py",
        "metric": "WRM",
        "snapshot": snapshot,
        "evaluation": evaluation,
    }


def _timestamp_from_generated_at(generated_at: str) -> str:
    text = generated_at.strip()
    if not text:
        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return parsed.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _resolve_paths(args: argparse.Namespace, payload: dict[str, Any]) -> tuple[Path, Path | None]:
    generated_at = str(payload.get("generated_at") or "").strip()
    timestamp = _timestamp_from_generated_at(generated_at)
    output_path = (
        Path(args.output).resolve()
        if str(args.output).strip()
        else (DEFAULT_OUTPUT_DIR / f"wrm-snapshot-{timestamp}.json").resolve()
    )
    latest_path = Path(args.latest_path).resolve() if str(args.latest_path).strip() else None
    return output_path, latest_path


def _write_payload(*, output_path: Path, latest_path: Path | None, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
    output_path.write_text(serialized, encoding="utf-8")
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(serialized, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args() if argv is None else parse_args_for(argv)
    payload = _build_payload(args)
    output_path, latest_path = _resolve_paths(args, payload)
    _write_payload(output_path=output_path, latest_path=latest_path, payload=payload)

    evaluation = payload.get("evaluation") or {}
    status = str(evaluation.get("status") or "unknown")
    reasons = evaluation.get("reasons") or []
    snapshot = payload.get("snapshot") or {}
    metrics = snapshot.get("metrics") or {}

    print("[growth-nsm-snapshot] result")
    print(f"  output: {output_path}")
    if latest_path is not None:
        print(f"  latest: {latest_path}")
    print(f"  evaluation_status: {status}")
    print(f"  wrm_pairs_total: {metrics.get('wrm_pairs_total')}")
    print(f"  wrm_active_pair_rate: {metrics.get('wrm_active_pair_rate')}")
    print(f"  reasons: {reasons}")

    if args.fail_on_degraded and status == "degraded":
        return 1
    return 0


def parse_args_for(argv: list[str]) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
