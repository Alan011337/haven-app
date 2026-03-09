#!/usr/bin/env python3
"""Run soft-delete purge audit and write evidence artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import SQLModel, Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import models  # noqa: F401,E402
from app.core.config import settings  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.services.data_soft_delete_purge import (  # noqa: E402
    SOFT_DELETE_PURGE_COUNT_KEYS,
    SoftDeletePurgeResult,
    purge_soft_deleted_rows,
)

DATA_SOFT_DELETE_PURGE_SCHEMA_VERSION = "1.1.0"
DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND = "data-soft-delete-purge"
DATA_SOFT_DELETE_PURGE_GENERATED_BY = "backend/scripts/run_data_soft_delete_purge_audit.py"
DATA_SOFT_DELETE_PURGE_CONTRACT_MODE = "strict"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run soft-delete purge audit.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=settings.DATA_SOFT_DELETE_PURGE_RETENTION_DAYS,
        help=(
            "Soft-delete purge retention window in days "
            "(default: DATA_SOFT_DELETE_PURGE_RETENTION_DAYS)."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply physical purge. Default is dry-run audit mode.",
    )
    parser.add_argument(
        "--allow-when-disabled",
        action="store_true",
        help=(
            "Allow --apply execution even when DATA_SOFT_DELETE_ENABLED=false. "
            "Useful for one-time cleanup."
        ),
    )
    return parser.parse_args()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_healthy(*, result: SoftDeletePurgeResult) -> bool:
    candidate_total = sum(result.candidate_counts.get(key, -1) for key in SOFT_DELETE_PURGE_COUNT_KEYS)
    purged_total = sum(result.purged_counts.get(key, -1) for key in SOFT_DELETE_PURGE_COUNT_KEYS)
    if candidate_total < 0 or purged_total < 0:
        return False
    for key in SOFT_DELETE_PURGE_COUNT_KEYS:
        candidate_count = result.candidate_counts.get(key)
        purged_count = result.purged_counts.get(key)
        if not isinstance(candidate_count, int) or candidate_count < 0:
            return False
        if not isinstance(purged_count, int) or purged_count < 0:
            return False
        if purged_count > candidate_count:
            return False
    if result.dry_run:
        if purged_total != 0:
            return False
    return True


def _write_evidence(
    *,
    retention_days: int,
    mode: str,
    result: SoftDeletePurgeResult,
    generated_at: str,
    healthy: bool,
) -> tuple[Path, Path]:
    evidence_dir = REPO_ROOT / "docs" / "security" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_timestamp()
    json_path = evidence_dir / f"data-soft-delete-purge-{stamp}.json"
    md_path = evidence_dir / f"data-soft-delete-purge-{stamp}.md"

    total_candidates = sum(result.candidate_counts.get(key, 0) for key in SOFT_DELETE_PURGE_COUNT_KEYS)
    total_purged = sum(result.purged_counts.get(key, 0) for key in SOFT_DELETE_PURGE_COUNT_KEYS)

    payload = {
        "schema_version": DATA_SOFT_DELETE_PURGE_SCHEMA_VERSION,
        "artifact_kind": DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND,
        "generated_by": DATA_SOFT_DELETE_PURGE_GENERATED_BY,
        "contract_mode": DATA_SOFT_DELETE_PURGE_CONTRACT_MODE,
        "generated_at": generated_at,
        "mode": mode,
        "soft_delete_enabled": settings.DATA_SOFT_DELETE_ENABLED,
        "retention_days": retention_days,
        "cutoff_iso": result.cutoff.isoformat(),
        "candidate_counts": result.candidate_counts,
        "purged_counts": result.purged_counts,
        "total_candidates": total_candidates,
        "total_purged": total_purged,
        "healthy": healthy,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Data Soft-Delete Purge Audit",
        "",
        f"- Schema version: {DATA_SOFT_DELETE_PURGE_SCHEMA_VERSION}",
        f"- Generated at (UTC): {generated_at}",
        f"- Mode: {mode}",
        f"- Soft-delete enabled: {'YES' if settings.DATA_SOFT_DELETE_ENABLED else 'NO'}",
        f"- Retention days: {retention_days}",
        f"- Cutoff (UTC): {result.cutoff.isoformat()}",
        f"- Total candidates: {total_candidates}",
        f"- Total purged: {total_purged}",
        f"- Healthy: {'YES' if healthy else 'NO'}",
        "",
        "| Data Class | Candidates | Purged |",
        "| --- | --- | --- |",
    ]
    for key in SOFT_DELETE_PURGE_COUNT_KEYS:
        lines.append(
            f"| `{key}` | {result.candidate_counts.get(key, 0)} | {result.purged_counts.get(key, 0)} |"
        )
    lines.extend(["", f"- Raw JSON: `{json_path}`"])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    args = parse_args()
    retention_days = max(1, int(args.retention_days))
    apply_mode = bool(args.apply)
    mode = "apply" if apply_mode else "dry_run"
    generated_at = datetime.now(timezone.utc).isoformat()

    if apply_mode and not settings.DATA_SOFT_DELETE_ENABLED and not args.allow_when_disabled:
        print("[data-soft-delete-purge-audit]")
        print("  result: fail")
        print(
            "  reason: refusing --apply while DATA_SOFT_DELETE_ENABLED=false "
            "(use --allow-when-disabled for intentional cleanup)"
        )
        return 1

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        result = purge_soft_deleted_rows(
            session=session,
            purge_retention_days=retention_days,
            dry_run=not apply_mode,
        )
        if apply_mode:
            session.commit()
        else:
            session.rollback()

    healthy = _is_healthy(result=result)
    json_path, md_path = _write_evidence(
        retention_days=retention_days,
        mode=mode,
        result=result,
        generated_at=generated_at,
        healthy=healthy,
    )

    print("[data-soft-delete-purge-audit]")
    print(f"  mode: {mode}")
    print(f"  soft_delete_enabled: {settings.DATA_SOFT_DELETE_ENABLED}")
    print(f"  retention_days: {retention_days}")
    print(f"  cutoff_iso: {result.cutoff.isoformat()}")
    print(f"  evidence_json: {json_path}")
    print(f"  evidence_md: {md_path}")
    if not healthy:
        print("result: fail")
        return 1
    print("result: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
