# backend/app/services/notification.py

import asyncio
import logging
import os
import threading
import time
import uuid
from typing import Literal, Optional

from app.core.config import settings
from app.core.log_redaction import redact_email
from app.models.user_onboarding_consent import UserOnboardingConsent
from app.services.notification_queue_support import (
    build_email_payload,
    build_backpressure_log_fields,
    build_notification_event_kwargs,
    classify_notification_exception,
    resolve_delivery_terminal_status,
    resolve_email_fallback_delay_seconds,
    resolve_exception_error_message,
    resolve_notification_queue_context,
    run_notification_delivery,
)
from app.services.posthog_events import capture_posthog_event
from app.services.notification_dedupe_store import create_notification_dedupe_store
from app.services.retry_backoff import compute_exponential_backoff_seconds

try:
    import resend
except ImportError:  # pragma: no cover
    resend = None

logger = logging.getLogger(__name__)

NotificationAction = Literal["journal", "card", "partner_bound", "time_capsule", "active_care", "mediation_invite", "cooldown_started"]
NotificationDedupeEvent = Literal[
    "journal",
    "card_waiting",
    "card_revealed",
    "partner_bound",
    "time_capsule",
    "active_care",
    "mediation_invite",
    "cooldown_started",
]

_notification_dedupe_store = create_notification_dedupe_store()
_notification_pending_tasks = 0
_notification_pending_tasks_lock = threading.Lock()
_notification_consent_cache: dict[uuid.UUID, tuple[float, bool]] = {}
_notification_consent_cache_lock = threading.Lock()


def reset_notification_dedupe_state_for_test() -> None:
    _notification_dedupe_store.reset()


def get_notification_queue_depth() -> int:
    with _notification_pending_tasks_lock:
        return max(0, int(_notification_pending_tasks))


def _notification_consent_cache_ttl_seconds() -> int:
    raw = getattr(settings, "NOTIFICATION_CONSENT_CACHE_SECONDS", 30)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 30


def invalidate_notification_preference_cache(user_id: uuid.UUID | None) -> None:
    if user_id is None:
        return
    with _notification_consent_cache_lock:
        _notification_consent_cache.pop(user_id, None)


def _runtime_config_value(
    *,
    env_key: str,
    settings_attr: str,
    default: str = "",
) -> str:
    env_raw = os.getenv(env_key)
    if env_raw is not None:
        env_val = env_raw.strip()
        if env_val:
            return env_val

    settings_val = getattr(settings, settings_attr, "")
    if isinstance(settings_val, str):
        stripped = settings_val.strip()
        if stripped:
            return stripped

    return default


def _is_notification_outbox_enabled() -> bool:
    from app.services.notification_outbox_config import is_notification_outbox_enabled

    return is_notification_outbox_enabled()


def is_email_notification_enabled() -> bool:
    if not bool(getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True)):
        return False
    if not resend:
        return False
    api_key = _runtime_config_value(env_key="RESEND_API_KEY", settings_attr="RESEND_API_KEY")
    return bool(api_key)


def _is_receiver_email_opted_out(receiver_user_id: uuid.UUID | None) -> bool:
    if receiver_user_id is None:
        return False
    ttl_seconds = _notification_consent_cache_ttl_seconds()
    if ttl_seconds > 0:
        now_mono = time.monotonic()
        with _notification_consent_cache_lock:
            cached = _notification_consent_cache.get(receiver_user_id)
            if cached and cached[0] > now_mono:
                return bool(cached[1])
    try:
        from sqlmodel import Session
        from app.db.session import engine

        opted_out = False
        with Session(engine) as session:
            consent = session.get(UserOnboardingConsent, receiver_user_id)
            if consent:
                opted_out = (consent.notification_frequency or "").strip().lower() == "off"

        if ttl_seconds > 0:
            expiry = time.monotonic() + float(ttl_seconds)
            with _notification_consent_cache_lock:
                _notification_consent_cache[receiver_user_id] = (expiry, opted_out)
        return opted_out
    except Exception:
        return False


