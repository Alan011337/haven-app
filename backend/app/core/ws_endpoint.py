from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.settings_domains import get_ws_settings
from app.core.socket_manager import manager
from app.core.ws_handler_helpers import resolve_ws_auth_token, resolve_ws_client_ip
from app.db.session import engine as default_engine
from app.models.user import User
from app.services.posthog_events import capture_posthog_event
from app.services.rate_limit import check_ws_connection_rate_limit
from app.services.rate_limit_scope import build_ws_message_scope_key
from app.services.socket_event_guard import resolve_typing_session_id
from app.services.ws_typing_session_cache import ws_typing_session_cache
from app.services.ws_abuse_guard import WsAbuseGuard
from app.services.ws_runtime_metrics import ws_runtime_metrics as default_ws_runtime_metrics


async def run_ws_endpoint(
    *,
    websocket: WebSocket,
    user_id: str,
    ws_abuse_guard: WsAbuseGuard,
    ws_runtime_metrics=default_ws_runtime_metrics,
    engine=default_engine,
    settings,
    logger: logging.Logger,
) -> None:
    ws_settings = get_ws_settings()
    if not bool(settings.WEBSOCKET_ENABLED):
        ws_runtime_metrics.increment("connections_rejected_feature_disabled")
        await websocket.close(code=1013)
        logger.info("WebSocket rejected: feature_disabled")
        return

    ws_abuse_guard.apply_runtime_limits(
        limit_count=ws_settings.message_rate_limit_count,
        window_seconds=ws_settings.message_rate_limit_window_seconds,
        backoff_seconds=ws_settings.message_backoff_seconds,
        max_payload_bytes=ws_settings.max_payload_bytes,
    )

    try:
        socket_user_id = uuid.UUID(user_id)
    except ValueError:
        ws_runtime_metrics.increment("connections_rejected_invalid_user_id")
        await websocket.close(code=1008)
        logger.warning("WebSocket rejected: invalid_user_id")
        return

    await websocket.accept()

    try:
        auth_token = await resolve_ws_auth_token(websocket)
    except asyncio.TimeoutError:
        ws_runtime_metrics.increment("connections_rejected_auth_timeout")
        await websocket.close(code=1008)
        logger.warning("WebSocket rejected: auth_timeout")
        return
    except WebSocketDisconnect:
        ws_runtime_metrics.increment("connections_rejected_auth_timeout")
        logger.warning("WebSocket rejected: auth_timeout (client closed)")
        return

    if not auth_token:
        ws_runtime_metrics.increment("connections_rejected_missing_token")
        await websocket.close(code=1008)
        logger.warning("WebSocket rejected: missing_token")
        return

    try:
        # Lazily import jose to avoid blocking app load on some macOS envs
        from jose import JWTError, jwt

        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject = payload.get("sub")
        token_user_id = uuid.UUID(str(subject))
        if token_user_id != socket_user_id:
            await websocket.close(code=1008)
            logger.warning("WebSocket rejected: token_subject_mismatch")
            return
    except (ValueError, TypeError):
        ws_runtime_metrics.increment("connections_rejected_invalid_token")
        await websocket.close(code=1008)
        logger.warning("WebSocket rejected: invalid_token")
        return
    except JWTError:
        ws_runtime_metrics.increment("connections_rejected_invalid_token")
        await websocket.close(code=1008)
        logger.warning("WebSocket rejected: invalid_token")
        return

    client_ip = resolve_ws_client_ip(websocket)
    ws_connection_scope = f"{socket_user_id}:{client_ip or 'unknown'}"
    ws_connection_allowed, ws_retry_after = check_ws_connection_rate_limit(
        scope_key=ws_connection_scope,
        limit_count=ws_settings.connection_rate_limit_count,
        window_seconds=ws_settings.connection_rate_limit_window_seconds,
    )
    if not ws_connection_allowed:
        ws_runtime_metrics.increment("connections_rejected_rate_limited")
        logger.warning(
            "WebSocket rejected: reason=connection_rate_limited retry_after=%ss",
            ws_retry_after,
        )
        try:
            await websocket.send_json(
                {
                    "event": "WS_CONNECTION_RATE_LIMITED",
                    "retry_after_seconds": ws_retry_after,
                }
            )
        except Exception:
            logger.debug("Failed to deliver WS_CONNECTION_RATE_LIMITED event")
        await websocket.close(code=1013)
        return

    def _lookup_ws_user():
        with Session(engine) as session:
            user = session.get(User, socket_user_id)
            return (user.partner_id if user else None, user is not None, bool(user and user.is_active))

    partner_user_id, user_found, user_active = await asyncio.get_event_loop().run_in_executor(
        None, _lookup_ws_user
    )
    if not user_found or not user_active:
        ws_runtime_metrics.increment("connections_rejected_user_not_found")
        await websocket.close(code=1008)
        logger.warning("WebSocket rejected: user_not_found")
        return

    active_user_connections = manager.connection_count(user_id)
    active_total_connections = manager.total_connection_count()
    allow_connection, reject_reason = ws_abuse_guard.allow_new_connection(
        user_id=user_id,
        active_user_connections=active_user_connections,
        active_total_connections=active_total_connections,
        max_connections_per_user=ws_settings.max_connections_per_user,
        max_connections_global=ws_settings.max_connections_global,
    )
    if not allow_connection:
        if reject_reason == "global_connection_cap":
            ws_runtime_metrics.increment("connections_rejected_global_cap")
        else:
            ws_runtime_metrics.increment("connections_rejected_per_user_cap")
        close_code = 1013 if reject_reason == "global_connection_cap" else 1008
        await websocket.close(code=close_code)
        logger.warning(
            "WebSocket rejected: reason=%s user_connections=%s total_connections=%s",
            reject_reason,
            active_user_connections,
            active_total_connections,
        )
        return

    device_header_name = (settings.RATE_LIMIT_DEVICE_HEADER or "x-device-id").strip().lower()
    device_id = (websocket.headers.get(device_header_name) or "").strip()[:128]
    message_scope_key = build_ws_message_scope_key(
        user_id=socket_user_id,
        partner_id=partner_user_id,
        client_ip=client_ip,
        device_id=device_id,
        include_ip=ws_settings.scope_include_ip,
        include_device=ws_settings.scope_include_device,
        include_partner_pair=ws_settings.scope_include_partner_pair,
    )

    await manager.connect(user_id, websocket)
    ws_runtime_metrics.increment("connections_accepted")
    capture_posthog_event(
        event_name="ws_connected",
        distinct_id=str(socket_user_id),
        properties={"transport": "websocket"},
    )
    logger.info("WebSocket user connected")

    try:
        while True:
            data = await websocket.receive_text()
            ws_runtime_metrics.increment("messages_received")

            message_allowed, violation = ws_abuse_guard.evaluate_message(
                user_id=user_id,
                payload_text=data,
                scope_key=message_scope_key,
            )
            if not message_allowed:
                reason = str((violation or {}).get("reason", "message_blocked"))
                if reason == "message_rate_limited":
                    ws_runtime_metrics.increment("messages_rate_limited")
                elif reason == "payload_too_large":
                    ws_runtime_metrics.increment("messages_payload_too_large")
                elif reason == "backoff_active":
                    ws_runtime_metrics.increment("messages_backoff_active")
                else:
                    ws_runtime_metrics.increment("messages_blocked_other")
                retry_after = int((violation or {}).get("retry_after_seconds", settings.WS_MESSAGE_BACKOFF_SECONDS))
                logger.warning(
                    "WebSocket throttled for %s: reason=%s retry_after=%ss",
                    user_id,
                    reason,
                    retry_after,
                )
                try:
                    await websocket.send_json(
                        {
                            "event": "WS_RATE_LIMITED",
                            "reason": reason,
                            "retry_after_seconds": retry_after,
                        }
                    )
                except Exception:
                    logger.debug("Failed to deliver WS_RATE_LIMITED event")
                await websocket.close(code=1013)
                break

            if data == "ping":
                await websocket.send_text("pong")
                continue

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                logger.debug("WebSocket ignored non-JSON payload")
                continue

            if not isinstance(payload, dict):
                continue

            event_type = payload.get("event")
            if event_type == "TYPING" and partner_user_id:
                raw_session_id = payload.get("session_id")
                cache_key = ws_typing_session_cache.build_key(
                    sender_user_id=str(socket_user_id),
                    partner_user_id=str(partner_user_id),
                    raw_session_id=raw_session_id,
                )
                cached_session_id = ws_typing_session_cache.get(cache_key)
                if cached_session_id:
                    ws_runtime_metrics.increment("typing_session_cache_hit")
                    await manager.send_personal_message(
                        {
                            "event": "PARTNER_TYPING",
                            "from_user_id": str(socket_user_id),
                            "session_id": cached_session_id,
                            "is_typing": bool(payload.get("is_typing")),
                        },
                        str(partner_user_id),
                    )
                    ws_runtime_metrics.increment("typing_events_forwarded")
                    continue
                ws_runtime_metrics.increment("typing_session_cache_miss")

                def _resolve_typing_sid():
                    with Session(engine) as session:
                        return resolve_typing_session_id(
                            session=session,
                            sender_user_id=socket_user_id,
                            partner_user_id=partner_user_id,
                            raw_session_id=raw_session_id,
                        )

                session_id = await asyncio.get_event_loop().run_in_executor(None, _resolve_typing_sid)
                if not session_id:
                    continue
                ws_typing_session_cache.set(cache_key, session_id)

                await manager.send_personal_message(
                    {
                        "event": "PARTNER_TYPING",
                        "from_user_id": str(socket_user_id),
                        "session_id": session_id,
                        "is_typing": bool(payload.get("is_typing")),
                    },
                    str(partner_user_id),
                )
                ws_runtime_metrics.increment("typing_events_forwarded")

    except WebSocketDisconnect as exc:
        manager.disconnect(user_id)
        ws_runtime_metrics.increment("connections_disconnected")
        close_code = int(getattr(exc, "code", 1000) or 1000)
        close_code_bucket = str(close_code) if close_code in {1000, 1001, 1006, 1008, 1011, 1013} else "other"
        ws_runtime_metrics.increment(f"connections_disconnected_code_{close_code_bucket}")
        capture_posthog_event(
            event_name="ws_disconnected",
            distinct_id=str(socket_user_id),
            properties={
                "close_code": close_code_bucket,
                "reason_bucket": "server_disconnect",
            },
        )
        logger.info("WebSocket user disconnected")
    except Exception as exc:
        logger.error("WebSocket error: reason=%s", type(exc).__name__)
        manager.disconnect(user_id)
        ws_runtime_metrics.increment("connections_error")
        try:
            await websocket.close(code=1011)
        except Exception:
            logger.debug("Failed to close websocket after error")
