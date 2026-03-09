#!/usr/bin/env python3
"""Run non-production data-restore drill and emit evidence artifacts."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
RUNBOOK_PATH = REPO_ROOT / "docs" / "security" / "data-restore-rehearsal.md"
POLICY_PATH = REPO_ROOT / "docs" / "security" / "data-deletion-lifecycle-policy.json"
LIFECYCLE_CONTRACT_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_data_deletion_lifecycle_contract.py"
VALIDATOR_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "validate_security_evidence.py"

SCHEMA_VERSION = "1.1.0"
ARTIFACT_KIND = "data-restore-drill"
GENERATED_BY = "backend/scripts/run_data_restore_drill_audit.py"
CONTRACT_MODE = "strict"
SOURCE_EVIDENCE_KIND = "data-soft-delete-purge"
DEFAULT_SOURCE_EVIDENCE_MAX_AGE_DAYS = 35

REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "rollback_plan_present",
    "lifecycle_contract_passed",
    "source_purge_evidence_fresh",
    "nonprod_dry_run",
)


@dataclass(frozen=True)
class DrillCheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class SourceEvidenceStatus:
    path: str | None
    generated_at: str | None
    max_age_days: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp(now_utc: datetime) -> str:
    return now_utc.strftime("%Y%m%dT%H%M%SZ")


def _load_module(script_name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _runbook_text() -> str:
    if not RUNBOOK_PATH.exists():
        return ""
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def _source_evidence_check(*, max_age_days: int) -> tuple[bool, str, SourceEvidenceStatus]:
    validator_module = _load_module("validate_security_evidence", VALIDATOR_SCRIPT_PATH)
    try:
        source_path = validator_module._resolve_latest_evidence_path(SOURCE_EVIDENCE_KIND)  # noqa: SLF001
    except FileNotFoundError:
        return (
            False,
            "source purge evidence missing",
            SourceEvidenceStatus(path=None, generated_at=None, max_age_days=max_age_days),
        )

    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            False,
            f"failed to read source purge evidence: {exc}",
            SourceEvidenceStatus(
                path=str(source_path.relative_to(REPO_ROOT)),
                generated_at=None,
                max_age_days=max_age_days,
            ),
        )
    if not isinstance(payload, dict):
        return (
            False,
            "source purge evidence payload must be an object",
            SourceEvidenceStatus(
                path=str(source_path.relative_to(REPO_ROOT)),
                generated_at=None,
                max_age_days=max_age_days,
            ),
        )

    freshness_errors = validator_module.validate_evidence_freshness(
        payload,
        max_age_days=max_age_days,
    )
    generated_at = payload.get("generated_at")
    status = SourceEvidenceStatus(
        path=str(source_path.relative_to(REPO_ROOT)),
        generated_at=generated_at if isinstance(generated_at, str) else None,
        max_age_days=max_age_days,
    )
    if freshness_errors:
        return False, "; ".join(freshness_errors), status
    return True, "source purge evidence freshness check passed", status


def _evaluate_checks(*, max_source_evidence_age_days: int) -> tuple[list[DrillCheckResult], SourceEvidenceStatus]:
    lifecycle_module = _load_module("check_data_deletion_lifecycle_contract", LIFECYCLE_CONTRACT_SCRIPT_PATH)
    lifecycle_violations = lifecycle_module.collect_data_deletion_lifecycle_contract_violations()
    runbook_text = _runbook_text()

    run_mode = os.getenv("DATA_RESTORE_DRILL_ENV", "").strip().lower()
    nonprod_ok = run_mode not in {"prod", "production"}

    source_ok, source_detail, source_status = _source_evidence_check(
        max_age_days=max_source_evidence_age_days
    )

    checks = [
        DrillCheckResult(
            name="runbook_present",
            ok=bool(runbook_text.strip()),
            detail="restore rehearsal runbook exists and is readable"
            if runbook_text.strip()
            else "restore rehearsal runbook missing or empty",
        ),
        DrillCheckResult(
            name="rollback_plan_present",
            ok=("## Rollback Plan" in runbook_text) or ("Rollback Plan" in runbook_text),
            detail="rollback section found in runbook"
            if ("Rollback Plan" in runbook_text)
            else "rollback section missing in restore rehearsal runbook",
        ),
        DrillCheckResult(
            name="lifecycle_contract_passed",
            ok=len(lifecycle_violations) == 0,
            detail="data deletion lifecycle contract satisfied"
            if len(lifecycle_violations) == 0
            else "lifecycle contract violations: " + "; ".join(v.reason for v in lifecycle_violations),
        ),
        DrillCheckResult(
            name="source_purge_evidence_fresh",
            ok=source_ok,
            detail=source_detail,
        ),
        DrillCheckResult(
            name="nonprod_dry_run",
            ok=nonprod_ok,
            detail="dry-run environment accepted"
            if nonprod_ok
            else "DATA_RESTORE_DRILL_ENV must not be production",
        ),
    ]
    return checks, source_status


def run_data_restore_drill(
    *,
    evidence_dir: Path | None = None,
    now_utc: datetime | None = None,
    source_evidence_max_age_days: int | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    now = now_utc or _utc_now()
    target_dir = evidence_dir or EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    source_max_age_days = source_evidence_max_age_days
    if source_max_age_days is None:
        raw_value = os.getenv("DATA_RESTORE_SOURCE_EVIDENCE_MAX_AGE_DAYS", "").strip()
        source_max_age_days = int(raw_value) if raw_value else DEFAULT_SOURCE_EVIDENCE_MAX_AGE_DAYS
    source_max_age_days = max(1, int(source_max_age_days))

    checks, source_status = _evaluate_checks(max_source_evidence_age_days=source_max_age_days)
    checks_passed = sum(1 for item in checks if item.ok)
    checks_total = len(checks)
    checks_failed = checks_total - checks_passed
    all_passed = checks_failed == 0

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "generated_by": GENERATED_BY,
        "contract_mode": CONTRACT_MODE,
        "generated_at": now.isoformat(),
        "dry_run": True,
        "runbook_path": "docs/security/data-restore-rehearsal.md",
        "policy_path": "docs/security/data-deletion-lifecycle-policy.json",
        "source_evidence_kind": SOURCE_EVIDENCE_KIND,
        "source_evidence_path": source_status.path,
        "source_evidence_generated_at": source_status.generated_at,
        "source_evidence_max_age_days": source_status.max_age_days,
        "required_checks": list(REQUIRED_CHECKS),
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "all_passed": all_passed,
        "results": [
            {
                "name": item.name,
                "ok": item.ok,
                "detail": item.detail,
            }
            for item in checks
        ],
    }

    stamp = _utc_stamp(now)
    json_path = target_dir / f"data-restore-drill-{stamp}.json"
    md_path = target_dir / f"data-restore-drill-{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Data Restore Rehearsal Drill",
        "",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated at (UTC): {payload['generated_at']}",
        f"- Dry run: {'YES' if payload['dry_run'] else 'NO'}",
        f"- Source evidence kind: {SOURCE_EVIDENCE_KIND}",
        f"- Source evidence path: {source_status.path or '(none)'}",
        f"- Source evidence max age days: {source_status.max_age_days}",
        f"- Checks passed: {checks_passed}/{checks_total}",
        f"- Overall: {'PASS' if all_passed else 'FAIL'}",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        lines.append(f"| `{item.name}` | {'PASS' if item.ok else 'FAIL'} | {item.detail} |")
    lines.extend(["", f"- Raw JSON: `{json_path}`"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload, json_path, md_path


def main() -> int:
    payload, json_path, md_path = run_data_restore_drill()
    print("[data-restore-drill]")
    print(f"  evidence_json: {json_path}")
    print(f"  evidence_md: {md_path}")
    print(f"  source_evidence_path: {payload['source_evidence_path']}")
    print(f"  checks_total: {payload['checks_total']}")
    print(f"  checks_passed: {payload['checks_passed']}")
    print(f"  checks_failed: {payload['checks_failed']}")
    if not payload["all_passed"]:
        print("result: fail")
        return 1
    print("result: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