def _prepare_resend_client() -> bool:
    if not resend:
        return False
    api_key = _runtime_config_value(env_key="RESEND_API_KEY", settings_attr="RESEND_API_KEY")
    if not api_key:
        return False
    resend.api_key = api_key
    return True

def build_notification_dedupe_key(
    *,
    event_type: NotificationDedupeEvent,
    sender_user_id: uuid.UUID,
    receiver_user_id: uuid.UUID,
    scope_id: uuid.UUID | str | None = None,
) -> str:
    sender = str(sender_user_id)
    receiver = str(receiver_user_id)
    if scope_id is None:
        return f"{event_type}:{sender}:{receiver}"
    return f"{event_type}:{str(scope_id)}:{sender}:{receiver}"


def _reserve_notification_slot(
    dedupe_key: str | None,
    *,
    cooldown_seconds: float | None = None,
) -> bool:
    if not dedupe_key:
        return True
    default_cooldown = float(settings.NOTIFICATION_COOLDOWN_SECONDS)
    sec = cooldown_seconds if cooldown_seconds is not None else default_cooldown
    if sec <= 0:
        return True
    return _notification_dedupe_store.reserve(
        dedupe_key=dedupe_key,
        cooldown_seconds=sec,
    )


def _release_notification_slot(dedupe_key: str | None) -> None:
    if not dedupe_key:
        return
    _notification_dedupe_store.release(dedupe_key=dedupe_key)


def _record_notification_status(
    *,
    receiver_email: str,
    action_type: NotificationAction,
    status: str,
    dedupe_key: str | None = None,
    receiver_user_id: Optional[uuid.UUID] = None,
    sender_user_id: Optional[uuid.UUID] = None,
    source_session_id: Optional[uuid.UUID] = None,
    error_message: str | None = None,
) -> None:
    _record_notification_event(
        **build_notification_event_kwargs(
            receiver_email=receiver_email,
            action_type=action_type,
            status=status,
            dedupe_key=dedupe_key,
            receiver_user_id=receiver_user_id,
            sender_user_id=sender_user_id,
            source_session_id=source_session_id,
            error_message=error_message,
        )
    )


def _release_slot_and_record_notification_status(
    *,
    dedupe_reserved: bool,
    dedupe_key: str | None,
    receiver_email: str,
    action_type: NotificationAction,
    status: str,
    receiver_user_id: Optional[uuid.UUID] = None,
    sender_user_id: Optional[uuid.UUID] = None,
    source_session_id: Optional[uuid.UUID] = None,
    error_message: str | None = None,
) -> None:
    if dedupe_reserved:
        _release_notification_slot(dedupe_key)
    _record_notification_status(
        receiver_email=receiver_email,
        action_type=action_type,
        status=status,
        dedupe_key=dedupe_key,
        receiver_user_id=receiver_user_id,
        sender_user_id=sender_user_id,
        source_session_id=source_session_id,
        error_message=error_message,
    )


