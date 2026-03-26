# backend/app/services/notification_multichannel.py
"""
Multi-channel notification dispatch: email, in_app_ws, push.
Uses notification_trigger_matrix for channel fallback order.
Push is best-effort; dry-run-safe when provider unavailable.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import uuid
from datetime import datetime
from typing import Literal, Optional, TypedDict

from app.core.settings_domains import get_push_dispatch_settings
from app.services.notification_runtime_metrics import notification_runtime_metrics
from app.services.posthog_events import capture_posthog_event
from app.services.retry_backoff import compute_exponential_backoff_seconds
from app.services.notification_trigger_matrix import (
    get_channels_for_event,
    is_channel_disabled,
)

logger = logging.getLogger(__name__)

NotificationAction = Literal["journal", "card", "partner_bound", "time_capsule", "active_care", "mediation_invite", "cooldown_started"]
TriggerEventType = str  # e.g. journal_created, card_waiting, card_revealed, partner_bound

FAILURE_PROVIDER_UNAVAILABLE = "provider_unavailable"
FAILURE_NO_SUBSCRIPTIONS = "no_subscriptions"
FAILURE_CHANNEL_DISABLED = "channel_disabled"
FAILURE_TRANSPORT_ERROR = "transport_error"
FAILURE_UNEXPECTED_ERROR = "unexpected_error"


class DispatchResult(TypedDict):
    success: bool
    reason: str | None


def _push_dispatch_max_active_subscriptions() -> int:
    return get_push_dispatch_settings().max_active_subscriptions


def _push_dispatch_batch_size() -> int:
    return get_push_dispatch_settings().batch_size


def _push_dispatch_retry_attempts() -> int:
    return get_push_dispatch_settings().retry_attempts


def _push_dispatch_retry_base_seconds() -> float:
    return get_push_dispatch_settings().retry_base_seconds


def _push_dispatch_max_concurrency() -> int:
    return get_push_dispatch_settings().max_concurrency


def _load_active_push_subscriptions(*, receiver_user_id: uuid.UUID) -> list:
    from sqlalchemy import and_, or_
    from sqlmodel import Session, col, select

    from app.db.session import engine
    from app.models.push_subscription import PushSubscription, PushSubscriptionState

    max_rows = _push_dispatch_max_active_subscriptions()
    batch_size = min(max_rows, _push_dispatch_batch_size())
    collected: list = []
    cursor_updated_at: datetime | None = None
    cursor_id: uuid.UUID | None = None

    with Session(engine) as session:
        while len(collected) < max_rows:
            statement = (
                select(PushSubscription)
                .where(
                    PushSubscription.user_id == receiver_user_id,
                    PushSubscription.state == PushSubscriptionState.ACTIVE,
                )
                .order_by(col(PushSubscription.updated_at).desc(), col(PushSubscription.id).desc())
                .limit(batch_size)
            )
            if cursor_updated_at is not None and cursor_id is not None:
                statement = statement.where(
                    or_(
                        col(PushSubscription.updated_at) < cursor_updated_at,
                        and_(
                            col(PushSubscription.updated_at) == cursor_updated_at,
                            col(PushSubscription.id) < cursor_id,
                        ),
                    )
                )
            batch_rows = session.exec(statement).all()
            if not batch_rows:
                break
            collected.extend(batch_rows)
            if len(collected) >= max_rows:
                break
            last_row = batch_rows[-1]
            cursor_updated_at = last_row.updated_at
            cursor_id = last_row.id
            if len(batch_rows) < batch_size:
                break
    return collected[:max_rows]


def _classify_dispatch_exception(exc: Exception) -> str:
    if isinstance(exc, ImportError):
        return FAILURE_PROVIDER_UNAVAILABLE
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        return FAILURE_TRANSPORT_ERROR
    return FAILURE_UNEXPECTED_ERROR


def _build_in_app_ws_payload(sender_name: str, action_type: NotificationAction) -> dict:
    if action_type == "journal":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "journal",
            "message": f"{sender_name} 剛剛寫了新的日記",
        }
    if action_type == "card":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "card",
            "message": f"{sender_name} 回覆了你們的對話卡片",
        }
    if action_type == "partner_bound":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "partner_bound",
            "message": f"{sender_name} 與你配對成功了",
        }
    if action_type == "time_capsule":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "time_capsule",
            "message": "時光膠囊到了，一起回顧過去的回憶吧",
        }
    if action_type == "active_care":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "active_care",
            "message": "好久沒一起互動了，來聊聊吧",
        }
    if action_type == "mediation_invite":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "mediation_invite",
            "message": "Haven 邀請你們換位思考，一起回答幾個問題",
        }
    if action_type == "cooldown_started":
        return {
            "event": "NEW_NOTIFICATION",
            "type": "cooldown_started",
            "message": "冷卻模式已啟動，先休息一下吧",
        }
    return {"event": "NEW_NOTIFICATION", "type": str(action_type), "message": "新通知"}


def _result(success: bool, reason: str | None = None) -> DispatchResult:
    return {"success": bool(success), "reason": reason}


async def dispatch_in_app_ws(
    *,
    receiver_user_id: uuid.UUID,
    sender_name: str,
    action_type: NotificationAction,
) -> DispatchResult:
    """Send in-app WebSocket notification."""
    if is_channel_disabled("in_app_ws"):
        return _result(False, FAILURE_CHANNEL_DISABLED)
    try:
        from app.core.socket_manager import manager

        payload = _build_in_app_ws_payload(sender_name=sender_name, action_type=action_type)
        await manager.send_personal_message(payload, str(receiver_user_id))
        return _result(True)
    except (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError, RuntimeError) as exc:
        logger.debug("in_app_ws dispatch failed: %s", type(exc).__name__)
        return _result(False, _classify_dispatch_exception(exc))
    except Exception as exc:
        logger.debug("in_app_ws dispatch failed: %s", type(exc).__name__)
        return _result(False, _classify_dispatch_exception(exc))


def _push_provider_available() -> bool:
    """Check if Web Push provider (pywebpush + VAPID) is available."""
    if importlib.util.find_spec("pywebpush") is None:
        return False
    from app.core.config import settings as runtime_settings

    return bool(
        runtime_settings.WEBPUSH_ENABLED
        and runtime_settings.PUSH_NOTIFICATIONS_ENABLED
        and runtime_settings.PUSH_VAPID_PUBLIC_KEY
        and runtime_settings.PUSH_VAPID_PRIVATE_KEY
    )


async def dispatch_push(
    *,
    receiver_user_id: uuid.UUID,
    sender_name: str,
    action_type: NotificationAction,
    ttl_seconds: int = 3600,
) -> DispatchResult:
    """
    Best-effort Web Push dispatch using existing push subscription records.
    Dry-run-safe: returns False without raising when provider unavailable.
    """
    del ttl_seconds
    if is_channel_disabled("push"):
        return _result(False, FAILURE_CHANNEL_DISABLED)
    if not _push_provider_available():
        logger.debug("Push provider unavailable (pywebpush/VAPID), skipping push dispatch")
        return _result(False, FAILURE_PROVIDER_UNAVAILABLE)

    try:
        rows = _load_active_push_subscriptions(receiver_user_id=receiver_user_id)

        if not rows:
            return _result(False, FAILURE_NO_SUBSCRIPTIONS)

        if action_type == "journal":
            title = f"✨ {sender_name} 寫了新的日記"
            body = "快去看看並給予回應吧！"
        elif action_type == "card":
            title = f"🃏 {sender_name} 回覆了卡片"
            body = "你們有一張卡片已經可以解鎖了！"
        elif action_type == "partner_bound":
            title = f"💕 {sender_name} 與你配對成功了"
            body = "快去看看對方的動態吧！"
        elif action_type == "time_capsule":
            title = "🕰 時光膠囊：回憶回來找你們了"
            body = "一起回顧過去寫下的心情吧"
        elif action_type == "active_care":
            title = "💬 Haven 想邀請你們"
            body = "好久沒一起互動了，抽一張牌或寫一句話給對方吧～"
        elif action_type == "mediation_invite":
            title = "🤝 調解模式：換位思考"
            body = "Haven 邀請你們各自回答幾個引導式問題"
        elif action_type == "cooldown_started":
            title = "⏸ 冷卻模式已啟動"
            body = "建議先休息一下，等時間過後再好好聊聊"
        else:
            title = "Haven"
            body = "你有一則新通知"

        from app.core.config import settings as runtime_settings

        vapid_private = (runtime_settings.PUSH_VAPID_PRIVATE_KEY or "").strip()
        vapid_subject = (runtime_settings.PUSH_VAPID_SUBJECT or "mailto:security@haven.app").strip()

        try:
            import pywebpush
        except ImportError:
            return _result(False, FAILURE_PROVIDER_UNAVAILABLE)

        sent = 0
        retry_attempts = _push_dispatch_retry_attempts()
        retry_base_seconds = _push_dispatch_retry_base_seconds()
        send_semaphore = asyncio.Semaphore(_push_dispatch_max_concurrency())

        async def _send_to_subscription(sub) -> bool:
            async with send_semaphore:
                for attempt in range(retry_attempts + 1):
                    try:
                        await asyncio.to_thread(
                            pywebpush.webpush,
                            subscription_info={
                                "endpoint": sub.endpoint,
                                "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
                            },
                            data=json.dumps({"title": title, "body": body}),
                            vapid_private_key=vapid_private,
                            vapid_claims={"sub": vapid_subject},
                        )
                        return True
                    except (
                        asyncio.TimeoutError,
                        TimeoutError,
                        ConnectionError,
                        OSError,
                        RuntimeError,
                    ) as exc:
                        reason = _classify_dispatch_exception(exc)
                        logger.debug(
                            "Push to subscription %s failed: %s (attempt=%s/%s reason=%s)",
                            sub.id,
                            type(exc).__name__,
                            attempt + 1,
                            retry_attempts + 1,
                            reason,
                        )
                        if reason == FAILURE_TRANSPORT_ERROR and attempt < retry_attempts:
                            await asyncio.sleep(
                                compute_exponential_backoff_seconds(
                                    attempt=attempt,
                                    base_seconds=retry_base_seconds,
                                    max_seconds=2.0,
                                    jitter_ratio=0.0,
                                )
                            )
                            continue
                        return False
                    except Exception as exc:
                        reason = _classify_dispatch_exception(exc)
                        logger.debug(
                            "Push to subscription %s failed: %s (attempt=%s/%s reason=%s)",
                            sub.id,
                            type(exc).__name__,
                            attempt + 1,
                            retry_attempts + 1,
                            reason,
                        )
                        if reason == FAILURE_TRANSPORT_ERROR and attempt < retry_attempts:
                            await asyncio.sleep(
                                compute_exponential_backoff_seconds(
                                    attempt=attempt,
                                    base_seconds=retry_base_seconds,
                                    max_seconds=2.0,
                                    jitter_ratio=0.0,
                                )
                            )
                            continue
                        return False
                return False

        push_results = await asyncio.gather(*[_send_to_subscription(sub) for sub in rows])
        sent = sum(1 for ok in push_results if ok)

        if sent > 0:
            capture_posthog_event(
                event_name="webpush_sent",
                distinct_id=str(receiver_user_id),
                properties={"action_type": action_type, "subscriptions_sent": sent},
            )
            return _result(True)
        return _result(False, FAILURE_TRANSPORT_ERROR)
    except Exception as exc:
        logger.debug("Push dispatch failed: %s", type(exc).__name__)
        return _result(False, _classify_dispatch_exception(exc))


async def dispatch_multichannel(
    *,
    event_type: TriggerEventType,
    receiver_email: str,
    receiver_user_id: Optional[uuid.UUID],
    sender_name: str,
    action_type: NotificationAction,
    detailed: bool = False,
) -> dict[str, bool] | dict[str, DispatchResult]:
    """
    Dispatch to all channels enabled for the event type (email, in_app_ws, push).
    Returns dict of channel -> success by default.
    When `detailed=True`, returns dict of channel -> {success, reason}.
    """
    channels = get_channels_for_event(event_type)
    bool_results: dict[str, bool] = {}
    detailed_results: dict[str, DispatchResult] = {}

    for ch in channels:
        notification_runtime_metrics.record_attempt(channel=ch)

        dispatch_result: DispatchResult
        if ch == "email":
            from app.services.notification import is_email_notification_enabled, send_partner_notification

            if not is_email_notification_enabled():
                dispatch_result = _result(False, FAILURE_PROVIDER_UNAVAILABLE)
            else:
                try:
                    ok = await send_partner_notification(
                        receiver_email=receiver_email,
                        sender_name=sender_name,
                        action_type=action_type,
                    )
                    dispatch_result = _result(ok, None if ok else FAILURE_TRANSPORT_ERROR)
                except (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError, RuntimeError) as exc:
                    logger.debug("Email dispatch failed: %s", type(exc).__name__)
                    dispatch_result = _result(False, _classify_dispatch_exception(exc))
                except Exception as exc:
                    logger.debug("Email dispatch failed: %s", type(exc).__name__)
                    dispatch_result = _result(False, _classify_dispatch_exception(exc))
        elif ch == "in_app_ws":
            if receiver_user_id:
                dispatch_result = await dispatch_in_app_ws(
                    receiver_user_id=receiver_user_id,
                    sender_name=sender_name,
                    action_type=action_type,
                )
            else:
                dispatch_result = _result(False, FAILURE_UNEXPECTED_ERROR)
        elif ch == "push":
            if receiver_user_id:
                dispatch_result = await dispatch_push(
                    receiver_user_id=receiver_user_id,
                    sender_name=sender_name,
                    action_type=action_type,
                )
            else:
                dispatch_result = _result(False, FAILURE_UNEXPECTED_ERROR)
        else:
            dispatch_result = _result(False, FAILURE_UNEXPECTED_ERROR)

        notification_runtime_metrics.record_result(
            channel=ch,
            success=dispatch_result["success"],
            reason=dispatch_result.get("reason"),
        )
        bool_results[ch] = dispatch_result["success"]
        detailed_results[ch] = dispatch_result

    if detailed:
        return detailed_results
    return bool_results
