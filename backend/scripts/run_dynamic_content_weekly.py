#!/usr/bin/env python3
"""
P2-E [AUTO-CONTENT]: Weekly pipeline to generate 5 時事卡片 and inject into the 時事 deck.

Usage: run weekly (e.g. Monday 04:00). Requires DB + OPENAI_API_KEY (optional; fallback to fixed prompts).
  cd backend && PYTHONPATH=. python scripts/run_dynamic_content_weekly.py
"""

import asyncio
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
    parser = argparse.ArgumentParser(description="Run dynamic content weekly injection job")
    parser.add_argument(
        "--lock-name",
        default="dynamic-content-weekly",
        help="Singleton lock name to prevent concurrent weekly runs.",
    )
    return parser.parse_args()


def main() -> int:
    from sqlmodel import Session
    from app.db.session import engine
    from app.services.dynamic_content_pipeline import (
        get_dynamic_content_runtime_state,
        run_weekly_injection,
    )
    from app.services.dynamic_content_runtime_metrics import dynamic_content_runtime_metrics
    from app.services.worker_lock import WorkerSingletonLock

    args = _parse_args()
    worker_lock = WorkerSingletonLock(lock_name=args.lock_name)
    if not worker_lock.acquire():
        logger.info(
            "dynamic content weekly run skipped: lock_not_acquired lock_name=%s",
            args.lock_name,
        )
        return 0

    async def _run() -> int:
        with Session(engine) as session:
            n = await run_weekly_injection(session)
            session.commit()
            return n

    try:
        n = asyncio.run(_run())
        logger.info(
            "Dynamic content weekly run complete: cards_inserted=%s counters=%s state=%s",
            n,
            dynamic_content_runtime_metrics.snapshot(),
            get_dynamic_content_runtime_state(),
        )
        return 0
    finally:
        worker_lock.release()


if __name__ == "__main__":
    sys.exit(main())
