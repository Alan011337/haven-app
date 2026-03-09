#!/usr/bin/env python3
"""Run non-production key-rotation dry-run drill and emit evidence artifacts."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
RUNBOOK_PATH = REPO_ROOT / "docs" / "security" / "keys.md"
POLICY_PATH = REPO_ROOT / "docs" / "security" / "secrets-key-management-policy.json"
CHECK_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_secrets_key_management_contract.py"

SCHEMA_VERSION = "1.1.0"
ARTIFACT_KIND = "key-rotation-drill"
GENERATED_BY = "backend/scripts/run_key_rotation_drill_audit.py"
CONTRACT_MODE = "strict"

REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "policy_contract_passed",
    "env_separation_enforced",
    "rollback_plan_present",
    "nonprod_dry_run",
)


@dataclass(frozen=True)
class DrillCheckResult:
    name: str
    ok: bool
    detail: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp(now_utc: datetime) -> str:
    return now_utc.strftime("%Y%m%dT%H%M%SZ")


def _load_policy_checker_module():
    spec = importlib.util.spec_from_file_location("check_secrets_key_management_contract", CHECK_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {CHECK_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _runbook_text() -> str:
    if not RUNBOOK_PATH.exists():
        return ""
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def _evaluate_checks() -> list[DrillCheckResult]:
    checker_module = _load_policy_checker_module()
    violations = checker_module.collect_secrets_key_management_contract_violations()
    runbook_text = _runbook_text()
    policy_payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    env_sep = policy_payload.get("environment_separation", {})
    prohibited_files = env_sep.get("prohibited_repo_files", [])
    prohibited_exists = [
        rel_path
        for rel_path in prohibited_files
        if isinstance(rel_path, str) and rel_path.strip() and (REPO_ROOT / rel_path).exists()
    ]
    env_sep_ok = (
        isinstance(env_sep, dict)
        and env_sep.get("prod_secret_manager_required") is True
        and not prohibited_exists
    )

    run_mode = os.getenv("KEY_ROTATION_DRILL_ENV", "").strip().lower()
    nonprod_ok = run_mode not in {"prod", "production"}

    checks = [
        DrillCheckResult(
            name="runbook_present",
            ok=bool(runbook_text.strip()),
            detail="runbook file exists and is readable" if runbook_text.strip() else "runbook missing or empty",
        ),
        DrillCheckResult(
            name="policy_contract_passed",
            ok=len(violations) == 0,
            detail="policy contract satisfied"
            if len(violations) == 0
            else "policy violations: " + "; ".join(v.reason for v in violations),
        ),
        DrillCheckResult(
            name="env_separation_enforced",
            ok=env_sep_ok,
            detail="prod secret manager required and prohibited secret files absent"
            if env_sep_ok
            else "environment separation policy failed",
        ),
        DrillCheckResult(
            name="rollback_plan_present",
            ok=("## Rollback Plan" in runbook_text) or ("Rollback Plan" in runbook_text),
            detail="rollback section found in runbook"
            if ("Rollback Plan" in runbook_text)
            else "rollback section missing in runbook",
        ),
        DrillCheckResult(
            name="nonprod_dry_run",
            ok=nonprod_ok,
            detail="dry-run environment accepted"
            if nonprod_ok
            else "KEY_ROTATION_DRILL_ENV must not be production",
        ),
    ]
    return checks


def run_key_rotation_drill(*, evidence_dir: Path | None = None, now_utc: datetime | None = None) -> tuple[dict, Path, Path]:
    now = now_utc or _utc_now()
    target_dir = evidence_dir or EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    checks = _evaluate_checks()
    checks_passed = sum(1 for item in checks if item.ok)
    checks_total = len(checks)
    checks_failed = checks_total - checks_passed
    all_passed = checks_failed == 0

    kms_provider = os.getenv("KEY_ROTATION_KMS_PROVIDER", "mock-kms").strip() or "mock-kms"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "generated_by": GENERATED_BY,
        "contract_mode": CONTRACT_MODE,
        "generated_at": now.isoformat(),
        "dry_run": True,
        "kms_provider": kms_provider,
        "runbook_path": "docs/security/keys.md",
        "policy_path": "docs/security/secrets-key-management-policy.json",
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
    json_path = target_dir / f"key-rotation-drill-{stamp}.json"
    md_path = target_dir / f"key-rotation-drill-{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Key Rotation Dry-Run Drill",
        "",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated at (UTC): {payload['generated_at']}",
        f"- Dry run: {'YES' if payload['dry_run'] else 'NO'}",
        f"- KMS provider: {kms_provider}",
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
    payload, json_path, md_path = run_key_rotation_drill()
    print("[key-rotation-drill]")
    print(f"  evidence_json: {json_path}")
    print(f"  evidence_md: {md_path}")
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
