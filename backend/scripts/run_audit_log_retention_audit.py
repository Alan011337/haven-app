#!/usr/bin/env python3
"""Run audit-log retention audit and write evidence artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import SQLModel, Session, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import models  # noqa: F401,E402
from app.core.config import settings  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.services.audit_log_retention import purge_expired_audit_events  # noqa: E402


AUDIT_RETENTION_SCHEMA_VERSION = "1.1.0"
AUDIT_RETENTION_ARTIFACT_KIND = "audit-log-retention"
AUDIT_RETENTION_GENERATED_BY = "backend/scripts/run_audit_log_retention_audit.py"
AUDIT_RETENTION_CONTRACT_MODE = "strict"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_evidence(
    *,
    retention_days: int,
    before_count: int,
    deleted_count: int,
    after_count: int,
    healthy: bool,
    generated_at: str,
) -> tuple[Path, Path]:
    evidence_dir = REPO_ROOT / "docs" / "security" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_timestamp()
    json_path = evidence_dir / f"audit-log-retention-{stamp}.json"
    md_path = evidence_dir / f"audit-log-retention-{stamp}.md"

    payload = {
        "schema_version": AUDIT_RETENTION_SCHEMA_VERSION,
        "artifact_kind": AUDIT_RETENTION_ARTIFACT_KIND,
        "generated_by": AUDIT_RETENTION_GENERATED_BY,
        "contract_mode": AUDIT_RETENTION_CONTRACT_MODE,
        "generated_at": generated_at,
        "retention_days": retention_days,
        "before_count": before_count,
        "deleted_count": deleted_count,
        "after_count": after_count,
        "healthy": healthy,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Audit Log Retention Audit",
        "",
        f"- Schema version: {AUDIT_RETENTION_SCHEMA_VERSION}",
        f"- Generated at (UTC): {generated_at}",
        f"- Retention days: {retention_days}",
        f"- Before count: {before_count}",
        f"- Deleted count: {deleted_count}",
        f"- After count: {after_count}",
        f"- Healthy: {'YES' if healthy else 'NO'}",
        "",
        f"- Raw JSON: `{json_path}`",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    SQLModel.metadata.create_all(engine)
    retention_days = max(1, int(settings.AUDIT_LOG_RETENTION_DAYS))
    generated_at = datetime.now(timezone.utc).isoformat()

    with Session(engine) as session:
        before_count = len(session.exec(select(AuditEvent)).all())
        deleted_count = purge_expired_audit_events(
            session=session,
            retention_days=retention_days,
        )
        session.commit()
        after_count = len(session.exec(select(AuditEvent)).all())

    healthy = (
        before_count >= 0
        and deleted_count >= 0
        and after_count >= 0
        and deleted_count <= before_count
        and after_count == (before_count - deleted_count)
    )
    json_path, md_path = _write_evidence(
        retention_days=retention_days,
        before_count=before_count,
        deleted_count=deleted_count,
        after_count=after_count,
        healthy=healthy,
        generated_at=generated_at,
    )

    print("[audit-log-retention-audit]")
    print(f"  retention_days: {retention_days}")
    print(f"  before_count: {before_count}")
    print(f"  deleted_count: {deleted_count}")
    print(f"  after_count: {after_count}")
    print(f"  evidence_json: {json_path}")
    print(f"  evidence_md: {md_path}")
    if not healthy:
        print("result: fail")
        return 1
    print("result: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

