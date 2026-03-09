# P2-B QUEUE-01: Async journal analysis and notification pipeline.
# Enqueue: journal_analysis (after journal create), journal_notify (after analysis done).
# Workers run in app lifespan when REDIS_URL and ASYNC_JOURNAL_ANALYSIS are set.

from app.queue.journal_tasks import (
    enqueue_journal_analysis,
    enqueue_journal_notification,
    is_async_journal_analysis_enabled,
    run_analysis_job,
    run_notification_job,
    start_journal_queue_workers,
    stop_journal_queue_workers,  # async; await from lifespan
)

__all__ = [
    "is_async_journal_analysis_enabled",
    "enqueue_journal_analysis",
    "enqueue_journal_notification",
    "run_analysis_job",
    "run_notification_job",
    "start_journal_queue_workers",
    "stop_journal_queue_workers",
]
