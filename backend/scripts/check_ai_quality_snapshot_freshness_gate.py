#!/usr/bin/env python3
"""AI quality snapshot evidence freshness gate for release pipelines."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_PATH = REPO_ROOT / "docs" / "security" / "evidence" / "ai-quality-snapshot-latest.json"
DEFAULT_MAX_AGE_HOURS = 36.0
MAX_AGE_HOURS_ENV_KEY = "AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS"
REQUIRE_PASS_ENV_KEY = "AI_QUALITY_SNAPSHOT_REQUIRE_PASS"
ALLOWED_RESULTS = frozenset({"pass", "degraded"})


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_positive_float(raw: str | None, *, default: float) -> float:
    if raw is None or str(raw).strip() == "":
        return default
    value = float(str(raw).strip())
    if value <= 0:
        raise ValueError("value must be greater than 0")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("snapshot root must be an object")
    return payload


def _parse_generated_at(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def evaluate_ai_quality_snapshot(
    payload: dict[str, Any],
    *,
    max_age_hours: float,
    require_pass: bool,
    now_utc: datetime | None = None,
) -> tuple[bool, str, list[str], dict[str, Any]]:
    reasons: list[str] = []
    meta: dict[str, Any] = {"require_pass": require_pass, "max_age_hours": max_age_hours}

    generated_at_raw = payload.get("generated_at")
    if not isinstance(generated_at_raw, str) or not generated_at_raw.strip():
        reasons.append("missing_generated_at")
    else:
        try:
            generated_at = _parse_generated_at(generated_at_raw)
        except ValueError:
            reasons.append("invalid_generated_at")
        else:
            now = now_utc.astimezone(UTC) if now_utc else datetime.now(UTC)
            age_seconds = (now - generated_at).total_seconds()
            if age_seconds < 0:
                reasons.append("generated_at_in_future")
            else:
                age_hours = round(age_seconds / 3600.0, 2)
                meta["age_hours"] = age_hours
                if age_hours > max_age_hours:
                    reasons.append("evidence_stale")

    artifact_kind = payload.get("artifact_kind")
    if artifact_kind != "ai-quality-snapshot":
        reasons.append("invalid_artifact_kind")

    evaluation = payload.get("evaluation")
    if not isinstance(evaluation, dict):
        reasons.append("missing_evaluation")
        result_value = "fail"
    else:
        result_value = str(evaluation.get("result") or "").strip().lower()
        if result_value not in ALLOWED_RESULTS:
            reasons.append("invalid_evaluation_result")
            result_value = "fail"
        else:
            meta["evaluation_result"] = result_value
            degraded_reasons = evaluation.get("degraded_reasons")
            if result_value == "degraded":
                if not isinstance(degraded_reasons, list):
                    reasons.append("invalid_degraded_reasons")
                else:
                    meta["degraded_reasons"] = [str(item) for item in degraded_reasons]
            if require_pass and result_value != "pass":
                reasons.append("evaluation_not_pass")

    if reasons:
        return False, "fail", reasons, meta
    if result_value == "degraded":
        return True, "degraded", [], meta
    return True, "pass", [], meta


def _write_summary(path: str | None, *, result: str, reasons: list[str], meta: dict[str, Any]) -> None:
    if not path:
        return
    payload = {"result": result, "reasons": reasons, "meta": meta}
    try:
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print("[ai-quality-snapshot-gate] warn: failed to write summary")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate AI quality snapshot evidence freshness and contract."
    )
    parser.add_argument("--evidence", default=None, help="Path to AI quality snapshot JSON")
    parser.add_argument("--allow-missing-evidence", action="store_true")
    parser.add_argument("--max-age-hours", type=float, default=None)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--summary-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary_path = (args.summary_path or "").strip() or None
    evidence_path = Path((args.evidence or "").strip() or str(DEFAULT_EVIDENCE_PATH))

    try:
        max_age_hours = (
            float(args.max_age_hours)
            if args.max_age_hours is not None
            else _parse_positive_float(os.getenv(MAX_AGE_HOURS_ENV_KEY), default=DEFAULT_MAX_AGE_HOURS)
        )
    except ValueError as exc:
        print("[ai-quality-snapshot-gate] fail: invalid max age")
        print(f"  detail: {exc}")
        _write_summary(summary_path, result="fail", reasons=["invalid_max_age_hours"], meta={})
        return 1

    require_pass = args.require_pass or _parse_bool(os.getenv(REQUIRE_PASS_ENV_KEY), default=False)

    print("[ai-quality-snapshot-gate] checking evidence")
    print(f"  evidence_path: {evidence_path}")
    print(f"  max_age_hours: {max_age_hours}")
    print(f"  require_pass: {'yes' if require_pass else 'no'}")

    if not evidence_path.exists():
        if args.allow_missing_evidence:
            print("[ai-quality-snapshot-gate] skipped: missing evidence")
            _write_summary(
                summary_path,
                result="skip",
                reasons=["missing_evidence"],
                meta={"evidence_path": str(evidence_path)},
            )
            return 0
        print("[ai-quality-snapshot-gate] fail: missing evidence")
        _write_summary(
            summary_path,
            result="fail",
            reasons=["missing_evidence"],
            meta={"evidence_path": str(evidence_path)},
        )
        return 1

    try:
        payload = _load_json(evidence_path)
    except Exception as exc:
        print("[ai-quality-snapshot-gate] fail: invalid evidence")
        print(f"  detail: {type(exc).__name__}")
        _write_summary(
            summary_path,
            result="fail",
            reasons=["invalid_evidence_file"],
            meta={"evidence_path": str(evidence_path)},
        )
        return 1

    passed, result, reasons, meta = evaluate_ai_quality_snapshot(
        payload,
        max_age_hours=max_age_hours,
        require_pass=require_pass,
    )
    meta["evidence_path"] = str(evidence_path)
    print(f"  evaluation_result: {meta.get('evaluation_result', 'unknown')}")
    if "age_hours" in meta:
        print(f"  evidence_age_hours: {meta['age_hours']}")

    if not passed:
        print("[ai-quality-snapshot-gate] result: fail")
        print("  reasons:")
        for reason in reasons:
            print(f"    - {reason}")
        _write_summary(summary_path, result="fail", reasons=reasons, meta=meta)
        return 1

    print(f"[ai-quality-snapshot-gate] result: {result}")
    _write_summary(summary_path, result=result, reasons=[], meta=meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