def _record_notification_event(
    *,
    receiver_email: str,
    action_type: NotificationAction,
    status: str,
    dedupe_key: str | None = None,
    receiver_user_id: Optional[uuid.UUID] = None,
    sender_user_id: Optional[uuid.UUID] = None,
    source_session_id: Optional[uuid.UUID] = None,
    error_message: str | None = None,
    upsert_by_dedupe: bool = False,
) -> None:
    try:
        from sqlmodel import Session, select, col
        from sqlalchemy.exc import IntegrityError, SQLAlchemyError

        from app.db.session import engine
        from app.core.datetime_utils import utcnow
        from app.models.notification_event import (
            NotificationActionType,
            NotificationChannel,
            NotificationDeliveryStatus,
            NotificationEvent,
        )

        with Session(engine) as session:
            action_type_value = NotificationActionType(action_type.upper())
            status_value = NotificationDeliveryStatus(status)
            read_at = utcnow() if status == "THROTTLED" else None

            def _find_row_by_dedupe() -> NotificationEvent | None:
                if not (upsert_by_dedupe and dedupe_key):
                    return None
                statement = (
                    select(NotificationEvent)
                    .where(
                        NotificationEvent.dedupe_key == dedupe_key,
                        NotificationEvent.receiver_email == receiver_email,
                    )
                    .order_by(col(NotificationEvent.created_at).desc())
                )
                return session.exec(statement).first()

            def _apply_values(row: NotificationEvent) -> None:
                row.channel = NotificationChannel.EMAIL
                row.action_type = action_type_value
                row.status = status_value
                row.receiver_email = receiver_email
                row.dedupe_key = dedupe_key
                row.receiver_user_id = receiver_user_id
                row.sender_user_id = sender_user_id
                row.source_session_id = source_session_id
                row.error_message = error_message
                if status == "THROTTLED":
                    row.is_read = True
                    row.read_at = read_at

            row = _find_row_by_dedupe()
            if row:
                _apply_values(row)
            else:
                row = NotificationEvent(
                    channel=NotificationChannel.EMAIL,
                    action_type=action_type_value,
                    status=status_value,
                    receiver_email=receiver_email,
                    dedupe_key=dedupe_key,
                    receiver_user_id=receiver_user_id,
                    sender_user_id=sender_user_id,
                    source_session_id=source_session_id,
                    error_message=error_message,
                    is_read=status == "THROTTLED",
                    read_at=read_at,
                )
            session.add(row)

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if not (upsert_by_dedupe and dedupe_key):
                    raise
                row = _find_row_by_dedupe()
                if row is None:
                    raise
                _apply_values(row)
                session.add(row)
                try:
                    session.commit()
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.warning(
                        "Notification event upsert commit failed: reason=%s",
                        type(e).__name__,
                    )
                    raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.warning(
                    "Notification event commit failed: reason=%s",
                    type(e).__name__,
                )
                raise
    except Exception as exc:
        logger.debug(
            "Skip notification event logging due to: reason=%s",
            type(exc).__name__,
        )


async def send_partner_notification(
    receiver_email: str,
    sender_name: str,
    action_type: NotificationAction,
) -> bool:
    """
    發送 Email 通知給伴侶
    action_type: "journal" (寫了日記) 或 "card" (回覆了牌組)
    """
    if not _prepare_resend_client():
        logger.warning("⚠️ 郵件供應商未就緒（resend/RESEND_API_KEY），跳過郵件發送")
        return False

    try:
        subject, html_content = build_email_payload(sender_name=sender_name, action_type=action_type)
    except ValueError:
        logger.warning("⚠️ 未知 action_type=%s，跳過郵件發送", action_type)
        return False

    from_email = _runtime_config_value(
        env_key="RESEND_FROM_EMAIL",
        settings_attr="RESEND_FROM_EMAIL",
        default="Haven <onboarding@resend.dev>",
    )
    email_payload = {
        "from": from_email,
        "to": receiver_email,
        "subject": subject,
        "html": html_content,
    }

    try:
        # resend SDK 為同步呼叫，放到 thread 避免阻塞事件迴圈。
        await asyncio.to_thread(resend.Emails.send, email_payload)
        logger.info("📧 通知信件已發送至 %s", redact_email(receiver_email))
        capture_posthog_event(
            event_name="email_notification_sent",
            distinct_id="system",
            properties={"action_type": action_type},
        )
        return True
    except (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError, RuntimeError) as e:
        logger.error(
            "❌ 郵件發送失敗: reason=%s class=%s",
            type(e).__name__,
            classify_notification_exception(e),
        )
        return False
    except Exception as e:
        logger.error(
            "❌ 郵件發送失敗: reason=%s class=unexpected_error",
            type(e).__name__,
        )
        return False


