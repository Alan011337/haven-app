from __future__ import annotations

import logging
import uuid
import time
from datetime import timedelta
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, delete, func, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.core.log_redaction import redact_email
from app.core.settings_domains import get_notification_outbox_settings
from app.db.session import engine
from app.models.notification_outbox import NotificationOutbox, NotificationOutboxStatus
from app.services.notification_runtime_metrics import notification_runtime_metrics
from app.services.notification_outbox_support import (
    build_auto_replay_summary,
    build_backpressure_metric_flags,
    build_cleanup_summary,
    build_process_summary,
    build_replay_summary,
    compute_dead_letter_rate_from_counts,
    compute_retry_age_p95_seconds,
    evaluate_backpressure_summary,
    is_outbox_backpressure_exempt,
    normalize_status_counts,
    resolve_adaptive_claim_limit,
)
from app.services.notification_outbox_config import (
    EMAIL_FALLBACK_DEFERRED_PREFIX as _EMAIL_FALLBACK_DEFERRED_PREFIX,
    adaptive_age_critical_seconds as _adaptive_age_critical_seconds,
    adaptive_age_scale_threshold_seconds as _adaptive_age_scale_threshold_seconds,
    adaptive_batching_enabled as _adaptive_batching_enabled,
    adaptive_max_claim_limit as _adaptive_max_claim_limit,
    auto_replay_enabled as _auto_replay_enabled,
    auto_replay_limit as _auto_replay_limit,
    auto_replay_min_dead_letter_rate as _auto_replay_min_dead_letter_rate,
    auto_replay_min_dead_rows as _auto_replay_min_dead_rows,
    backpressure_depth_threshold as _backpressure_depth_threshold,
    backpressure_oldest_age_seconds as _backpressure_oldest_age_seconds,
    compute_backoff_seconds as _compute_backoff_seconds,
    dead_retention_days as _dead_retention_days,
    decode_email_fallback_deferred_reason as _decode_email_fallback_deferred_reason,
    default_claim_limit as _default_claim_limit,
    default_max_attempts as _default_max_attempts,
    dispatch_lock_name as _dispatch_lock_name,
    encode_email_fallback_deferred_reason as _encode_email_fallback_deferred_reason,
    processing_timeout_seconds as _processing_timeout_seconds,
    sent_retention_days as _sent_retention_days,
)
from app.services.notification_outbox_state import resolve_dispatch_transition
from app.services.worker_lock import WorkerSingletonLock

logger = logging.getLogger(__name__)


def _elapsed_seconds_since_created(item: NotificationOutbox) -> int:
    try:
        elapsed_seconds = (utcnow() - item.created_at).total_seconds()
        return max(0, int(elapsed_seconds))
    except Exception:
        return 0


def _classify_outbox_error(exc: Exception) -> str:
    if isinstance(exc, SQLAlchemyError):
        return "db_error"
    return "unexpected_error"


def _classify_dispatch_error(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError,)):
        return "dispatch_timeout"
    return "unexpected_error"


def _claim_ready_outbox_ids(
    *,
    session: Session,
    now_utc,
    limit: int,
) -> list[uuid.UUID]:
    claim_started_at = time.monotonic()
    dialect = getattr(getattr(session.get_bind(), "dialect", None), "name", "").lower()
    id_query = (
        select(NotificationOutbox.id)
        .where(
            col(NotificationOutbox.status).in_(
                [NotificationOutboxStatus.PENDING, NotificationOutboxStatus.RETRY]
            ),
            NotificationOutbox.available_at <= now_utc,
        )
        .order_by(col(NotificationOutbox.created_at).asc())
        .limit(limit)
    )
    if dialect == "postgresql":
        # Use SKIP LOCKED in Postgres to avoid dispatcher contention under parallel workers.
        id_query = id_query.with_for_update(skip_locked=True)

    candidate_ids = list(session.exec(id_query).all())
    if not candidate_ids:
        session.commit()
        return []
    notification_runtime_metrics.increment("notification_outbox_claim_round_total")
    notification_runtime_metrics.increment(
        "notification_outbox_claim_candidate_total",
        amount=len(candidate_ids),
    )

    session.exec(
        update(NotificationOutbox)
        .where(
            col(NotificationOutbox.id).in_(candidate_ids),
            col(NotificationOutbox.status).in_(
                [NotificationOutboxStatus.PENDING, NotificationOutboxStatus.RETRY]
            ),
            NotificationOutbox.available_at <= now_utc,
        )
        .values(
            status=NotificationOutboxStatus.PROCESSING,
            updated_at=now_utc,
        )
    )
    claimed_ids = list(
        session.exec(
            select(NotificationOutbox.id).where(
                col(NotificationOutbox.id).in_(candidate_ids),
                NotificationOutbox.status == NotificationOutboxStatus.PROCESSING,
                NotificationOutbox.updated_at == now_utc,
            )
        ).all()
    )
    claimed_count = len(claimed_ids)
    notification_runtime_metrics.increment(
        "notification_outbox_claimed_total",
        amount=claimed_count,
    )
    claim_gap = max(0, len(candidate_ids) - claimed_count)
    if claim_gap > 0:
        notification_runtime_metrics.increment(
            "notification_outbox_claim_gap_total",
            amount=claim_gap,
        )
    claim_latency_ms = max(0, int((time.monotonic() - claim_started_at) * 1000))
    notification_runtime_metrics.increment("notification_outbox_claim_latency_samples_total")
    notification_runtime_metrics.increment(
        "notification_outbox_claim_latency_ms_total",
        amount=max(1, claim_latency_ms),
    )
    session.commit()
    return claimed_ids


