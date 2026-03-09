#!/usr/bin/env python3
"""
Process Stripe webhook receipts that are queued or failed and ready for retry.

Usage:
  cd backend && PYTHONPATH=. python scripts/run_billing_webhook_retry_dispatch.py --limit 100
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
    parser = argparse.ArgumentParser(description="Process billing webhook retry batch")
    parser.add_argument("--limit", type=int, default=50, help="Maximum receipts to process")
    return parser.parse_args()


def main() -> int:
    from app.api.routers.billing import process_pending_stripe_webhook_receipts

    args = _parse_args()
    summary = process_pending_stripe_webhook_receipts(limit=args.limit)
    logger.info(
        "billing webhook retry summary: selected=%s processed=%s errors=%s",
        summary.get("selected", 0),
        summary.get("processed", 0),
        summary.get("errors", 0),
    )
    return 0 if int(summary.get("errors", 0)) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
