#!/usr/bin/env python3
"""
Purge old notification outbox rows.

Usage:
  cd backend && PYTHONPATH=. python scripts/run_notification_outbox_cleanup.py
  cd backend && PYTHONPATH=. python scripts/run_notification_outbox_cleanup.py --sent-retention-days 7 --dead-retention-days 14
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup notification outbox old rows")
    parser.add_argument(
        "--sent-retention-days",
        type=int,
        default=None,
        help="Retention days for SENT rows (default from settings)",
    )
    parser.add_argument(
        "--dead-retention-days",
        type=int,
        default=None,
        help="Retention days for DEAD rows (default from settings)",
    )
    return parser.parse_args()


def main() -> int:
    from app.services.notification_outbox import cleanup_notification_outbox

    args = _parse_args()
    summary = cleanup_notification_outbox(
        sent_retention_days=args.sent_retention_days,
        dead_retention_days=args.dead_retention_days,
    )
    logger.info(
        "notification outbox cleanup summary: purged_sent=%s purged_dead=%s errors=%s",
        summary.get("purged_sent", 0),
        summary.get("purged_dead", 0),
        summary.get("errors", 0),
    )
    return 0 if int(summary.get("errors", 0)) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
