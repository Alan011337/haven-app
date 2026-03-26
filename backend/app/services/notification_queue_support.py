from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any


def classify_notification_exception(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError,)):
        return "timeout"
    if isinstance(exc, (ConnectionError, OSError)):
        return "transport_error"
    if isinstance(exc, (ValueError, TypeError)):
        return "payload_error"
    return "unexpected_error"


def build_email_payload(sender_name: str, action_type: str) -> tuple[str, str]:
    if action_type == "journal":
        return (
            f"✨ 嘿！{sender_name} 剛剛在 Haven 寫下了新的心情",
            f"<strong>{sender_name}</strong> 剛分享了今天的日記，快去看看並給予回應吧！",
        )
    if action_type == "card":
        return (
            f"🃏 揭曉時刻！{sender_name} 回覆了你們的對話卡片",
            f"你們有一張卡片已經可以解鎖了！快去看看 <strong>{sender_name}</strong> 說了什麼。",
        )
    if action_type == "partner_bound":
        return (
            f"💕 {sender_name} 與你配對成功了",
            f"<strong>{sender_name}</strong> 已與你成為伴侶，快去看看對方的動態吧！",
        )
    if action_type == "time_capsule":
        return (
            "🕰 時光膠囊：回憶回來找你們了",
            "你們過去一起寫下的回憶，現在回來找你們了。快來看看當時的心情吧。",
        )
    if action_type == "active_care":
        return (
            "💬 Haven 想邀請你們",
            "好久沒一起互動了，抽一張牌或寫一句話給對方吧～",
        )
    if action_type == "mediation_invite":
        return (
            "🤝 調解模式：換位思考",
            "Haven 偵測到可能的情緒張力，邀請你們各自回答幾個引導式問題，幫助彼此理解。",
        )
    if action_type == "cooldown_started":
        return (
            "⏸ 冷卻模式已啟動",
            "你的伴侶啟動了冷卻時間，建議先休息一下，等時間過後再好好聊聊。",
        )
    raise ValueError(f"Unsupported notification action_type: {action_type}")


def resolve_notification_queue_context(
    *,
    event_type: str | None,
    default_cooldown_seconds: float,
    throttle_window_seconds: int | None,
) -> tuple[bool, float | None]:
    use_multichannel = bool(event_type)
    if not use_multichannel:
        return False, None
    if throttle_window_seconds is not None and int(throttle_window_seconds) > 0:
        return True, float(throttle_window_seconds)
    return True, float(default_cooldown_seconds)


def build_notification_event_kwargs(
    *,
    receiver_email: str,
    action_type: str,
    status: str,
    dedupe_key: str | None,
    receiver_user_id: uuid.UUID | None,
    sender_user_id: uuid.UUID | None,
    source_session_id: uuid.UUID | None,
    error_message: str | None = None,
    upsert_by_dedupe: bool = True,
) -> dict[str, Any]:
    return {
        "receiver_email": receiver_email,
        "action_type": action_type,
        "status": status,
        "dedupe_key": dedupe_key,
        "receiver_user_id": receiver_user_id,
        "sender_user_id": sender_user_id,
        "source_session_id": source_session_id,
        "error_message": error_message,
        "upsert_by_dedupe": upsert_by_dedupe,
    }


def build_backpressure_log_fields(*, backpressure: dict[str, Any]) -> tuple[str, int, int]:
    return (
        str(backpressure.get("reason", "unknown")),
        int(backpressure.get("depth", -1)),
        int(backpressure.get("oldest_pending_age_seconds", -1)),
    )


def resolve_email_fallback_delay_seconds(raw_delay_seconds: int | float | str | None) -> int:
    try:
        return max(0, int(raw_delay_seconds or 0))
    except (TypeError, ValueError):
        return 0


def should_attempt_email_fallback(
    *,
    delivered: bool,
    receiver_user_id: uuid.UUID | None,
    email_enabled: bool,
    receiver_opted_out: bool,
) -> bool:
    return (
        not delivered
        and receiver_user_id is not None
        and email_enabled
        and not receiver_opted_out
    )


async def run_notification_delivery(
    *,
    use_multichannel: bool,
    event_type: str | None,
    receiver_email: str,
    receiver_user_id: uuid.UUID | None,
    sender_name: str,
    action_type: str,
    email_fallback_delay_seconds: int,
    send_partner_notification_with_retry: Callable[..., Awaitable[bool]],
    is_email_notification_enabled: Callable[[], bool],
    is_receiver_email_opted_out: Callable[[uuid.UUID | None], bool],
    sleep: Callable[[float], Awaitable[Any]],
    dispatch_multichannel: Callable[..., Awaitable[dict[str, bool]]] | None = None,
) -> tuple[bool, bool]:
    if not use_multichannel:
        delivered = await send_partner_notification_with_retry(
            receiver_email=receiver_email,
            sender_name=sender_name,
            action_type=action_type,
        )
        return delivered, False

    if dispatch_multichannel is None:
        raise ValueError("dispatch_multichannel is required for multichannel notification delivery")

    results = await dispatch_multichannel(
        event_type=event_type,
        receiver_email=receiver_email,
        receiver_user_id=receiver_user_id,
        sender_name=sender_name,
        action_type=action_type,
    )
    delivered = any(results.values())
    if not should_attempt_email_fallback(
        delivered=delivered,
        receiver_user_id=receiver_user_id,
        email_enabled=is_email_notification_enabled(),
        receiver_opted_out=is_receiver_email_opted_out(receiver_user_id),
    ):
        return delivered, False

    if email_fallback_delay_seconds > 0:
        await sleep(float(email_fallback_delay_seconds))
    delivered = await send_partner_notification_with_retry(
        receiver_email=receiver_email,
        sender_name=sender_name,
        action_type=action_type,
    )
    return delivered, delivered


def resolve_delivery_terminal_status(*, delivered: bool) -> tuple[str, str | None]:
    if delivered:
        return "SENT", None
    return "FAILED", "retry_exhausted"


def resolve_exception_error_message(
    *,
    exc: Exception,
    classify_notification_exception: Callable[[Exception], str],
) -> str:
    if isinstance(exc, (RuntimeError, OSError, ValueError, TypeError)):
        return classify_notification_exception(exc)
    return "unexpected_error"
