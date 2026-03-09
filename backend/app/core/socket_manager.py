# backend/app/core/socket_manager.py
# P2 Phase 1: WebSocket horizontal scaling via Redis Pub/Sub when REDIS_URL is set.

from typing import Dict, Any
import asyncio
import hashlib
import json
import logging
import time
from fastapi import WebSocket

from app.core.config import settings
from app.core.structured_logger import should_sample_event
from app.core.settings_domains import get_ws_settings
from app.services.ws_runtime_metrics import (
    record_partner_event_delivered,
    record_partner_event_delivery_latency_ms,
    record_partner_event_failed,
    record_partner_event_publish_attempted,
    record_partner_event_publish_failed,
    record_partner_event_publish_succeeded,
    record_partner_event_queued,
)

logger = logging.getLogger(__name__)

WS_REDIS_CHANNEL = "haven:ws:send"


class ConnectionManager:
    """In-memory WebSocket manager (single instance)."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self._send_locks: Dict[str, asyncio.Lock] = {}
        self._pending_senders: Dict[str, int] = {}
        self._outbound_sequence: Dict[str, int] = {}
        self._send_timeout_seconds = 2.0
        self._send_lock_wait_seconds = 0.1
        self._max_pending_sends_per_user = 8
        self._refresh_send_limits()

    def _refresh_send_limits(self) -> None:
        ws_settings = get_ws_settings()
        self._send_timeout_seconds = ws_settings.send_timeout_seconds
        self._send_lock_wait_seconds = ws_settings.send_lock_wait_seconds
        self._max_pending_sends_per_user = ws_settings.max_pending_sends_per_user

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        self._refresh_send_limits()
        uid = str(user_id)
        self.active_connections[uid] = websocket
        self._send_locks.setdefault(uid, asyncio.Lock())
        self._pending_senders.setdefault(uid, 0)
        self._outbound_sequence.setdefault(uid, 0)

    def disconnect(self, user_id: str) -> None:
        uid = str(user_id)
        if uid in self.active_connections:
            del self.active_connections[uid]
        self._send_locks.pop(uid, None)
        self._pending_senders.pop(uid, None)
        self._outbound_sequence.pop(uid, None)

    def _next_message_sequence(self, user_id: str) -> int:
        current = int(self._outbound_sequence.get(user_id, 0) or 0)
        if current >= 2_147_483_647:
            current = 0
        current += 1
        self._outbound_sequence[user_id] = current
        return current

    def _attach_message_sequence(self, user_id: str, message: dict) -> dict:
        payload = dict(message)
        if "_ws_seq" not in payload:
            payload["_ws_seq"] = self._next_message_sequence(user_id)
        return payload

    @staticmethod
    def _masked_user_id(user_id: str) -> str:
        return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:10]

    def _reserve_pending_sender_slot(self, user_id: str) -> bool:
        current = int(self._pending_senders.get(user_id, 0) or 0)
        if current >= self._max_pending_sends_per_user:
            return False
        self._pending_senders[user_id] = current + 1
        return True

    def _release_pending_sender_slot(self, user_id: str) -> None:
        current = int(self._pending_senders.get(user_id, 0) or 0)
        if current <= 1:
            self._pending_senders[user_id] = 0
            return
        self._pending_senders[user_id] = current - 1

    async def _send_json_with_backpressure(
        self,
        *,
        uid: str,
        websocket: WebSocket,
        message: dict,
    ) -> None:
        send_lock = self._send_locks.setdefault(uid, asyncio.Lock())
        acquired = False
        if send_lock.locked():
            if not self._reserve_pending_sender_slot(uid):
                raise TimeoutError("outbound_send_pending_limit_exceeded")
            try:
                await asyncio.wait_for(
                    send_lock.acquire(),
                    timeout=self._send_lock_wait_seconds,
                )
                acquired = True
            finally:
                self._release_pending_sender_slot(uid)
        else:
            await send_lock.acquire()
            acquired = True

        try:
            await asyncio.wait_for(
                websocket.send_json(message),
                timeout=self._send_timeout_seconds,
            )
        finally:
            if acquired and send_lock.locked():
                send_lock.release()

    def connection_count(self, user_id: str) -> int:
        return 1 if str(user_id) in self.active_connections else 0

    def total_connection_count(self) -> int:
        return len(self.active_connections)

    async def send_personal_message(self, message: dict, user_id: str) -> None:
        self._refresh_send_limits()
        uid = str(user_id)
        message_with_seq = self._attach_message_sequence(uid, message)
        record_partner_event_queued()
        record_partner_event_publish_attempted()
        started_at = time.monotonic()
        if uid in self.active_connections:
            record_partner_event_publish_succeeded()
            try:
                await self._send_json_with_backpressure(
                    uid=uid,
                    websocket=self.active_connections[uid],
                    message=message_with_seq,
                )
                record_partner_event_delivered()
                record_partner_event_delivery_latency_ms((time.monotonic() - started_at) * 1000.0)
            except Exception as e:
                record_partner_event_failed()
                if should_sample_event(
                    sample_key=f"ws-send-failed:{uid}:{type(e).__name__}",
                    sample_rate=getattr(settings, "LOG_SAMPLE_RATE_WS_SEND_FAILURE", 0.25),
                ):
                    logger.warning(
                        "WebSocket send failed for uid=%s: reason=%s",
                        self._masked_user_id(uid),
                        type(e).__name__,
                    )
                self.disconnect(uid)
        else:
            record_partner_event_publish_failed()
            record_partner_event_failed()


class RedisBackedConnectionManager(ConnectionManager):
    """WebSocket manager with Redis Pub/Sub for cross-instance delivery."""

    def __init__(self, redis_url: str) -> None:
        super().__init__()
        self._redis_url = redis_url
        self._redis: Any = None
        self._pubsub: Any = None
        self._subscriber_task: asyncio.Task[None] | None = None

    async def _ensure_redis(self) -> None:
        if self._redis is not None:
            return
        try:
            from redis.asyncio import Redis
            self._redis = Redis.from_url(
                self._redis_url,
                decode_responses=True,
            )
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(WS_REDIS_CHANNEL)
        except Exception as e:
            logger.warning("Redis WebSocket backend init failed: %s", type(e).__name__)
            raise

    async def _subscriber_loop(self) -> None:
        if self._pubsub is None:
            return
        try:
            while True:
                msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg is None:
                    continue
                if msg["type"] != "message":
                    continue
                try:
                    data = json.loads(msg["data"])
                    uid = data.get("user_id")
                    payload = data.get("message")
                    if not uid or not isinstance(payload, dict):
                        continue
                    if uid in self.active_connections:
                        try:
                            started_at = time.monotonic()
                            await self._send_json_with_backpressure(
                                uid=uid,
                                websocket=self.active_connections[uid],
                                message=payload,
                            )
                            record_partner_event_delivered()
                            record_partner_event_delivery_latency_ms(
                                (time.monotonic() - started_at) * 1000.0
                            )
                        except Exception as e:
                            logger.debug("Redis WS send_json failed for uid=%s: %s", uid, type(e).__name__)
                            record_partner_event_failed()
                            self.disconnect(uid)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug("Redis WS message parse error: %s", type(e).__name__)
        except asyncio.CancelledError:
            logger.info("WebSocket Redis subscriber loop cancelled")
        except Exception as e:
            logger.error("WebSocket Redis subscriber error: %s", type(e).__name__)

    async def start(self) -> None:
        await self._ensure_redis()
        if self._pubsub is not None:
            self._subscriber_task = asyncio.create_task(self._subscriber_loop())
            logger.info("WebSocket Redis subscriber started")

    async def stop(self) -> None:
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            self._subscriber_task = None
        if self._pubsub is not None:
            await self._pubsub.unsubscribe(WS_REDIS_CHANNEL)
            await self._pubsub.close()
            self._pubsub = None
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def send_personal_message(self, message: dict, user_id: str) -> None:
        uid = str(user_id)
        message_with_seq = self._attach_message_sequence(uid, message)
        record_partner_event_queued()
        record_partner_event_publish_attempted()
        # Fast-path: if receiver is connected on this node, deliver directly first.
        # This avoids unnecessary Redis roundtrip and reduces latency under load.
        if uid in self.active_connections:
            started_at = time.monotonic()
            try:
                await self._send_json_with_backpressure(
                    uid=uid,
                    websocket=self.active_connections[uid],
                    message=message_with_seq,
                )
                record_partner_event_publish_succeeded()
                record_partner_event_delivered()
                record_partner_event_delivery_latency_ms((time.monotonic() - started_at) * 1000.0)
                return
            except Exception as e:
                record_partner_event_publish_failed()
                record_partner_event_failed()
                if should_sample_event(
                    sample_key=f"ws-redis-local-fastpath-failed:{uid}:{type(e).__name__}",
                    sample_rate=getattr(settings, "LOG_SAMPLE_RATE_WS_SEND_FAILURE", 0.25),
                ):
                    logger.warning(
                        "WebSocket local fast-path failed for uid=%s: %s",
                        self._masked_user_id(uid),
                        type(e).__name__,
                    )
                self.disconnect(uid)

        try:
            await self._ensure_redis()
            payload = json.dumps({"user_id": uid, "message": message_with_seq})
            await self._redis.publish(WS_REDIS_CHANNEL, payload)
            record_partner_event_publish_succeeded()
            # Delivery is async: subscriber (this or other instance) will call record_partner_event_delivered when it sends
        except Exception as e:
            record_partner_event_publish_failed()
            record_partner_event_failed()
            if should_sample_event(
                sample_key=f"ws-redis-publish-failed:{uid}:{type(e).__name__}",
                sample_rate=getattr(settings, "LOG_SAMPLE_RATE_WS_SEND_FAILURE", 0.25),
            ):
                logger.warning(
                    "WebSocket Redis publish failed for uid=%s: %s",
                    self._masked_user_id(uid),
                    type(e).__name__,
                )


def create_socket_manager(redis_url: str | None) -> ConnectionManager | RedisBackedConnectionManager:
    """Create in-memory or Redis-backed manager. Caller must await .start() for Redis manager."""
    if redis_url and redis_url.strip():
        return RedisBackedConnectionManager(redis_url.strip())
    return ConnectionManager()


# Default: in-memory (for tests and when REDIS_URL not set). Replaced in lifespan when REDIS_URL set.
manager: ConnectionManager | RedisBackedConnectionManager = ConnectionManager()


async def init_socket_manager(redis_url: str | None) -> None:
    """Initialize global manager. Call from app lifespan; use REDIS_URL for horizontal scaling."""
    global manager
    m = create_socket_manager(redis_url)
    if isinstance(m, RedisBackedConnectionManager):
        await m.start()
    manager = m


async def shutdown_socket_manager() -> None:
    """Stop Redis subscriber and close connections. Call from app lifespan shutdown."""
    global manager
    if isinstance(manager, RedisBackedConnectionManager):
        await manager.stop()
