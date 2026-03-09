from __future__ import annotations

import uuid
from datetime import timedelta
from time import perf_counter
from typing import Any, Callable, Optional

from fastapi import HTTPException, status
from sqlalchemy import update as sqlalchemy_update
from sqlmodel import col, func, select

from app import models
from app.api.deps import CurrentUser, SessionDep
from app.api.error_handling import commit_with_error_handling
from app.api.routers.users.notification_filters import (
    build_notification_filter_clauses,
    normalize_action_type_or_raise,
    normalize_delivery_status_or_raise,
)
from app.core.datetime_utils import utcnow
from app.models.audit_event import AuditEventOutcome
from app.models.notification_event import (
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from app.schemas.notification import (
    NotificationDailyStatsPublic,
    NotificationErrorReasonStatsPublic,
    NotificationEventPublic,
    NotificationMarkReadResult,
    NotificationRetryResult,
    NotificationStatsPublic,
)
from app.services.audit_log import record_audit_event_best_effort


def handle_read_my_notifications(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int,
    offset: int,
    unread_only: bool,
    action_type: Optional[str],
    delivery_status: Optional[str],
    error_reason: Optional[str],
    log_notification_metrics: Callable[..., None],
) -> list[NotificationEventPublic]:
    query_started_at = perf_counter()
    normalized_action_type = normalize_action_type_or_raise(action_type)
    normalized_delivery_status = normalize_delivery_status_or_raise(delivery_status)
    normalized_error_reason = (error_reason or "").strip() or None
    clauses = build_notification_filter_clauses(
        receiver_user_id=current_user.id,
        unread_only=unread_only,
        action_type=normalized_action_type,
        delivery_status=normalized_delivery_status,
        error_reason=normalized_error_reason,
    )
    statement = (
        select(NotificationEvent)
        .where(*clauses)
        .order_by(col(NotificationEvent.created_at).desc())
        .offset(offset)
        .limit(max(1, min(limit, 100)))
    )

    rows = session.exec(statement).all()
    payload = [NotificationEventPublic.model_validate(row.model_dump()) for row in rows]
    log_notification_metrics(
        endpoint="notifications_list",
        current_user=current_user,
        unread_only=unread_only,
        action_type=normalized_action_type,
        delivery_status=normalized_delivery_status,
        error_reason=normalized_error_reason,
        limit=limit,
        offset=offset,
        result_count=len(payload),
        duration_ms=int((perf_counter() - query_started_at) * 1000),
    )
    return payload


def handle_read_my_notification_stats(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    window_days: int,
    unread_only: bool,
    action_type: Optional[str],
    delivery_status: Optional[str],
    error_reason: Optional[str],
    log_notification_metrics: Callable[..., None],
) -> NotificationStatsPublic:
    query_started_at = perf_counter()
    normalized_action_type = normalize_action_type_or_raise(action_type)
    normalized_delivery_status = normalize_delivery_status_or_raise(delivery_status)
    normalized_error_reason = (error_reason or "").strip() or None
    clauses = build_notification_filter_clauses(
        receiver_user_id=current_user.id,
        unread_only=unread_only,
        action_type=normalized_action_type,
        delivery_status=normalized_delivery_status,
        error_reason=normalized_error_reason,
    )

    status_rows = session.exec(
        select(NotificationEvent.status, func.count(NotificationEvent.id))
        .where(*clauses)
        .group_by(NotificationEvent.status)
    ).all()
    status_counts: dict[str, int] = {}
    for status_value, count in status_rows:
        key = status_value.value if isinstance(status_value, NotificationDeliveryStatus) else str(status_value)
        status_counts[key] = int(count or 0)

    action_rows = session.exec(
        select(NotificationEvent.action_type, func.count(NotificationEvent.id))
        .where(*clauses)
        .group_by(NotificationEvent.action_type)
    ).all()
    action_counts: dict[str, int] = {}
    for action_value, count in action_rows:
        key = action_value.value if isinstance(action_value, NotificationActionType) else str(action_value)
        action_counts[key] = int(count or 0)

    unread_count = int(
        session.exec(
            select(func.count(NotificationEvent.id)).where(
                *clauses,
                NotificationEvent.is_read.is_(False),
            )
        ).one()
        or 0
    )

    now = utcnow()
    recent_24h_start = now - timedelta(hours=24)
    recent_24h_count = int(
        session.exec(
            select(func.count(NotificationEvent.id)).where(
                *clauses,
                NotificationEvent.created_at >= recent_24h_start,
            )
        ).one()
        or 0
    )
    recent_24h_failed_count = int(
        session.exec(
            select(func.count(NotificationEvent.id)).where(
                *clauses,
                NotificationEvent.created_at >= recent_24h_start,
                NotificationEvent.status == NotificationDeliveryStatus.FAILED,
            )
        ).one()
        or 0
    )

    total_count = int(sum(status_counts.values()))
    last_event_at = session.exec(select(func.max(NotificationEvent.created_at)).where(*clauses)).one()

    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=window_days - 1
    )
    window_rows = session.exec(
        select(NotificationEvent.created_at, NotificationEvent.status).where(
            *clauses,
            NotificationEvent.created_at >= window_start,
        )
    ).all()

    date_keys = [(now.date() - timedelta(days=offset)) for offset in range(window_days - 1, -1, -1)]
    daily_map: dict[str, dict[str, int]] = {
        key.isoformat(): {
            "total_count": 0,
            "sent_count": 0,
            "failed_count": 0,
            "throttled_count": 0,
            "queued_count": 0,
        }
        for key in date_keys
    }

    for created_at, status_value in window_rows:
        day_key = created_at.date().isoformat()
        bucket = daily_map.get(day_key)
        if not bucket:
            continue
        bucket["total_count"] += 1
        status_key = status_value.value if isinstance(status_value, NotificationDeliveryStatus) else str(status_value)
        if status_key == NotificationDeliveryStatus.SENT.value:
            bucket["sent_count"] += 1
        elif status_key == NotificationDeliveryStatus.FAILED.value:
            bucket["failed_count"] += 1
        elif status_key == NotificationDeliveryStatus.THROTTLED.value:
            bucket["throttled_count"] += 1
        elif status_key == NotificationDeliveryStatus.QUEUED.value:
            bucket["queued_count"] += 1

    window_daily = [
        NotificationDailyStatsPublic(
            date=key,
            total_count=daily_map[key.isoformat()]["total_count"],
            sent_count=daily_map[key.isoformat()]["sent_count"],
            failed_count=daily_map[key.isoformat()]["failed_count"],
            throttled_count=daily_map[key.isoformat()]["throttled_count"],
            queued_count=daily_map[key.isoformat()]["queued_count"],
        )
        for key in date_keys
    ]
    window_total_count = int(sum(item.total_count for item in window_daily))
    window_sent_count = int(sum(item.sent_count for item in window_daily))
    window_failed_count = int(sum(item.failed_count for item in window_daily))
    window_throttled_count = int(sum(item.throttled_count for item in window_daily))
    window_queued_count = int(sum(item.queued_count for item in window_daily))

    failure_reason_rows = session.exec(
        select(NotificationEvent.error_message, func.count(NotificationEvent.id))
        .where(
            *clauses,
            NotificationEvent.created_at >= window_start,
            NotificationEvent.status == NotificationDeliveryStatus.FAILED,
        )
        .group_by(NotificationEvent.error_message)
        .order_by(func.count(NotificationEvent.id).desc())
        .limit(5)
    ).all()
    window_top_failure_reasons = [
        NotificationErrorReasonStatsPublic(
            reason=(error_message or "unknown"),
            count=int(count or 0),
        )
        for error_message, count in failure_reason_rows
    ]

    payload = NotificationStatsPublic(
        total_count=total_count,
        unread_count=unread_count,
        queued_count=status_counts.get(NotificationDeliveryStatus.QUEUED.value, 0),
        sent_count=status_counts.get(NotificationDeliveryStatus.SENT.value, 0),
        failed_count=status_counts.get(NotificationDeliveryStatus.FAILED.value, 0),
        throttled_count=status_counts.get(NotificationDeliveryStatus.THROTTLED.value, 0),
        journal_count=action_counts.get(NotificationActionType.JOURNAL.value, 0),
        card_count=action_counts.get(NotificationActionType.CARD.value, 0),
        recent_24h_count=recent_24h_count,
        recent_24h_failed_count=recent_24h_failed_count,
        window_days=window_days,
        window_total_count=window_total_count,
        window_sent_count=window_sent_count,
        window_failed_count=window_failed_count,
        window_throttled_count=window_throttled_count,
        window_queued_count=window_queued_count,
        window_daily=window_daily,
        window_top_failure_reasons=window_top_failure_reasons,
        last_event_at=last_event_at,
    )
    log_notification_metrics(
        endpoint="notifications_stats",
        current_user=current_user,
        unread_only=unread_only,
        action_type=normalized_action_type,
        delivery_status=normalized_delivery_status,
        error_reason=normalized_error_reason,
        window_days=window_days,
        result_count=payload.total_count,
        duration_ms=int((perf_counter() - query_started_at) * 1000),
    )
    return payload


