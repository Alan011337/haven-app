#!/usr/bin/env python3
"""Run billing reconciliation audit and write evidence artifacts."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlmodel import Session, SQLModel, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import engine  # noqa: E402
from app.models.billing import (  # noqa: E402
    BillingCommandLog,
    BillingEntitlementState,
    BillingLedgerEntry,
)

BILLING_RECON_SCHEMA_VERSION = "1.1.0"
BILLING_RECON_ARTIFACT_KIND = "billing-reconciliation"
BILLING_RECON_GENERATED_BY = "backend/scripts/run_billing_reconciliation_audit.py"
BILLING_RECON_CONTRACT_MODE = "strict"


@dataclass
class UserAuditResult:
    user_id: str
    command_count: int
    command_ledger_count: int
    missing_command_ledger_count: int
    missing_command_ids: list[str]
    entitlement_state: str | None
    entitlement_plan: str | None
    healthy: bool


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _iter_user_ids(session: Session) -> Iterable[str]:
    command_user_ids = {
        str(row)
        for row in session.exec(select(BillingCommandLog.user_id).distinct()).all()
        if row is not None
    }
    entitlement_user_ids = {
        str(row)
        for row in session.exec(select(BillingEntitlementState.user_id).distinct()).all()
        if row is not None
    }
    return sorted(command_user_ids.union(entitlement_user_ids))


def _audit_user(session: Session, user_id: str) -> UserAuditResult:
    command_rows = session.exec(
        select(BillingCommandLog).where(BillingCommandLog.user_id == user_id)
    ).all()
    expected_keys = {f"cmd:{row.id}" for row in command_rows}

    command_ledger_keys = set(
        session.exec(
            select(BillingLedgerEntry.source_key).where(
                BillingLedgerEntry.user_id == user_id,
                BillingLedgerEntry.source_type == "COMMAND",
            )
        ).all()
    )
    missing_command_ids = [
        str(row.id) for row in command_rows if f"cmd:{row.id}" not in command_ledger_keys
    ]

    entitlement = session.exec(
        select(BillingEntitlementState).where(BillingEntitlementState.user_id == user_id)
    ).first()

    healthy = len(missing_command_ids) == 0 and (
        len(command_rows) == 0 or entitlement is not None
    )
    return UserAuditResult(
        user_id=user_id,
        command_count=len(command_rows),
        command_ledger_count=len(expected_keys.intersection(command_ledger_keys)),
        missing_command_ledger_count=len(missing_command_ids),
        missing_command_ids=missing_command_ids,
        entitlement_state=entitlement.lifecycle_state if entitlement else None,
        entitlement_plan=entitlement.current_plan if entitlement else None,
        healthy=healthy,
    )


def _write_evidence(results: list[UserAuditResult]) -> tuple[Path, Path]:
    evidence_dir = REPO_ROOT / "docs" / "security" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_timestamp()
    json_path = evidence_dir / f"billing-reconciliation-{stamp}.json"
    md_path = evidence_dir / f"billing-reconciliation-{stamp}.md"

    generated_at = datetime.now(timezone.utc).isoformat()
    total_users = len(results)
    unhealthy_users = [item for item in results if not item.healthy]
    payload = {
        "schema_version": BILLING_RECON_SCHEMA_VERSION,
        "artifact_kind": BILLING_RECON_ARTIFACT_KIND,
        "generated_by": BILLING_RECON_GENERATED_BY,
        "contract_mode": BILLING_RECON_CONTRACT_MODE,
        "generated_at": generated_at,
        "total_users": total_users,
        "healthy_users": total_users - len(unhealthy_users),
        "unhealthy_users": len(unhealthy_users),
        "results": [asdict(item) for item in results],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Billing Reconciliation Audit",
        "",
        f"- Schema version: {payload['schema_version']}",
        f"- Generated at (UTC): {generated_at}",
        f"- Total users: {payload['total_users']}",
        f"- Healthy users: {payload['healthy_users']}",
        f"- Unhealthy users: {payload['unhealthy_users']}",
        "",
        "| User | Healthy | Commands | Command Ledgers | Missing Command Ledgers | Entitlement |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        entitlement_label = item.entitlement_state or "none"
        if item.entitlement_plan:
            entitlement_label = f"{entitlement_label}:{item.entitlement_plan}"
        lines.append(
            f"| `{item.user_id}` | {'YES' if item.healthy else 'NO'} | {item.command_count} | "
            f"{item.command_ledger_count} | {item.missing_command_ledger_count} | {entitlement_label} |"
        )

    if unhealthy_users:
        lines.extend(["", "## Unhealthy Details", ""])
        for item in unhealthy_users:
            lines.append(
                f"- `{item.user_id}` missing_command_ids={item.missing_command_ids}, "
                f"entitlement_state={item.entitlement_state}"
            )

    lines.append("")
    lines.append(f"- Raw JSON: `{json_path}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user_ids = list(_iter_user_ids(session))
        results = [_audit_user(session, user_id) for user_id in user_ids]
    json_path, md_path = _write_evidence(results)

    unhealthy_count = len([item for item in results if not item.healthy])
    print("[billing-reconciliation-audit]")
    print(f"  total_users: {len(results)}")
    print(f"  unhealthy_users: {unhealthy_count}")
    print(f"  evidence_json: {json_path}")
    print(f"  evidence_md: {md_path}")
    if unhealthy_count > 0:
        print("result: fail")
        return 1
    print("result: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
