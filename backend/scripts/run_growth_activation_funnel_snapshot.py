#!/usr/bin/env python3
"""Generate growth activation funnel snapshot evidence."""

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
from app.services.growth_activation_runtime import (  # noqa: E402
    DEFAULT_MIN_SIGNUPS,
    DEFAULT_TARGET_BIND_RATE,
    DEFAULT_TARGET_FIRST_DECK_RATE,
    DEFAULT_TARGET_FIRST_JOURNAL_RATE,
    DEFAULT_WINDOW_DAYS,
    build_growth_activation_funnel_snapshot,
    evaluate_growth_activation_funnel_snapshot,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "growth" / "evidence"
DEFAULT_LATEST_PATH = DEFAULT_OUTPUT_DIR / "activation-funnel-snapshot-latest.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate growth activation funnel snapshot evidence.")
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help="Rolling window in days.",
    )
    parser.add_argument(
        "--min-signups",
        type=int,
        default=DEFAULT_MIN_SIGNUPS,
        help="Minimum signup sample size before evaluation leaves insufficient-data.",
    )
    parser.add_argument(
        "--target-bind-rate",
        type=float,
        default=DEFAULT_TARGET_BIND_RATE,
        help="Target bind conversion ratio from signup cohort.",
    )
    parser.add_argument(
        "--target-first-journal-rate",
        type=float,
        default=DEFAULT_TARGET_FIRST_JOURNAL_RATE,
        help="Target first journal conversion ratio from signup cohort.",
    )
    parser.add_argument(
        "--target-first-deck-rate",
        type=float,
        default=DEFAULT_TARGET_FIRST_DECK_RATE,
        help="Target first deck conversion ratio from signup cohort.",
    )
    parser.add_argument(
        "--output",
        default="",
        help=(
            "Output JSON path. Defaults to "
            "docs/growth/evidence/activation-funnel-snapshot-<timestamp>.json"
        ),
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


def parse_args_for(argv: list[str]) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        snapshot = build_growth_activation_funnel_snapshot(
            session=session,
            window_days=args.window_days,
        )
    evaluation = evaluate_growth_activation_funnel_snapshot(
        snapshot,
        min_signups=args.min_signups,
        target_bind_rate=args.target_bind_rate,
        target_first_journal_rate=args.target_first_journal_rate,
        target_first_deck_rate=args.target_first_deck_rate,
    )

    now = datetime.now(UTC)
    return {
        "artifact_kind": "growth-activation-funnel-snapshot",
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "generated_by": "backend/scripts/run_growth_activation_funnel_snapshot.py",
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
        else (DEFAULT_OUTPUT_DIR / f"activation-funnel-snapshot-{timestamp}.json").resolve()
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

    snapshot = payload.get("snapshot") or {}
    evaluation = payload.get("evaluation") or {}
    counts = snapshot.get("counts") or {}
    metrics = snapshot.get("metrics") or {}

    print("[growth-activation-funnel] result")
    print(f"  output: {output_path}")
    if latest_path is not None:
        print(f"  latest: {latest_path}")
    print(f"  snapshot_status: {snapshot.get('status', 'unknown')}")
    print(f"  evaluation_status: {evaluation.get('status', 'unknown')}")
    print(f"  signup_completed_users: {counts.get('signup_completed_users')}")
    print(f"  partner_bound_users: {counts.get('partner_bound_users')}")
    print(f"  first_journal_users: {counts.get('first_journal_users')}")
    print(f"  first_deck_users: {counts.get('first_deck_users')}")
    print(f"  bind_rate: {metrics.get('bind_rate')}")
    print(f"  first_journal_rate: {metrics.get('first_journal_rate')}")
    print(f"  first_deck_rate: {metrics.get('first_deck_rate')}")

    if args.fail_on_degraded and str(evaluation.get("status") or "").strip().lower() == "degraded":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