def _reclaim_stale_processing_rows(*, session: Session, now_utc) -> int:
    cutoff = now_utc - timedelta(seconds=_processing_timeout_seconds())
    result = session.exec(
        update(NotificationOutbox)
        .where(
            NotificationOutbox.status == NotificationOutboxStatus.PROCESSING,
            NotificationOutbox.updated_at < cutoff,
        )
        .values(
            status=NotificationOutboxStatus.RETRY,
            available_at=now_utc,
            updated_at=now_utc,
            last_error_reason="processing_timeout_reclaimed",
        )
    )
    reclaimed = int(getattr(result, "rowcount", 0) or 0)
    if reclaimed > 0:
        notification_runtime_metrics.increment("notification_outbox_reclaimed_total", amount=reclaimed)
        logger.warning(
            "Notification outbox reclaimed stale processing rows: count=%s timeout_seconds=%s",
            reclaimed,
            _processing_timeout_seconds(),
        )
    session.commit()
    return reclaimed


def reclaim_stale_processing_rows(*, session: Session, now_utc=None) -> int:
    return _reclaim_stale_processing_rows(session=session, now_utc=now_utc or utcnow())


def get_notification_outbox_stale_processing_count() -> int:
    try:
        with Session(engine) as session:
            now_utc = utcnow()
            cutoff = now_utc - timedelta(seconds=_processing_timeout_seconds())
            value = session.exec(
                select(func.count(NotificationOutbox.id)).where(
                    NotificationOutbox.status == NotificationOutboxStatus.PROCESSING,
                    NotificationOutbox.updated_at < cutoff,
                )
            ).one()
            return int(value or 0)
    except SQLAlchemyError as exc:
        logger.warning(
            "Notification outbox stale-processing probe failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return -1


def get_notification_outbox_dispatch_lock_heartbeat_age_seconds() -> int:
    state = WorkerSingletonLock.read_lock_state(_dispatch_lock_name())
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
    age_seconds = (datetime.now(timezone.utc) - updated_at.astimezone(timezone.utc)).total_seconds()
    return max(0, int(age_seconds))


def get_notification_outbox_depth() -> int:
    try:
        with Session(engine) as session:
            now = utcnow()
            value = session.exec(
                select(func.count(NotificationOutbox.id)).where(
                    col(NotificationOutbox.status).in_(
                        [
                            NotificationOutboxStatus.PENDING,
                            NotificationOutboxStatus.RETRY,
                            NotificationOutboxStatus.PROCESSING,
                        ]
                    ),
                    NotificationOutbox.available_at <= now,
                )
            ).one()
            return int(value or 0)
    except SQLAlchemyError as exc:
        logger.warning(
            "Notification outbox depth probe failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return -1


def get_notification_outbox_oldest_pending_age_seconds() -> int:
    try:
        with Session(engine) as session:
            oldest_created_at = session.exec(
                select(func.min(NotificationOutbox.created_at)).where(
                    col(NotificationOutbox.status).in_(
                        [
                            NotificationOutboxStatus.PENDING,
                            NotificationOutboxStatus.RETRY,
                            NotificationOutboxStatus.PROCESSING,
                        ]
                    )
                )
            ).one()
            if oldest_created_at is None:
                return 0
            age_seconds = int((utcnow() - oldest_created_at).total_seconds())
            return max(0, age_seconds)
    except SQLAlchemyError as exc:
        logger.warning(
            "Notification outbox oldest-age probe failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return -1


def get_notification_outbox_status_counts() -> dict[str, int]:
    try:
        with Session(engine) as session:
            rows = session.exec(
                select(NotificationOutbox.status, func.count(NotificationOutbox.id))
                .group_by(NotificationOutbox.status)
            ).all()
            return normalize_status_counts(list(rows))
    except SQLAlchemyError as exc:
        logger.warning(
            "Notification outbox status-count probe failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return {}


def get_notification_outbox_retry_age_p95_seconds() -> int:
    try:
        with Session(engine) as session:
            retry_rows = session.exec(
                select(NotificationOutbox.created_at).where(
                    NotificationOutbox.status == NotificationOutboxStatus.RETRY
                )
            ).all()
            return compute_retry_age_p95_seconds(
                created_at_rows=list(retry_rows),
                now_utc=utcnow(),
            )
    except SQLAlchemyError as exc:
        logger.warning(
            "Notification outbox retry-age probe failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return -1


def get_notification_outbox_dead_letter_rate() -> float:
    return compute_dead_letter_rate_from_counts(get_notification_outbox_status_counts())


def _is_outbox_backpressure_exempt(*, event_type: str | None, action_type: str | None) -> bool:
    cfg = get_notification_outbox_settings()
    return is_outbox_backpressure_exempt(
        event_type=event_type,
        action_type=action_type,
        exempt_event_types=tuple(cfg.backlog_throttle_exempt_event_types),
        exempt_action_types=tuple(cfg.backlog_throttle_exempt_action_types),
    )


def evaluate_notification_outbox_backpressure(
    *,
    event_type: str | None,
    action_type: str | None,
) -> dict[str, int | str | bool]:
    cfg = get_notification_outbox_settings()
    depth = get_notification_outbox_depth()
    oldest = get_notification_outbox_oldest_pending_age_seconds()
    summary = evaluate_backpressure_summary(
        enabled=bool(cfg.backlog_throttle_enabled),
        event_type=event_type,
        action_type=action_type,
        exempt_event_types=tuple(cfg.backlog_throttle_exempt_event_types),
        exempt_action_types=tuple(cfg.backlog_throttle_exempt_action_types),
        depth=depth,
        oldest_pending_age_seconds=oldest,
        depth_threshold=int(cfg.backlog_throttle_depth_threshold),
        oldest_pending_age_seconds_threshold=int(
            cfg.backlog_throttle_oldest_pending_seconds_threshold
        ),
    )
    if not cfg.backlog_throttle_enabled:
        return summary

    metric_flags = build_backpressure_metric_flags(summary)
    if metric_flags["is_exempt"]:
        notification_runtime_metrics.increment("notification_outbox_backpressure_exempt_total")
        return summary
    if metric_flags["probe_unavailable"]:
        notification_runtime_metrics.increment("notification_outbox_backpressure_probe_unavailable_total")
        return summary
    if metric_flags["depth_triggered"]:
        notification_runtime_metrics.increment("notification_outbox_backpressure_triggered_total")
        notification_runtime_metrics.increment(
            "notification_outbox_backpressure_triggered_depth_total"
        )
        return summary
    if metric_flags["oldest_triggered"]:
        notification_runtime_metrics.increment("notification_outbox_backpressure_triggered_total")
        notification_runtime_metrics.increment(
            "notification_outbox_backpressure_triggered_oldest_pending_total"
        )
        return summary

    return summary


def resolve_notification_outbox_claim_limit(
    *,
    base_limit: int,
    backlog_depth: int,
    oldest_pending_age_seconds: int = 0,
    adaptive_enabled: bool,
    adaptive_max_limit: int,
    age_scale_threshold_seconds: int = 300,
    age_critical_seconds: int = 1200,
) -> int:
    return resolve_adaptive_claim_limit(
        base_limit=base_limit,
        backlog_depth=backlog_depth,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        adaptive_enabled=adaptive_enabled,
        adaptive_max_limit=adaptive_max_limit,
        age_scale_threshold_seconds=age_scale_threshold_seconds,
        age_critical_seconds=age_critical_seconds,
    )


def enqueue_notification_outbox(
    *,
    receiver_email: str,
    sender_name: str,
    action_type: str,
    event_type: str | None,
    dedupe_key: str | None,
    dedupe_slot_reserved: bool,
    receiver_user_id: uuid.UUID | None,
    sender_user_id: uuid.UUID | None,
    source_session_id: uuid.UUID | None,
    max_attempts: int | None = None,
) -> uuid.UUID | None:
    now = utcnow()
    attempts_limit = max(1, int(max_attempts or _default_max_attempts()))
    item = NotificationOutbox(
        status=NotificationOutboxStatus.PENDING,
        receiver_email=receiver_email,
        sender_name=sender_name,
        action_type=action_type,
        event_type=event_type,
        dedupe_key=dedupe_key,
        dedupe_slot_reserved=bool(dedupe_slot_reserved),
        receiver_user_id=receiver_user_id,
        sender_user_id=sender_user_id,
        source_session_id=source_session_id,
        max_attempts=attempts_limit,
        available_at=now,
        created_at=now,
        updated_at=now,
    )
    try:
        with Session(engine) as session:
            session.add(item)
            session.commit()
            session.refresh(item)
    except SQLAlchemyError as exc:
        logger.error(
            "Notification outbox enqueue failed: receiver=%s action=%s reason=%s error_type=%s",
            redact_email(receiver_email),
            action_type,
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return None

    notification_runtime_metrics.increment("notification_outbox_enqueued_total")
    return item.id


async def _dispatch_once(item: NotificationOutbox) -> tuple[bool, str | None]:
    if item.event_type:
        from app.services.notification_multichannel import dispatch_multichannel
        from app.services.notification import (
            is_email_notification_enabled,
            send_partner_notification_with_retry,
            _is_receiver_email_opted_out,
        )

        results = await dispatch_multichannel(
            event_type=item.event_type,
            receiver_email=item.receiver_email,
            receiver_user_id=item.receiver_user_id,
            sender_name=item.sender_name,
            action_type=item.action_type,  # type: ignore[arg-type]
        )
        if any(bool(v) for v in results.values()):
            return True, None
        if (
            item.receiver_user_id is not None
            and is_email_notification_enabled()
            and not _is_receiver_email_opted_out(item.receiver_user_id)
        ):
            fallback_delay = max(
                0,
                int(getattr(settings, "NOTIFICATION_EMAIL_FALLBACK_DELAY_SECONDS", 300)),
            )
            if fallback_delay > 0:
                elapsed_seconds = _elapsed_seconds_since_created(item)
                if elapsed_seconds < fallback_delay:
                    remaining_seconds = fallback_delay - elapsed_seconds
                    return False, _encode_email_fallback_deferred_reason(remaining_seconds)
            ok = await send_partner_notification_with_retry(
                receiver_email=item.receiver_email,
                sender_name=item.sender_name,
                action_type=item.action_type,  # type: ignore[arg-type]
            )
            if ok:
                return True, None
        return False, "multichannel_retry_exhausted"

    from app.services.notification import send_partner_notification

    ok = await send_partner_notification(
        receiver_email=item.receiver_email,
        sender_name=item.sender_name,
        action_type=item.action_type,  # type: ignore[arg-type]
    )
    if ok:
        return True, None
    return False, "email_transport_error"


def _release_dedupe_slot_if_needed(item: NotificationOutbox) -> None:
    if not item.dedupe_slot_reserved:
        return
    if not item.dedupe_key:
        return
    try:
        from app.services.notification import _release_notification_slot

        _release_notification_slot(item.dedupe_key)
    except Exception as exc:
        logger.warning(
            "Notification outbox dedupe slot release failed: reason=%s",
            type(exc).__name__,
        )


async def process_notification_outbox_batch(
    *,
    limit: int | None = None,
    adaptive: bool | None = None,
) -> dict[str, int]:
    base_limit = max(1, int(limit or _default_claim_limit()))
    adaptive_enabled = bool(_adaptive_batching_enabled() if adaptive is None else adaptive)
    backlog_depth = -1
    oldest_pending_age_seconds = -1
    selected_limit = base_limit
    if adaptive_enabled:
        backlog_depth = get_notification_outbox_depth()
        oldest_pending_age_seconds = get_notification_outbox_oldest_pending_age_seconds()
        depth_threshold = _backpressure_depth_threshold()
        oldest_age_threshold = _backpressure_oldest_age_seconds()
        if (
            backlog_depth >= depth_threshold
            or oldest_pending_age_seconds >= oldest_age_threshold
        ):
            notification_runtime_metrics.increment("notification_outbox_backpressure_active_total")
        selected_limit = resolve_notification_outbox_claim_limit(
            base_limit=base_limit,
            backlog_depth=backlog_depth,
            oldest_pending_age_seconds=max(0, oldest_pending_age_seconds),
            adaptive_enabled=True,
            adaptive_max_limit=_adaptive_max_claim_limit(),
            age_scale_threshold_seconds=_adaptive_age_scale_threshold_seconds(),
            age_critical_seconds=_adaptive_age_critical_seconds(),
        )
        if selected_limit > base_limit:
            notification_runtime_metrics.increment("notification_outbox_adaptive_scale_up_total")
            if backlog_depth >= depth_threshold:
                notification_runtime_metrics.increment("notification_outbox_adaptive_depth_scale_up_total")
            if oldest_pending_age_seconds >= _adaptive_age_scale_threshold_seconds():
                notification_runtime_metrics.increment("notification_outbox_adaptive_age_scale_up_total")

    now = utcnow()
    summary = build_process_summary(
        base_limit=base_limit,
        selected_limit=selected_limit,
        backlog_depth=backlog_depth,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        adaptive_enabled=adaptive_enabled,
    )

    with Session(engine) as session:
        try:
            summary["reclaimed"] = _reclaim_stale_processing_rows(
                session=session,
                now_utc=now,
            )
            selected_ids = _claim_ready_outbox_ids(
                session=session,
                now_utc=now,
                limit=selected_limit,
            )
            summary["selected"] = len(selected_ids)
            if selected_limit > 0 and summary["selected"] >= selected_limit:
                notification_runtime_metrics.increment("notification_outbox_claim_saturation_total")
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error(
                "Notification outbox claim failed: reason=%s error_type=%s",
                _classify_outbox_error(exc),
                type(exc).__name__,
            )
            summary["errors"] += 1
            return summary

    for outbox_id in selected_ids:
        with Session(engine) as session:
            row = session.get(NotificationOutbox, outbox_id)
            if row is None:
                continue

            row.attempt_count = max(0, int(row.attempt_count)) + 1
            row.last_attempt_at = utcnow()
            row.updated_at = row.last_attempt_at

            delivered = False
            failure_reason: str | None = None
            try:
                delivered, failure_reason = await _dispatch_once(row)
            except Exception as exc:
                delivered = False
                failure_reason = _classify_dispatch_error(exc)
                logger.error(
                    "Notification outbox dispatch crashed: id=%s reason=%s error_type=%s",
                    row.id,
                    failure_reason,
                    type(exc).__name__,
                )

            backoff_seconds = _compute_backoff_seconds(attempt_count=row.attempt_count)
            deferred_seconds = _decode_email_fallback_deferred_reason(failure_reason)
            if deferred_seconds is not None:
                backoff_seconds = max(backoff_seconds, deferred_seconds)
                failure_reason = _EMAIL_FALLBACK_DEFERRED_PREFIX

            transition = resolve_dispatch_transition(
                row=row,
                delivered=delivered,
                failure_reason=failure_reason,
                now_utc=utcnow(),
                backoff_seconds=backoff_seconds,
            )
            row.status = transition.status
            row.last_error_reason = transition.last_error_reason
            if transition.available_at is not None:
                row.available_at = transition.available_at
            summary[transition.summary_bucket] += 1
            notification_runtime_metrics.increment(transition.metric_key)
            if transition.release_dedupe_slot:
                _release_dedupe_slot_if_needed(row)

            try:
                session.add(row)
                session.commit()
            except SQLAlchemyError as exc:
                session.rollback()
                summary["errors"] += 1
                logger.error(
                    "Notification outbox persistence failed: id=%s reason=%s error_type=%s",
                    outbox_id,
                    _classify_outbox_error(exc),
                    type(exc).__name__,
                )

    return summary


def cleanup_notification_outbox(
    *,
    sent_retention_days: int | None = None,
    dead_retention_days: int | None = None,
) -> dict[str, int]:
    sent_days = max(1, int(sent_retention_days or _sent_retention_days()))
    dead_days = max(1, int(dead_retention_days or _dead_retention_days()))
    now = utcnow()
    sent_cutoff = now - timedelta(days=sent_days)
    dead_cutoff = now - timedelta(days=dead_days)

    summary = build_cleanup_summary()

    try:
        with Session(engine) as session:
            sent_delete_result = session.exec(
                delete(NotificationOutbox).where(
                    NotificationOutbox.status == NotificationOutboxStatus.SENT,
                    NotificationOutbox.updated_at < sent_cutoff,
                )
            )
            summary["purged_sent"] = int(getattr(sent_delete_result, "rowcount", 0) or 0)

            dead_delete_result = session.exec(
                delete(NotificationOutbox).where(
                    NotificationOutbox.status == NotificationOutboxStatus.DEAD,
                    NotificationOutbox.updated_at < dead_cutoff,
                )
            )
            summary["purged_dead"] = int(getattr(dead_delete_result, "rowcount", 0) or 0)

            session.commit()
    except SQLAlchemyError as exc:
        summary["errors"] = 1
        logger.error(
            "Notification outbox cleanup failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return summary

    if summary["purged_sent"] > 0:
        notification_runtime_metrics.increment(
            "notification_outbox_purged_sent_total",
            amount=summary["purged_sent"],
        )
    if summary["purged_dead"] > 0:
        notification_runtime_metrics.increment(
            "notification_outbox_purged_dead_total",
            amount=summary["purged_dead"],
        )

    return summary


def replay_dead_notification_outbox(
    *,
    limit: int | None = None,
    reset_attempt_count: bool = False,
) -> dict[str, int]:
    selected_limit = max(1, int(limit or _default_claim_limit()))
    now = utcnow()
    summary = build_replay_summary()

    try:
        with Session(engine) as session:
            rows = list(
                session.exec(
                    select(NotificationOutbox)
                    .where(NotificationOutbox.status == NotificationOutboxStatus.DEAD)
                    .order_by(col(NotificationOutbox.updated_at).desc())
                    .limit(selected_limit)
                ).all()
            )
            summary["selected"] = len(rows)
            for row in rows:
                row.status = NotificationOutboxStatus.RETRY
                row.available_at = now
                row.updated_at = now
                row.last_error_reason = "manual_replay_requested"
                # Dead-letter rows already released dedupe slots; keep disabled to avoid double release.
                row.dedupe_slot_reserved = False
                if reset_attempt_count:
                    row.attempt_count = 0
                session.add(row)

            session.commit()
            summary["replayed"] = len(rows)
    except SQLAlchemyError as exc:
        summary["errors"] = 1
        logger.error(
            "Notification outbox dead-letter replay failed: reason=%s error_type=%s",
            _classify_outbox_error(exc),
            type(exc).__name__,
        )
        return summary

    if summary["replayed"] > 0:
        notification_runtime_metrics.increment(
            "notification_outbox_replayed_total",
            amount=summary["replayed"],
        )
    return summary


def auto_replay_dead_notification_outbox(
    *,
    enabled: bool | None = None,
    replay_limit: int | None = None,
    min_dead_rows: int | None = None,
    min_dead_letter_rate: float | None = None,
    reset_attempt_count: bool = False,
) -> dict[str, int | float]:
    effective_enabled = _auto_replay_enabled() if enabled is None else bool(enabled)
    effective_limit = max(1, int(replay_limit or _auto_replay_limit()))
    effective_min_dead_rows = max(1, int(min_dead_rows or _auto_replay_min_dead_rows()))
    effective_min_dead_letter_rate = max(
        0.0,
        min(1.0, float(min_dead_letter_rate if min_dead_letter_rate is not None else _auto_replay_min_dead_letter_rate())),
    )

    summary = build_auto_replay_summary(enabled=effective_enabled)
    if not effective_enabled:
        return summary

    counts = get_notification_outbox_status_counts()
    dead_rows = int(counts.get(NotificationOutboxStatus.DEAD.value, 0))
    dead_letter_rate = float(get_notification_outbox_dead_letter_rate())
    summary["dead_rows"] = dead_rows
    summary["dead_letter_rate"] = dead_letter_rate

    if dead_rows < effective_min_dead_rows:
        return summary
    if dead_letter_rate < effective_min_dead_letter_rate:
        return summary

    replay_summary = replay_dead_notification_outbox(
        limit=effective_limit,
        reset_attempt_count=reset_attempt_count,
    )
    summary["triggered"] = 1
    summary["replayed"] = int(replay_summary.get("replayed", 0))
    summary["errors"] = int(replay_summary.get("errors", 0))
    notification_runtime_metrics.increment("notification_outbox_auto_replay_triggered_total")
    if summary["errors"] > 0:
        notification_runtime_metrics.increment("notification_outbox_auto_replay_error_total")
    return summary