async def send_partner_notification_with_retry(
    receiver_email: str,
    sender_name: str,
    action_type: NotificationAction,
    *,
    max_retries: int = 2,
    base_delay_seconds: float = 1.0,
) -> bool:
    for attempt in range(max_retries + 1):
        success = await send_partner_notification(
            receiver_email=receiver_email,
            sender_name=sender_name,
            action_type=action_type,
        )
        if success:
            return True

        if attempt < max_retries:
            await asyncio.sleep(
                compute_exponential_backoff_seconds(
                    attempt=attempt,
                    base_seconds=base_delay_seconds,
                    max_seconds=10.0,
                    jitter_ratio=0.0,
                )
            )

    return False


def queue_partner_notification(
    receiver_email: str,
    sender_name: str,
    action_type: NotificationAction,
    *,
    dedupe_key: str | None = None,
    receiver_user_id: Optional[uuid.UUID] = None,
    sender_user_id: Optional[uuid.UUID] = None,
    source_session_id: Optional[uuid.UUID] = None,
    bypass_dedupe_cooldown: bool = False,
    event_type: Optional[str] = None,
) -> None:
    global _notification_pending_tasks
    dedupe_reserved = False
    throttle_window_seconds: int | None = None
    if event_type:
        from app.services.notification_trigger_matrix import get_throttle_window_seconds

        throttle_window_seconds = get_throttle_window_seconds(event_type)
    use_multichannel, cooldown_sec = resolve_notification_queue_context(
        event_type=event_type,
        default_cooldown_seconds=float(settings.NOTIFICATION_COOLDOWN_SECONDS),
        throttle_window_seconds=throttle_window_seconds,
    )
    if not bypass_dedupe_cooldown:
        dedupe_reserved = _reserve_notification_slot(dedupe_key, cooldown_seconds=cooldown_sec)
        if not dedupe_reserved:
            _record_notification_status(
                receiver_email=receiver_email,
                action_type=action_type,
                status="THROTTLED",
                dedupe_key=dedupe_key,
                receiver_user_id=receiver_user_id,
                sender_user_id=sender_user_id,
                source_session_id=source_session_id,
            )
            logger.info("🔕 通知已節流略過: %s (%s)", redact_email(receiver_email), action_type)
            return

    if use_multichannel:
        from app.services.notification_trigger_matrix import get_channels_for_event

        channels = get_channels_for_event(event_type)
        if not channels:
            _release_slot_and_record_notification_status(
                dedupe_reserved=dedupe_reserved,
                dedupe_key=dedupe_key,
                receiver_email=receiver_email,
                action_type=action_type,
                status="FAILED",
                receiver_user_id=receiver_user_id,
                sender_user_id=sender_user_id,
                source_session_id=source_session_id,
                error_message="no_channels_enabled",
            )
            logger.info("ℹ️ 通知觸發已停用或無可用頻道：%s (%s)", redact_email(receiver_email), event_type)
            return
    elif not is_email_notification_enabled():
        _release_slot_and_record_notification_status(
            dedupe_reserved=dedupe_reserved,
            dedupe_key=dedupe_key,
            receiver_email=receiver_email,
            action_type=action_type,
            status="FAILED",
            receiver_user_id=receiver_user_id,
            sender_user_id=sender_user_id,
            source_session_id=source_session_id,
            error_message="provider_unavailable",
        )
        logger.info("ℹ️ 郵件供應商未配置，略過通知排程：%s (%s)", redact_email(receiver_email), action_type)
        return

    _record_notification_status(
        receiver_email=receiver_email,
        action_type=action_type,
        status="QUEUED",
        dedupe_key=dedupe_key,
        receiver_user_id=receiver_user_id,
        sender_user_id=sender_user_id,
        source_session_id=source_session_id,
    )
    capture_posthog_event(
        event_name="email_notification_queued",
        distinct_id="system",
        properties={"action_type": action_type, "event_type": event_type or "none"},
    )

    if _is_notification_outbox_enabled():
        from app.services.notification_outbox import (
            enqueue_notification_outbox,
            evaluate_notification_outbox_backpressure,
        )

        backpressure = evaluate_notification_outbox_backpressure(
            event_type=event_type if use_multichannel else None,
            action_type=action_type,
        )
        if bool(backpressure.get("throttle", False)):
            _release_slot_and_record_notification_status(
                dedupe_reserved=dedupe_reserved,
                dedupe_key=dedupe_key,
                receiver_email=receiver_email,
                action_type=action_type,
                status="THROTTLED",
                receiver_user_id=receiver_user_id,
                sender_user_id=sender_user_id,
                source_session_id=source_session_id,
                error_message="outbox_backpressure",
            )
            reason, depth, oldest_pending_age_seconds = build_backpressure_log_fields(
                backpressure=backpressure
            )
            logger.warning(
                (
                    "⚠️ 通知 outbox 進入節流保護，略過排程：receiver=%s action=%s "
                    "reason=%s depth=%s oldest_pending_age_seconds=%s"
                ),
                redact_email(receiver_email),
                action_type,
                reason,
                depth,
                oldest_pending_age_seconds,
            )
            return

        outbox_id = enqueue_notification_outbox(
            receiver_email=receiver_email,
            sender_name=sender_name,
            action_type=action_type,
            event_type=event_type if use_multichannel else None,
            dedupe_key=dedupe_key,
            dedupe_slot_reserved=dedupe_reserved,
            receiver_user_id=receiver_user_id,
            sender_user_id=sender_user_id,
            source_session_id=source_session_id,
        )
        if outbox_id is None:
            _release_slot_and_record_notification_status(
                dedupe_reserved=dedupe_reserved,
                dedupe_key=dedupe_key,
                receiver_email=receiver_email,
                action_type=action_type,
                status="FAILED",
                receiver_user_id=receiver_user_id,
                sender_user_id=sender_user_id,
                source_session_id=source_session_id,
                error_message="outbox_enqueue_failed",
            )
            logger.warning("⚠️ 通知 outbox 排程失敗：%s (%s)", redact_email(receiver_email), action_type)
            return

        logger.info(
            "📮 通知已寫入 outbox：id=%s receiver=%s action=%s",
            outbox_id,
            redact_email(receiver_email),
            action_type,
        )
        return

    async def _runner() -> None:
        global _notification_pending_tasks
        try:
            try:
                dispatch_multichannel = None
                if use_multichannel:
                    from app.services.notification_multichannel import dispatch_multichannel

                delivered, used_multichannel_fallback = await run_notification_delivery(
                    use_multichannel=use_multichannel,
                    event_type=event_type,
                    receiver_email=receiver_email,
                    receiver_user_id=receiver_user_id,
                    sender_name=sender_name,
                    action_type=action_type,
                    email_fallback_delay_seconds=resolve_email_fallback_delay_seconds(
                        getattr(settings, "NOTIFICATION_EMAIL_FALLBACK_DELAY_SECONDS", 300)
                    ),
                    send_partner_notification_with_retry=send_partner_notification_with_retry,
                    is_email_notification_enabled=is_email_notification_enabled,
                    is_receiver_email_opted_out=_is_receiver_email_opted_out,
                    sleep=asyncio.sleep,
                    dispatch_multichannel=dispatch_multichannel if use_multichannel else None,
                )
                if used_multichannel_fallback:
                    capture_posthog_event(
                        event_name="email_notification_sent",
                        distinct_id="system",
                        properties={
                            "action_type": action_type,
                            "source": "multichannel_fallback",
                        },
                    )
            except asyncio.CancelledError:
                _release_slot_and_record_notification_status(
                    dedupe_reserved=dedupe_reserved,
                    dedupe_key=dedupe_key,
                    receiver_email=receiver_email,
                    action_type=action_type,
                    status="FAILED",
                    receiver_user_id=receiver_user_id,
                    sender_user_id=sender_user_id,
                    source_session_id=source_session_id,
                    error_message="task_cancelled",
                )
                logger.info("ℹ️ 通知背景任務已取消：%s (%s)", redact_email(receiver_email), action_type)
                return
            except (RuntimeError, OSError, ValueError, TypeError) as exc:
                _release_slot_and_record_notification_status(
                    dedupe_reserved=dedupe_reserved,
                    dedupe_key=dedupe_key,
                    receiver_email=receiver_email,
                    action_type=action_type,
                    status="FAILED",
                    receiver_user_id=receiver_user_id,
                    sender_user_id=sender_user_id,
                    source_session_id=source_session_id,
                    error_message=resolve_exception_error_message(
                        exc=exc,
                        classify_notification_exception=classify_notification_exception,
                    ),
                )
                logger.error(
                    "❌ 通知背景任務執行失敗：%s (%s) reason=%s",
                    redact_email(receiver_email),
                    action_type,
                    type(exc).__name__,
                )
                return
            except Exception as exc:
                _release_slot_and_record_notification_status(
                    dedupe_reserved=dedupe_reserved,
                    dedupe_key=dedupe_key,
                    receiver_email=receiver_email,
                    action_type=action_type,
                    status="FAILED",
                    receiver_user_id=receiver_user_id,
                    sender_user_id=sender_user_id,
                    source_session_id=source_session_id,
                    error_message=resolve_exception_error_message(
                        exc=exc,
                        classify_notification_exception=classify_notification_exception,
                    ),
                )
                logger.error(
                    "❌ 通知背景任務執行失敗（未分類）：%s (%s) reason=%s",
                    redact_email(receiver_email),
                    action_type,
                    type(exc).__name__,
                )
                return

            terminal_status, terminal_error_message = resolve_delivery_terminal_status(
                delivered=delivered
            )
            if terminal_status == "SENT":
                _record_notification_status(
                    receiver_email=receiver_email,
                    action_type=action_type,
                    status=terminal_status,
                    dedupe_key=dedupe_key,
                    receiver_user_id=receiver_user_id,
                    sender_user_id=sender_user_id,
                    source_session_id=source_session_id,
                )
            else:
                _release_slot_and_record_notification_status(
                    dedupe_reserved=dedupe_reserved,
                    dedupe_key=dedupe_key,
                    receiver_email=receiver_email,
                    action_type=action_type,
                    status=terminal_status,
                    receiver_user_id=receiver_user_id,
                    sender_user_id=sender_user_id,
                    source_session_id=source_session_id,
                    error_message=terminal_error_message,
                )
                logger.warning("⚠️ 通知最終仍未送達：%s (%s)", redact_email(receiver_email), action_type)
        finally:
            with _notification_pending_tasks_lock:
                _notification_pending_tasks = max(0, _notification_pending_tasks - 1)

    try:
        with _notification_pending_tasks_lock:
            _notification_pending_tasks += 1
        task = asyncio.create_task(_runner())
    except RuntimeError:
        with _notification_pending_tasks_lock:
            _notification_pending_tasks = max(0, _notification_pending_tasks - 1)
        _release_slot_and_record_notification_status(
            dedupe_reserved=dedupe_reserved,
            dedupe_key=dedupe_key,
            receiver_email=receiver_email,
            action_type=action_type,
            status="FAILED",
            receiver_user_id=receiver_user_id,
            sender_user_id=sender_user_id,
            source_session_id=source_session_id,
            error_message="no_event_loop",
        )
        logger.warning("⚠️ 目前無可用事件迴圈，略過通知排程")
        return

    def _on_done(completed_task: "asyncio.Task[None]") -> None:
        try:
            completed_task.result()
        except asyncio.CancelledError:
            logger.debug("Notification task cancelled")
        except (RuntimeError, OSError, ValueError, TypeError) as exc:
            logger.error("❌ 通知背景任務發生未預期錯誤: reason=%s", type(exc).__name__)
        except Exception as exc:
            logger.error(
                "❌ 通知背景任務發生未預期錯誤(未分類): reason=%s",
                type(exc).__name__,
            )

    task.add_done_callback(_on_done)