def handle_mark_notifications_read(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    action_type: Optional[str],
    logger: Any,
    log_notification_metrics: Callable[..., None],
) -> NotificationMarkReadResult:
    query_started_at = perf_counter()
    normalized_action_type = normalize_action_type_or_raise(action_type)

    clauses: list[Any] = [
        NotificationEvent.receiver_user_id == current_user.id,
        NotificationEvent.is_read.is_(False),
        NotificationEvent.deleted_at.is_(None),
    ]
    if normalized_action_type:
        clauses.append(NotificationEvent.action_type == normalized_action_type)

    pending_count = int(
        session.exec(select(func.count(NotificationEvent.id)).where(*clauses)).one() or 0
    )

    if pending_count == 0:
        log_notification_metrics(
            endpoint="notifications_mark_read",
            current_user=current_user,
            action_type=normalized_action_type,
            updated=0,
            duration_ms=int((perf_counter() - query_started_at) * 1000),
        )
        return NotificationMarkReadResult(updated=0)

    now = utcnow()
    session.exec(
        sqlalchemy_update(NotificationEvent)
        .where(*clauses)
        .values(is_read=True, read_at=now)
    )

    commit_with_error_handling(
        session,
        logger=logger,
        action="Mark notifications read",
        conflict_detail="通知狀態更新發生衝突，請重試。",
        failure_detail="通知狀態更新失敗，請稍後再試。",
    )

    log_notification_metrics(
        endpoint="notifications_mark_read",
        current_user=current_user,
        action_type=normalized_action_type,
        updated=pending_count,
        duration_ms=int((perf_counter() - query_started_at) * 1000),
    )
    return NotificationMarkReadResult(updated=pending_count)


