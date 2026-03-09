#!/usr/bin/env python3
"""
ARCH-01: Tiered storage — export data older than ARCHIVE_COLD_AFTER_DAYS to S3 (cold tier).

Usage:
  Set COLD_TIER_S3_BUCKET (required), optionally ARCHIVE_COLD_AFTER_DAYS (default 90),
  ARCHIVE_DRY_RUN=1 to only report what would be archived.
  Requires AWS credentials (env or IAM) with s3:PutObject on the bucket.

See docs/backend/tiered-storage-strategy.md for full strategy.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path when run from repo root
if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ARCHIVE_COLD_AFTER_DAYS = int(os.environ.get("ARCHIVE_COLD_AFTER_DAYS", "90"))
COLD_TIER_S3_BUCKET = (os.environ.get("COLD_TIER_S3_BUCKET") or "").strip()
ARCHIVE_DRY_RUN = os.environ.get("ARCHIVE_DRY_RUN", "").lower() in ("1", "true", "yes")


def _cutoff_ts():
    return (datetime.now(timezone.utc) - timedelta(days=ARCHIVE_COLD_AFTER_DAYS)).replace(tzinfo=timezone.utc)


def run_archive_journals() -> int:
    """Export journals with created_at before cutoff to JSONL; upload to S3. Returns count exported."""
    if not COLD_TIER_S3_BUCKET and not ARCHIVE_DRY_RUN:
        logger.error("COLD_TIER_S3_BUCKET is not set")
        return 0

    from sqlmodel import Session, select
    from app.db.session import engine
    from app.models.journal import Journal

    cutoff = _cutoff_ts()
    with Session(engine) as session:
        stmt = select(Journal).where(Journal.created_at < cutoff).order_by(Journal.created_at.asc())
        rows = list(session.exec(stmt).all())
    if not rows:
        logger.info("No journals to archive (cutoff=%s)", cutoff.isoformat())
        return 0

    logger.info("Would archive %d journals (cutoff=%s)", len(rows), cutoff.isoformat())
    if ARCHIVE_DRY_RUN:
        return len(rows)

    try:
        import boto3
    except ImportError:
        logger.error("boto3 not installed; pip install boto3")
        return 0

    prefix = f"cold-tier/journals/{cutoff.strftime('%Y-%m')}"
    key = f"{prefix}/journals_{cutoff.strftime('%Y-%m-%d')}.jsonl"
    buf = "\n".join(json.dumps(r.model_dump(mode="json"), default=str) for r in rows) + "\n"

    client = boto3.client("s3")
    client.put_object(Bucket=COLD_TIER_S3_BUCKET, Key=key, Body=buf.encode("utf-8"), ContentType="application/jsonl")
    logger.info("Uploaded %s to s3://%s/%s (%d records)", key, COLD_TIER_S3_BUCKET, key, len(rows))
    return len(rows)


def main() -> int:
    if ARCHIVE_DRY_RUN:
        logger.info("DRY RUN: no uploads will be performed")
    n = run_archive_journals()
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
