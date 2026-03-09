#!/usr/bin/env python3
"""
Dispatch queued notification outbox items.

Usage:
  cd backend && PYTHONPATH=. python scripts/run_notification_outbox_dispatch.py --limit 100
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from datetime import datetime, timezone
import sys
from pathlib import Path

if __name__ == "__main__":
    _backend = Path(__file__).resolve().parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process notification outbox batch")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum outbox records to process. Defaults to adaptive limit.",
    )
    parser.add_argument(
        "--disable-adaptive",
        action="store_true",
        help="Disable adaptive outbox batch sizing and use fixed claim limit.",
    )
    parser.add_argument(
        "--replay-dead",
        action="store_true",
        help="Move dead-letter rows back to RETRY before dispatch.",
    )
    parser.add_argument(
        "--replay-limit",
        type=int,
        default=100,
        help="Maximum dead-letter rows to replay when --replay-dead is enabled.",
    )
    parser.add_argument(
        "--reset-attempt-count",
        action="store_true",
        help="Reset attempt_count=0 for replayed dead-letter rows.",
    )
    parser.add_argument(
        "--replay-only",
        action="store_true",
        help="Run dead-letter replay only and skip dispatch batch.",
    )
    parser.add_argument(
        "--disable-auto-replay",
        action="store_true",
        help="Disable automatic dead-letter replay guardrail.",
    )
    parser.add_argument(
        "--lock-name",
        default=None,
        help="Singleton lock name to prevent concurrent dispatcher runs.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously with interval sleeps between batches.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=None,
        help="Loop interval seconds (defaults to NOTIFICATION_OUTBOX_DISPATCH_LOOP_INTERVAL_SECONDS).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Optional max loop iterations when --loop is enabled.",
    )
    parser.add_argument(
        "--heartbeat-every",
        type=int,
        default=None,
        help="Emit heartbeat log every N iterations in loop mode.",
    )
    return parser.parse_args()


def main() -> int:
    from app.core.config import settings
    from app.core.settings_domains import get_notification_outbox_settings
    from app.services.notification_outbox import (
        auto_replay_dead_notification_outbox,
        get_notification_outbox_stale_processing_count,
        process_notification_outbox_batch,
        replay_dead_notification_outbox,
    )
    from app.services.worker_lock import WorkerSingletonLock

    args = _parse_args()
    lock_name = (args.lock_name or get_notification_outbox_settings().dispatch_lock_name).strip()
    if not lock_name:
        lock_name = "notification-outbox-dispatch"

    worker_lock = WorkerSingletonLock(lock_name=lock_name)
    if not worker_lock.acquire():
        logger.info(
            "notification outbox dispatcher skipped: lock_not_acquired lock_name=%s",
            lock_name,
        )
        return 0
    logger.info(
        "notification outbox dispatcher lock acquired: lock_name=%s lock_file=%s heartbeat_seconds=%s",
        getattr(worker_lock, "lock_name", lock_name),
        getattr(worker_lock, "lock_file_path", "n/a"),
        getattr(worker_lock, "heartbeat_seconds", "n/a"),
    )

    def _lock_heartbeat_age_seconds() -> int:
        reader = getattr(WorkerSingletonLock, "read_lock_state", None)
        if not callable(reader):
            return -1
        state = reader(lock_name)
        if not isinstance(state, dict):
            return -1
        raw_updated_at = state.get("updated_at")
        if not isinstance(raw_updated_at, str) or not raw_updated_at.strip():
            return -1
        try:
            updated_at = datetime.fromisoformat(raw_updated_at)
        except ValueError:
            return -1
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        age_seconds = (now_utc - updated_at.astimezone(timezone.utc)).total_seconds()
        return max(0, int(age_seconds))

    def _run_one_iteration(*, allow_manual_replay: bool) -> tuple[int, dict[str, int]]:
        replay_summary = {"selected": 0, "replayed": 0, "errors": 0}
        auto_replay_summary = {
            "enabled": 0,
            "triggered": 0,
            "dead_rows": 0,
            "dead_letter_rate": 0.0,
            "replayed": 0,
            "errors": 0,
        }

        auto_replay_summary = auto_replay_dead_notification_outbox(
            enabled=False if args.disable_auto_replay else None,
            replay_limit=args.replay_limit,
            reset_attempt_count=bool(args.reset_attempt_count),
        )
        if int(auto_replay_summary.get("triggered", 0)) > 0:
            logger.info(
                (
                    "notification outbox auto-replay triggered: dead_rows=%s dead_letter_rate=%.4f "
                    "replayed=%s errors=%s"
                ),
                auto_replay_summary.get("dead_rows", 0),
                float(auto_replay_summary.get("dead_letter_rate", 0.0)),
                auto_replay_summary.get("replayed", 0),
                auto_replay_summary.get("errors", 0),
            )
            if int(auto_replay_summary.get("errors", 0)) > 0:
                return 1, {"sent": 0, "retried": 0, "dead": 0, "errors": int(auto_replay_summary.get("errors", 0))}

        if allow_manual_replay and args.replay_dead:
            replay_summary = replay_dead_notification_outbox(
                limit=args.replay_limit,
                reset_attempt_count=bool(args.reset_attempt_count),
            )
            logger.info(
                "notification outbox dead-letter replay summary: selected=%s replayed=%s errors=%s",
                replay_summary.get("selected", 0),
                replay_summary.get("replayed", 0),
                replay_summary.get("errors", 0),
            )
            if int(replay_summary.get("errors", 0)) > 0:
                return 1, {"sent": 0, "retried": 0, "dead": 0, "errors": int(replay_summary.get("errors", 0))}
            if args.replay_only:
                return 0, {"sent": 0, "retried": 0, "dead": 0, "errors": 0}

        summary = asyncio.run(
            process_notification_outbox_batch(
                limit=args.limit,
                adaptive=False if args.disable_adaptive else None,
            )
        )
        stale_processing = get_notification_outbox_stale_processing_count()
        stale_threshold = max(
            0,
            int(
                getattr(
                    settings,
                    "HEALTH_NOTIFICATION_OUTBOX_STALE_PROCESSING_DEGRADED_THRESHOLD",
                    10,
                )
            ),
        )
        logger.info(
            (
                "notification outbox dispatch summary: selected=%s sent=%s retried=%s dead=%s "
                "errors=%s replayed=%s auto_replayed=%s base_limit=%s selected_limit=%s backlog_depth=%s "
                "oldest_pending_age_seconds=%s reclaimed=%s stale_processing=%s lock_heartbeat_age_seconds=%s adaptive=%s"
            ),
            summary.get("selected", 0),
            summary.get("sent", 0),
            summary.get("retried", 0),
            summary.get("dead", 0),
            summary.get("errors", 0),
            replay_summary.get("replayed", 0),
            auto_replay_summary.get("replayed", 0),
            summary.get("base_limit", 0),
            summary.get("selected_limit", 0),
            summary.get("backlog_depth", -1),
            summary.get("oldest_pending_age_seconds", -1),
            summary.get("reclaimed", 0),
            stale_processing,
            _lock_heartbeat_age_seconds(),
            summary.get("adaptive_enabled", 0),
        )
        if stale_processing >= stale_threshold > 0:
            logger.error(
                "notification outbox stale processing exceeds threshold: stale_processing=%s threshold=%s",
                stale_processing,
                stale_threshold,
            )
            return 1, {
                "sent": int(summary.get("sent", 0) or 0),
                "retried": int(summary.get("retried", 0) or 0),
                "dead": int(summary.get("dead", 0) or 0),
                "errors": int(summary.get("errors", 0) or 0) + 1,
            }
        return (0 if int(summary.get("errors", 0)) == 0 else 1), {
            "sent": int(summary.get("sent", 0) or 0),
            "retried": int(summary.get("retried", 0) or 0),
            "dead": int(summary.get("dead", 0) or 0),
            "errors": int(summary.get("errors", 0) or 0),
        }

    try:
        if not args.loop:
            exit_code, _ = _run_one_iteration(allow_manual_replay=True)
            return exit_code

        from app.core.config import settings as app_settings

        interval_seconds = max(
            1,
            int(
                args.interval_seconds
                or getattr(app_settings, "NOTIFICATION_OUTBOX_DISPATCH_LOOP_INTERVAL_SECONDS", 15)
            ),
        )
        heartbeat_every = max(
            1,
            int(
                args.heartbeat_every
                or getattr(app_settings, "NOTIFICATION_OUTBOX_DISPATCH_HEARTBEAT_EVERY", 10)
            ),
        )
        max_iterations = int(args.max_iterations or 0)
        iteration = 0
        aggregate = {"sent": 0, "retried": 0, "dead": 0, "errors": 0}
        logger.info(
            "notification outbox dispatcher loop started: interval_seconds=%s heartbeat_every=%s max_iterations=%s",
            interval_seconds,
            heartbeat_every,
            max_iterations if max_iterations > 0 else "unbounded",
        )
        while True:
            iteration += 1
            exit_code, summary = _run_one_iteration(allow_manual_replay=(iteration == 1))
            for key in aggregate:
                aggregate[key] += int(summary.get(key, 0) or 0)
            if args.replay_only:
                logger.info(
                    "notification outbox dispatcher replay-only completed in loop mode: iteration=%s",
                    iteration,
                )
                return 0
            if exit_code != 0:
                logger.error(
                    "notification outbox dispatcher loop aborted: iteration=%s aggregate=%s",
                    iteration,
                    aggregate,
                )
                return exit_code
            if iteration % heartbeat_every == 0:
                logger.info(
                    "notification outbox dispatcher heartbeat: iteration=%s aggregate=%s lock_heartbeat_age_seconds=%s",
                    iteration,
                    aggregate,
                    _lock_heartbeat_age_seconds(),
                )
            if max_iterations > 0 and iteration >= max_iterations:
                logger.info(
                    "notification outbox dispatcher loop completed: iterations=%s aggregate=%s",
                    iteration,
                    aggregate,
                )
                return 0
            time.sleep(interval_seconds)
    finally:
        worker_lock.release()


if __name__ == "__main__":
    sys.exit(main())
