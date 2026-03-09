from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlmodel import col

from app.api.deps import CurrentUser
from app.models.notification_event import (
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)

logger = logging.getLogger(__name__)


def normalize_action_type_or_raise(action_type: Optional[str]) -> Optional[str]:
    if action_type is None:
        return None
    normalized_action_type = action_type.strip().upper()
    if not normalized_action_type:
        return None
    if normalized_action_type not in {item.value for item in NotificationActionType}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type: {action_type}",
        )
    return normalized_action_type


def normalize_delivery_status_or_raise(delivery_status: Optional[str]) -> Optional[str]:
    if delivery_status is None:
        return None
    normalized_status = delivery_status.strip().upper()
    if not normalized_status:
        return None
    if normalized_status not in {item.value for item in NotificationDeliveryStatus}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {delivery_status}",
        )
    return normalized_status


def build_notification_filter_clauses(
    *,
    receiver_user_id: uuid.UUID,
    unread_only: bool = False,
    action_type: Optional[str] = None,
    delivery_status: Optional[str] = None,
    error_reason: Optional[str] = None,
) -> list[Any]:
    clauses: list[Any] = [
        NotificationEvent.receiver_user_id == receiver_user_id,
        NotificationEvent.deleted_at.is_(None),
    ]

    if unread_only:
        clauses.append(NotificationEvent.is_read.is_(False))
    if action_type:
        clauses.append(NotificationEvent.action_type == action_type)
    if delivery_status:
        clauses.append(NotificationEvent.status == delivery_status)

    normalized_error_reason = (error_reason or "").strip()
    if normalized_error_reason:
        clauses.append(NotificationEvent.error_message.is_not(None))
        clauses.append(col(NotificationEvent.error_message).ilike(f"%{normalized_error_reason}%"))

    return clauses


def log_notification_metrics(
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
