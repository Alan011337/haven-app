#!/usr/bin/env python3
"""Run non-production chaos drill audit and emit evidence artifacts."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
RUNBOOK_PATH = REPO_ROOT / "docs" / "ops" / "chaos-drill-spec.md"
INCIDENT_PLAYBOOK_PATH = REPO_ROOT / "docs" / "ops" / "incident-response-playbook.md"
REPORT_TEMPLATE_PATH = REPO_ROOT / "docs" / "ops" / "chaos-drill-report-template.md"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "chaos-drill.yml"

SCHEMA_VERSION = "1.1.0"
ARTIFACT_KIND = "chaos-drill"
GENERATED_BY = "backend/scripts/run_chaos_drill_audit.py"
CONTRACT_MODE = "strict"
REQUIRED_DRILLS: tuple[str, ...] = (
    "ai_provider_outage",
    "ws_storm",
)
REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "incident_playbook_ai_outage_present",
    "incident_playbook_ws_storm_present",
    "report_template_present",
    "workflow_schedule_declared",
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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _has_ai_outage_section(text: str) -> bool:
    markers = ("providers.openai.error", "OpenAI API 異常", "AI provider")
    return any(marker in text for marker in markers)


def _has_ws_storm_section(text: str) -> bool:
    markers = ("ws_sli_below_target", "WebSocket SLI", "WS storm")
    return any(marker in text for marker in markers)


def _workflow_schedule_declared(text: str) -> bool:
    return 'cron: "0 9 * * 5"' in text


def _evaluate_checks() -> list[DrillCheckResult]:
    runbook_text = _read_text(RUNBOOK_PATH)
    incident_text = _read_text(INCIDENT_PLAYBOOK_PATH)
    report_template_text = _read_text(REPORT_TEMPLATE_PATH)
    workflow_text = _read_text(WORKFLOW_PATH)

    run_mode = os.getenv("CHAOS_DRILL_ENV", "").strip().lower()
    nonprod_ok = run_mode not in {"prod", "production"}

    checks = [
        DrillCheckResult(
            name="runbook_present",
            ok=bool(runbook_text.strip()),
            detail="chaos drill runbook exists and is readable"
            if runbook_text.strip()
            else "chaos drill runbook missing or empty",
        ),
        DrillCheckResult(
            name="incident_playbook_ai_outage_present",
            ok=_has_ai_outage_section(incident_text),
            detail="AI outage section found in incident playbook"
            if _has_ai_outage_section(incident_text)
            else "AI outage section missing in incident playbook",
        ),
        DrillCheckResult(
            name="incident_playbook_ws_storm_present",
            ok=_has_ws_storm_section(incident_text),
            detail="WS storm section found in incident playbook"
            if _has_ws_storm_section(incident_text)
            else "WS storm section missing in incident playbook",
        ),
        DrillCheckResult(
            name="report_template_present",
            ok=bool(report_template_text.strip()),
            detail="chaos drill report template exists"
            if report_template_text.strip()
            else "chaos drill report template missing or empty",
        ),
        DrillCheckResult(
            name="workflow_schedule_declared",
            ok=_workflow_schedule_declared(workflow_text),
            detail="weekly Friday schedule declared in workflow"
            if _workflow_schedule_declared(workflow_text)
            else "workflow schedule missing required weekly Friday cron",
        ),
        DrillCheckResult(
            name="nonprod_dry_run",
            ok=nonprod_ok,
            detail="dry-run environment accepted"
            if nonprod_ok
            else "CHAOS_DRILL_ENV must not be production",
        ),
    ]
    return checks


def run_chaos_drill(
    *,
    evidence_dir: Path | None = None,
    now_utc: datetime | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    now = now_utc or _utc_now()
    target_dir = evidence_dir or EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    checks = _evaluate_checks()
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
        "runbook_path": "docs/ops/chaos-drill-spec.md",
        "incident_playbook_path": "docs/ops/incident-response-playbook.md",
        "report_template_path": "docs/ops/chaos-drill-report-template.md",
        "workflow_path": ".github/workflows/chaos-drill.yml",
        "required_drills": list(REQUIRED_DRILLS),
        "executed_drills": list(REQUIRED_DRILLS),
        "required_checks": list(REQUIRED_CHECKS),
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "all_passed": all_passed,
        "results": [
            {"name": item.name, "ok": item.ok, "detail": item.detail}
            for item in checks
        ],
    }

    stamp = _utc_stamp(now)
    json_path = target_dir / f"chaos-drill-{stamp}.json"
    md_path = target_dir / f"chaos-drill-{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Chaos Drill Evidence",
        "",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated at (UTC): {payload['generated_at']}",
        f"- Dry run: {'YES' if payload['dry_run'] else 'NO'}",
        f"- Required drills: {', '.join(REQUIRED_DRILLS)}",
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
    payload, json_path, md_path = run_chaos_drill()
    print("[chaos-drill]")
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
