#!/usr/bin/env python3
"""Run billing console drift audit and emit evidence artifacts."""

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
POLICY_PATH = REPO_ROOT / "docs" / "security" / "billing-console-drift-policy.json"
RUNBOOK_PATH = REPO_ROOT / "docs" / "billing" / "console-drift-monitor.md"
STORE_CONTRACT_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_store_compliance_contract.py"

SCHEMA_VERSION = "1.1.0"
ARTIFACT_KIND = "billing-console-drift"
GENERATED_BY = "backend/scripts/run_billing_console_drift_audit.py"
CONTRACT_MODE = "strict"

POLICY_SCHEMA_VERSION = "1.0.0"
POLICY_ARTIFACT_KIND = "billing-console-drift-policy"

REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "policy_contract_passed",
    "store_compliance_contract_passed",
    "webhook_secret_configured",
    "webhook_tolerance_within_policy",
    "async_mode_within_policy",
    "nonprod_dry_run",
)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


@dataclass(frozen=True)
class DriftCheckResult:
    name: str
    ok: bool
    detail: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp(now_utc: datetime) -> str:
    return now_utc.strftime("%Y%m%dT%H%M%SZ")


def _load_store_contract_module():
    spec = importlib.util.spec_from_file_location(
        "check_store_compliance_contract",
        STORE_CONTRACT_SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {STORE_CONTRACT_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_policy_payload() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _validate_policy_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if payload.get("schema_version") != POLICY_SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if payload.get("artifact_kind") != POLICY_ARTIFACT_KIND:
        errors.append("artifact_kind mismatch")

    expected = payload.get("expected")
    if not isinstance(expected, dict):
        errors.append("expected must be object")
        return errors

    require_secret = expected.get("require_webhook_secret")
    if not isinstance(require_secret, bool):
        errors.append("expected.require_webhook_secret must be boolean")

    max_tolerance = expected.get("max_webhook_tolerance_seconds")
    if not isinstance(max_tolerance, int) or max_tolerance <= 0:
        errors.append("expected.max_webhook_tolerance_seconds must be positive integer")

    allowed_async_modes = expected.get("allowed_async_modes")
    if not isinstance(allowed_async_modes, list) or not allowed_async_modes:
        errors.append("expected.allowed_async_modes must be non-empty list")
    elif not all(isinstance(item, bool) for item in allowed_async_modes):
        errors.append("expected.allowed_async_modes entries must be boolean")

    references = payload.get("references")
    if not isinstance(references, dict):
        errors.append("references must be object")
    else:
        required_reference_keys = (
            "store_compliance_matrix",
            "store_compliance_doc",
            "billing_engine_doc",
            "drift_runbook",
        )
        for key in required_reference_keys:
            rel_path = references.get(key)
            if not isinstance(rel_path, str) or not rel_path.strip():
                errors.append(f"references.{key} must be non-empty string path")
                continue
            if not (REPO_ROOT / rel_path).exists():
                errors.append(f"references.{key} path not found: {rel_path}")

    return errors


def _evaluate_checks() -> tuple[list[DriftCheckResult], dict[str, Any]]:
    policy_payload = _load_policy_payload()
    policy_errors = _validate_policy_contract(policy_payload)
    store_contract_module = _load_store_contract_module()
    store_contract_errors = store_contract_module.collect_store_compliance_contract_violations()

    expected = policy_payload.get("expected", {})
    max_tolerance = int(expected.get("max_webhook_tolerance_seconds", 300))
    allowed_async_modes = expected.get("allowed_async_modes", [True, False])

    webhook_secret = (settings.BILLING_STRIPE_WEBHOOK_SECRET or "").strip()
    tolerance_seconds = int(settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS)
    async_mode = bool(settings.BILLING_STRIPE_WEBHOOK_ASYNC_MODE)
    run_mode = os.getenv("BILLING_CONSOLE_DRIFT_ENV", "").strip().lower()
    nonprod_ok = run_mode not in {"prod", "production"}

    checks = [
        DriftCheckResult(
            name="runbook_present",
            ok=RUNBOOK_PATH.exists() and bool(RUNBOOK_PATH.read_text(encoding="utf-8").strip()),
            detail="runbook exists and is non-empty"
            if RUNBOOK_PATH.exists() and bool(RUNBOOK_PATH.read_text(encoding="utf-8").strip())
            else "runbook missing or empty",
        ),
        DriftCheckResult(
            name="policy_contract_passed",
            ok=len(policy_errors) == 0,
            detail="policy contract satisfied"
            if len(policy_errors) == 0
            else "; ".join(policy_errors),
        ),
        DriftCheckResult(
            name="store_compliance_contract_passed",
            ok=len(store_contract_errors) == 0,
            detail="store compliance contract satisfied"
            if len(store_contract_errors) == 0
            else "; ".join(item.reason for item in store_contract_errors),
        ),
        DriftCheckResult(
            name="webhook_secret_configured",
            ok=bool(webhook_secret),
            detail="billing webhook secret is configured"
            if webhook_secret
            else "billing webhook secret is missing",
        ),
        DriftCheckResult(
            name="webhook_tolerance_within_policy",
            ok=tolerance_seconds <= max_tolerance,
            detail=f"runtime tolerance={tolerance_seconds}s within max={max_tolerance}s"
            if tolerance_seconds <= max_tolerance
            else f"runtime tolerance={tolerance_seconds}s exceeds max={max_tolerance}s",
        ),
        DriftCheckResult(
            name="async_mode_within_policy",
            ok=async_mode in allowed_async_modes,
            detail=f"runtime async_mode={async_mode} allowed"
            if async_mode in allowed_async_modes
            else f"runtime async_mode={async_mode} not in allowed_async_modes={allowed_async_modes}",
        ),
        DriftCheckResult(
            name="nonprod_dry_run",
            ok=nonprod_ok,
            detail="dry-run environment accepted"
            if nonprod_ok
            else "BILLING_CONSOLE_DRIFT_ENV must not be production",
        ),
    ]
    runtime_snapshot = {
        "provider": str(policy_payload.get("provider", "stripe")).strip().lower() or "stripe",
        "runtime_tolerance_seconds": tolerance_seconds,
        "runtime_async_mode": async_mode,
    }
    return checks, runtime_snapshot


def run_billing_console_drift_audit(
    *,
    evidence_dir: Path | None = None,
    now_utc: datetime | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    now = now_utc or _utc_now()
    target_dir = evidence_dir or EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    checks, runtime_snapshot = _evaluate_checks()
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
        "provider": runtime_snapshot["provider"],
        "runbook_path": "docs/billing/console-drift-monitor.md",
        "policy_path": "docs/security/billing-console-drift-policy.json",
        "required_checks": list(REQUIRED_CHECKS),
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "all_passed": all_passed,
        "runtime": {
            "webhook_tolerance_seconds": runtime_snapshot["runtime_tolerance_seconds"],
            "webhook_async_mode": runtime_snapshot["runtime_async_mode"],
        },
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
    json_path = target_dir / f"billing-console-drift-{stamp}.json"
    md_path = target_dir / f"billing-console-drift-{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Billing Console Drift Audit",
        "",
        f"- Generated at (UTC): {payload['generated_at']}",
        f"- Provider: {payload['provider']}",
        f"- Dry run: {'YES' if payload['dry_run'] else 'NO'}",
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
    payload, json_path, md_path = run_billing_console_drift_audit()
    print("[billing-console-drift-audit]")
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