def handle_mark_single_notification_read(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID,
    logger: Any,
) -> NotificationMarkReadResult:
    item = session.get(NotificationEvent, notification_id)
    if not item or item.deleted_at is not None or item.receiver_user_id != current_user.id:
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=(item.receiver_user_id if item else None),
            action="NOTIFICATION_READ_DENIED",
            resource_type="notification",
            resource_id=notification_id,
            outcome=AuditEventOutcome.DENIED,
            reason="not_owner_or_missing",
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if item.is_read:
        return NotificationMarkReadResult(updated=0)

    item.is_read = True
    item.read_at = utcnow()
    session.add(item)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Mark single notification read",
        conflict_detail="通知狀態更新發生衝突，請重試。",
        failure_detail="通知狀態更新失敗，請稍後再試。",
    )
    return NotificationMarkReadResult(updated=1)


async def handle_retry_notification_delivery(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID,
) -> NotificationRetryResult:
    from app.api.routers import users as users_router_module

    item = session.get(NotificationEvent, notification_id)
    if not item or item.deleted_at is not None or item.receiver_user_id != current_user.id:
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=(item.receiver_user_id if item else None),
            action="NOTIFICATION_RETRY_DENIED",
            resource_type="notification",
            resource_id=notification_id,
            outcome=AuditEventOutcome.DENIED,
            reason="not_owner_or_missing",
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if not users_router_module.is_email_notification_enabled():
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=item.receiver_user_id,
            action="NOTIFICATION_RETRY_ERROR",
            resource_type="notification",
            resource_id=notification_id,
            outcome=AuditEventOutcome.ERROR,
            reason="provider_not_configured",
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email provider is not configured yet.",
        )

    if item.status not in {
        NotificationDeliveryStatus.FAILED,
        NotificationDeliveryStatus.THROTTLED,
    }:
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=item.receiver_user_id,
            action="NOTIFICATION_RETRY_DENIED",
            resource_type="notification",
            resource_id=notification_id,
            outcome=AuditEventOutcome.DENIED,
            reason="status_not_retryable",
            metadata={"status": item.status.value},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only FAILED or THROTTLED notifications can be retried.",
        )

    sender_name = "你的伴侶"
    sender_user_id = item.sender_user_id
    if sender_user_id:
        sender_user = session.get(models.User, sender_user_id)
        if sender_user:
            sender_name = sender_user.full_name or sender_user.email.split("@")[0] or sender_name

    action_type = "journal" if item.action_type == NotificationActionType.JOURNAL else "card"
    users_router_module.queue_partner_notification(
        receiver_email=item.receiver_email,
        sender_name=sender_name,
        action_type=action_type,  # type: ignore[arg-type]
        dedupe_key=item.dedupe_key,
        receiver_user_id=item.receiver_user_id,
        sender_user_id=item.sender_user_id,
        source_session_id=item.source_session_id,
        bypass_dedupe_cooldown=True,
    )
    return NotificationRetryResult(queued=True)

