#!/usr/bin/env python3
"""CUJ synthetic evidence freshness gate for release pipelines."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "docs" / "sre" / "evidence"
DEFAULT_MAX_AGE_HOURS = 36.0
MAX_AGE_HOURS_ENV_KEY = "CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS"
REQUIRE_PASS_ENV_KEY = "CUJ_SYNTHETIC_EVIDENCE_REQUIRE_PASS"
ALLOWED_RESULT_VALUES = frozenset({"pass", "fail"})
ALLOWED_STAGE_STATUS_VALUES = frozenset({"pass", "warn", "fail"})


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
    try:
        value = float(str(raw).strip())
    except ValueError as exc:
        raise ValueError("value must be numeric") from exc
    if value <= 0:
        raise ValueError("value must be greater than 0")
    return value


def _find_latest_evidence_file(evidence_dir: Path) -> Path:
    candidates = sorted(evidence_dir.glob("cuj-synthetic-*.json"))
    if not candidates:
        raise FileNotFoundError(f"no CUJ synthetic evidence found in {evidence_dir}")
    return candidates[-1]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"evidence file missing: {path}") from exc
    except OSError as exc:
        raise RuntimeError(f"unable to read evidence file: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"evidence file is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("evidence JSON root must be object")
    return payload


def _parse_generated_at(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("generated_at must include timezone")
    return parsed.astimezone(UTC)


def evaluate_cuj_synthetic_evidence(
    payload: dict[str, Any],
    *,
    max_age_hours: float,
    require_pass: bool,
    now_utc: datetime | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be greater than 0")

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

    result_value = payload.get("result")
    if not isinstance(result_value, str) or result_value not in ALLOWED_RESULT_VALUES:
        reasons.append("invalid_result")
    elif require_pass and result_value != "pass":
        reasons.append("result_not_pass")
    else:
        meta["result"] = result_value

    failure_class = payload.get("failure_class")
    if not isinstance(failure_class, str) or not failure_class.strip():
        reasons.append("invalid_failure_class")
    else:
        meta["failure_class"] = failure_class.strip()

    failed_stages = payload.get("failed_stages")
    if not isinstance(failed_stages, list) or not all(
        isinstance(item, str) and item.strip() for item in failed_stages
    ):
        reasons.append("invalid_failed_stages")
    else:
        meta["failed_stages_count"] = len(failed_stages)

    warn_stages = payload.get("warn_stages")
    if not isinstance(warn_stages, list) or not all(
        isinstance(item, str) and item.strip() for item in warn_stages
    ):
        reasons.append("invalid_warn_stages")
    else:
        meta["warn_stages_count"] = len(warn_stages)

    strict_mode = payload.get("strict_mode")
    if not isinstance(strict_mode, bool):
        reasons.append("invalid_strict_mode")

    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        reasons.append("invalid_stages")
    else:
        stage_ids: set[str] = set()
        for index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                reasons.append(f"invalid_stage_item:{index}")
                continue
            stage_name = stage.get("stage")
            stage_status = stage.get("status")
            stage_detail = stage.get("detail")
            if not isinstance(stage_name, str) or not stage_name.strip():
                reasons.append(f"invalid_stage_name:{index}")
            elif stage_name in stage_ids:
                reasons.append(f"duplicate_stage_name:{stage_name}")
            else:
                stage_ids.add(stage_name)
            if not isinstance(stage_status, str) or stage_status not in ALLOWED_STAGE_STATUS_VALUES:
                reasons.append(f"invalid_stage_status:{index}")
            if not isinstance(stage_detail, str) or not stage_detail.strip():
                reasons.append(f"invalid_stage_detail:{index}")
        required_stages = {"health_endpoint", "ws_slo_gate", "cuj_slo_gate", "cuj_01_ritual", "cuj_02_journal"}
        missing_stages = sorted(required_stages - stage_ids)
        if missing_stages:
            reasons.append(f"missing_required_stages:{','.join(missing_stages)}")
        meta["stages_count"] = len(stages)

    return len(reasons) == 0, reasons, meta


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
        print("[cuj-synthetic-evidence-gate] warn: failed to write summary")
        print(f"  path: {path}")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate CUJ synthetic evidence freshness and contract for release gates."
    )
    parser.add_argument("--evidence-dir", default=None)
    parser.add_argument("--allow-missing-evidence", action="store_true")
    parser.add_argument("--max-age-hours", type=float, default=None)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--summary-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary_path = (args.summary_path or "").strip() or None
    evidence_dir = Path((args.evidence_dir or "").strip() or str(DEFAULT_EVIDENCE_DIR))

    try:
        max_age_hours = (
            float(args.max_age_hours)
            if args.max_age_hours is not None
            else _parse_positive_float(os.getenv(MAX_AGE_HOURS_ENV_KEY), default=DEFAULT_MAX_AGE_HOURS)
        )
    except ValueError as exc:
        print("[cuj-synthetic-evidence-gate] fail: invalid max age")
        print(f"  detail: {exc}")
        _write_summary(summary_path, result="fail", reasons=["invalid_max_age_hours"], meta={})
        return 1

    require_pass = args.require_pass or _parse_bool(os.getenv(REQUIRE_PASS_ENV_KEY), default=False)

    print("[cuj-synthetic-evidence-gate] checking evidence")
    print(f"  evidence_dir: {evidence_dir}")
    print(f"  max_age_hours: {max_age_hours}")
    print(f"  require_pass: {'yes' if require_pass else 'no'}")

    try:
        evidence_path = _find_latest_evidence_file(evidence_dir)
    except FileNotFoundError as exc:
        if args.allow_missing_evidence:
            print("[cuj-synthetic-evidence-gate] skipped: missing evidence")
            print(f"  detail: {exc}")
            _write_summary(
                summary_path,
                result="skip",
                reasons=["missing_evidence"],
                meta={"evidence_dir": str(evidence_dir)},
            )
            return 0
        print("[cuj-synthetic-evidence-gate] fail: missing evidence")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            result="fail",
            reasons=["missing_evidence"],
            meta={"evidence_dir": str(evidence_dir)},
        )
        return 1

    try:
        payload = _load_json(evidence_path)
    except RuntimeError as exc:
        print("[cuj-synthetic-evidence-gate] fail: invalid evidence file")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            result="fail",
            reasons=["invalid_evidence_file"],
            meta={"evidence_path": str(evidence_path)},
        )
        return 1

    passed, reasons, meta = evaluate_cuj_synthetic_evidence(
        payload,
        max_age_hours=max_age_hours,
        require_pass=require_pass,
    )
    meta["evidence_path"] = str(evidence_path)
    if "age_hours" in meta:
        print(f"  evidence_age_hours: {meta['age_hours']}")
    print(f"  evidence_result: {meta.get('result', 'unknown')}")
    print(f"  failure_class: {meta.get('failure_class', 'unknown')}")

    if not passed:
        print("[cuj-synthetic-evidence-gate] result: fail")
        print("  reasons:")
        for reason in reasons:
            print(f"    - {reason}")
        _write_summary(summary_path, result="fail", reasons=reasons, meta=meta)
        return 1

    print("[cuj-synthetic-evidence-gate] result: pass")
    _write_summary(summary_path, result="pass", reasons=[], meta=meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
