#!/usr/bin/env python3
"""Launch signoff artifact freshness gate for release pipelines."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_PATH = REPO_ROOT / "docs" / "security" / "evidence" / "p0-readiness-latest.json"
ARTIFACT_PATH_ENV_KEY = "LAUNCH_SIGNOFF_ARTIFACT_PATH"
MAX_AGE_DAYS_ENV_KEY = "LAUNCH_SIGNOFF_MAX_AGE_DAYS"
REQUIRE_READY_ENV_KEY = "LAUNCH_SIGNOFF_REQUIRE_READY"
DEFAULT_MAX_AGE_DAYS = 14
ALLOWED_CHECK_STATUSES = frozenset({"pass", "fail", "skip"})
REQUIRED_CHECK_IDS = frozenset(
    {
        "release_checklist_complete",
        "launch_gate_complete",
        "store_compliance_contract_passed",
        "release_gate_local_runtime",
    }
)


def _parse_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_positive_int(raw: str | None, *, default: int) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise ValueError("value must be an integer") from exc
    if value <= 0:
        raise ValueError("value must be greater than 0")
    return value


def _load_artifact(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"artifact file not found: {path}") from exc
    except OSError as exc:
        raise RuntimeError(f"unable to read artifact file: {path}: {exc}") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"artifact is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("artifact root must be an object")
    return payload


def _parse_generated_at(raw: str) -> datetime:
    compact = raw.strip()
    try:
        return datetime.strptime(compact, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(compact.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("generated_at_utc must be compact or ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("generated_at_utc timestamp must include timezone")
    return parsed.astimezone(UTC)


def evaluate_launch_signoff_artifact(
    payload: dict[str, Any],
    *,
    max_age_days: int,
    require_ready: bool,
    now_utc: datetime | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    if max_age_days <= 0:
        raise ValueError("max_age_days must be greater than 0")

    reasons: list[str] = []
    meta: dict[str, Any] = {}

    generated_at_raw = payload.get("generated_at_utc")
    if not isinstance(generated_at_raw, str) or not generated_at_raw.strip():
        reasons.append("missing_generated_at_utc")
        return False, reasons, meta

    try:
        generated_at = _parse_generated_at(generated_at_raw)
    except ValueError:
        reasons.append("invalid_generated_at_utc")
        return False, reasons, meta

    current = now_utc.astimezone(UTC) if now_utc else datetime.now(UTC)
    age_seconds = (current - generated_at).total_seconds()
    if age_seconds < 0:
        reasons.append("generated_at_in_future")
    else:
        max_age_seconds = float(max_age_days) * 24 * 60 * 60
        if age_seconds > max_age_seconds:
            reasons.append("artifact_stale")
        meta["age_hours"] = round(age_seconds / 3600, 2)

    checks = payload.get("checks")
    if not isinstance(checks, list):
        reasons.append("missing_checks")
        return False, reasons, meta

    check_ids: set[str] = set()
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            reasons.append(f"invalid_check_entry:{index}")
            continue
        check_id = item.get("id")
        status = item.get("status")
        if not isinstance(check_id, str) or not check_id.strip():
            reasons.append(f"invalid_check_id:{index}")
            continue
        check_ids.add(check_id.strip())
        if not isinstance(status, str) or status.strip() not in ALLOWED_CHECK_STATUSES:
            reasons.append(f"invalid_check_status:{check_id}")

    missing_required_ids = sorted(REQUIRED_CHECK_IDS - check_ids)
    if missing_required_ids:
        reasons.append(f"missing_required_checks:{','.join(missing_required_ids)}")

    overall_ready = payload.get("overall_ready")
    if not isinstance(overall_ready, bool):
        reasons.append("invalid_overall_ready")
    elif require_ready and not overall_ready:
        reasons.append("overall_not_ready")

    meta["generated_at_utc"] = generated_at.isoformat()
    meta["overall_ready"] = overall_ready if isinstance(overall_ready, bool) else None
    meta["required_checks_present"] = not missing_required_ids
    meta["max_age_days"] = max_age_days
    meta["require_ready"] = require_ready

    return len(reasons) == 0, reasons, meta


def _write_summary(path: str | None, *, result: str, reasons: list[str], meta: dict[str, Any]) -> None:
    if not path:
        return
    payload = {
        "result": result,
        "reasons": reasons,
        "meta": meta,
    }
    try:
        Path(path).write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print("[launch-signoff-gate] warn: failed to write summary")
        print(f"  path: {path}")
        print(f"  detail: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate launch signoff artifact freshness and required check coverage "
            "before release."
        )
    )
    parser.add_argument(
        "--artifact-path",
        default=None,
        help=f"Path to launch artifact JSON. Defaults to ${ARTIFACT_PATH_ENV_KEY} or {DEFAULT_ARTIFACT_PATH}.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help=f"Maximum artifact age in days. Defaults to ${MAX_AGE_DAYS_ENV_KEY} or {DEFAULT_MAX_AGE_DAYS}.",
    )
    parser.add_argument(
        "--allow-missing-artifact",
        action="store_true",
        help="Return success when launch artifact file is missing.",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help=f"Also require `overall_ready=true` (can be set by ${REQUIRE_READY_ENV_KEY}=1).",
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Optional path to write JSON summary for CI step summaries.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    raw_artifact_path = (args.artifact_path or os.getenv(ARTIFACT_PATH_ENV_KEY) or "").strip()
    artifact_path = Path(raw_artifact_path) if raw_artifact_path else DEFAULT_ARTIFACT_PATH

    max_age_raw = (
        str(args.max_age_days)
        if args.max_age_days is not None
        else os.getenv(MAX_AGE_DAYS_ENV_KEY)
    )
    try:
        max_age_days = _parse_positive_int(max_age_raw, default=DEFAULT_MAX_AGE_DAYS)
    except ValueError as exc:
        print("[launch-signoff-gate] fail: invalid max age")
        print(f"  detail: {exc}")
        return 1

    require_ready = args.require_ready or _parse_bool(os.getenv(REQUIRE_READY_ENV_KEY), default=False)
    summary_path = (args.summary_path or "").strip() or None

    print("[launch-signoff-gate] checking launch signoff artifact")
    print(f"  artifact_path: {artifact_path}")
    print(f"  max_age_days: {max_age_days}")
    print(f"  require_ready: {'yes' if require_ready else 'no'}")

    try:
        payload = _load_artifact(artifact_path)
    except RuntimeError as exc:
        if args.allow_missing_artifact and "not found" in str(exc):
            print("[launch-signoff-gate] skipped: missing artifact")
            print(f"  detail: {exc}")
            _write_summary(
                summary_path,
                result="skip",
                reasons=["missing_artifact"],
                meta={"artifact_path": str(artifact_path)},
            )
            return 0
        print("[launch-signoff-gate] fail: unable to load artifact")
        print(f"  detail: {exc}")
        _write_summary(
            summary_path,
            result="fail",
            reasons=["artifact_load_error"],
            meta={"artifact_path": str(artifact_path)},
        )
        return 1

    passed, reasons, meta = evaluate_launch_signoff_artifact(
        payload,
        max_age_days=max_age_days,
        require_ready=require_ready,
    )

    print(f"  overall_ready: {meta.get('overall_ready')}")
    if "age_hours" in meta:
        print(f"  artifact_age_hours: {meta['age_hours']}")

    if not passed:
        print("[launch-signoff-gate] result: fail")
        print("  reasons:")
        for reason in reasons:
            print(f"    - {reason}")
        _write_summary(
            summary_path,
            result="fail",
            reasons=reasons,
            meta=meta,
        )
        return 1

    print("[launch-signoff-gate] result: pass")
    _write_summary(
        summary_path,
        result="pass",
        reasons=[],
        meta=meta,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
