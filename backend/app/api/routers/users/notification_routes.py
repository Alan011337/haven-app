from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.api.routers.users.notification_handlers import (
    handle_mark_notifications_read,
    handle_mark_single_notification_read,
    handle_read_my_notifications,
    handle_read_my_notification_stats,
    handle_retry_notification_delivery,
)
from app.api.routers.users.push_handlers import (
    handle_delete_my_push_subscription,
    handle_dry_run_my_push_dispatch,
    handle_list_my_push_subscriptions,
    handle_upsert_my_push_subscription,
)
from app.schemas.notification import (
    NotificationEventPublic,
    NotificationMarkReadResult,
    NotificationRetryResult,
    NotificationStatsPublic,
    PushDispatchDryRunRequest,
    PushDispatchDryRunResult,
    PushSubscriptionCreate,
    PushSubscriptionDeleteResult,
    PushSubscriptionPublic,
    PushSubscriptionUpsertResult,
)

router = APIRouter()
# Keep logger name aligned with legacy users router to preserve existing patch hooks.
logger = logging.getLogger("app.api.routers.users.routes")


def _log_notification_metrics(
    *,
    endpoint: str,
    current_user: CurrentUser,
    unread_only: bool = False,
    action_type: Optional[str] = None,
    delivery_status: Optional[str] = None,
    error_reason: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    window_days: Optional[int] = None,
    result_count: Optional[int] = None,
    updated: Optional[int] = None,
    duration_ms: int,
) -> None:
    logger.info(
        (
            "notification_metrics endpoint=%s user_id=%s unread_only=%s "
            "action_type=%s status=%s error_reason=%s limit=%s offset=%s "
            "window_days=%s result_count=%s updated=%s duration_ms=%s"
        ),
        endpoint,
        current_user.id,
        unread_only,
        action_type,
        delivery_status,
        error_reason,
        limit,
        offset,
        window_days,
        result_count,
        updated,
        duration_ms,
    )


@router.get("/notifications", response_model=list[NotificationEventPublic])
def read_my_notifications(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = False,
    action_type: Optional[str] = None,
    delivery_status: Optional[str] = Query(default=None, alias="status"),
    error_reason: Optional[str] = Query(default=None),
):
    return handle_read_my_notifications(
        session=session,
        current_user=current_user,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
        action_type=action_type,
        delivery_status=delivery_status,
        error_reason=error_reason,
        log_notification_metrics=_log_notification_metrics,
    )


@router.get("/notifications/stats", response_model=NotificationStatsPublic)
def read_my_notification_stats(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    window_days: int = Query(default=7, ge=1, le=30),
    unread_only: bool = False,
    action_type: Optional[str] = None,
    delivery_status: Optional[str] = Query(default=None, alias="status"),
    error_reason: Optional[str] = Query(default=None),
) -> NotificationStatsPublic:
    return handle_read_my_notification_stats(
        session=session,
        current_user=current_user,
        window_days=window_days,
        unread_only=unread_only,
        action_type=action_type,
        delivery_status=delivery_status,
        error_reason=error_reason,
        log_notification_metrics=_log_notification_metrics,
    )


@router.post("/notifications/mark-read", response_model=NotificationMarkReadResult)
def mark_notifications_read(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    action_type: Optional[str] = None,
) -> NotificationMarkReadResult:
    return handle_mark_notifications_read(
        session=session,
        current_user=current_user,
        action_type=action_type,
        logger=logger,
        log_notification_metrics=_log_notification_metrics,
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationMarkReadResult)
def mark_single_notification_read(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID,
) -> NotificationMarkReadResult:
    return handle_mark_single_notification_read(
        session=session,
        current_user=current_user,
        notification_id=notification_id,
        logger=logger,
    )


@router.post("/notifications/{notification_id}/retry", response_model=NotificationRetryResult)
async def retry_notification_delivery(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    notification_id: uuid.UUID,
) -> NotificationRetryResult:
    return await handle_retry_notification_delivery(
        session=session,
        current_user=current_user,
        notification_id=notification_id,
    )


@router.get("/push-subscriptions", response_model=list[PushSubscriptionPublic])
def list_my_push_subscriptions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    include_inactive: bool = Query(default=True),
) -> list[PushSubscriptionPublic]:
    return handle_list_my_push_subscriptions(
        session=session,
        current_user=current_user,
        include_inactive=include_inactive,
    )


@router.post("/push-subscriptions", response_model=PushSubscriptionUpsertResult)
def upsert_my_push_subscription(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: PushSubscriptionCreate,
) -> PushSubscriptionUpsertResult:
    return handle_upsert_my_push_subscription(
        session=session,
        current_user=current_user,
        payload=payload,
    )


@router.post("/push-subscriptions/dry-run", response_model=PushDispatchDryRunResult)
def dry_run_my_push_dispatch(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: PushDispatchDryRunRequest,
) -> PushDispatchDryRunResult:
    return handle_dry_run_my_push_dispatch(
        session=session,
        current_user=current_user,
        payload=payload,
    )


@router.delete("/push-subscriptions/{subscription_id}", response_model=PushSubscriptionDeleteResult)
def delete_my_push_subscription(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    subscription_id: uuid.UUID,
) -> PushSubscriptionDeleteResult:
    return handle_delete_my_push_subscription(
        session=session,
        current_user=current_user,
        subscription_id=subscription_id,
    )
