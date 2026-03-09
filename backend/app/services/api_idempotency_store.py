from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, delete, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.api_idempotency_record import ApiIdempotencyRecord

logger = logging.getLogger(__name__)

MIN_KEY_LEN = 8
MAX_KEY_LEN = 200
_PURGE_LOCK = threading.Lock()
_NEXT_PURGE_AT_TS = 0.0


@dataclass(frozen=True)
class IdempotencyReplayDecision:
    status: str
    status_code: int | None = None
    payload: dict[str, Any] | None = None


def _setting_int(name: str, default: int) -> int:
    raw = getattr(settings, name, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _enabled() -> bool:
    return bool(getattr(settings, "API_IDEMPOTENCY_ENABLED", True))


def _ttl_seconds() -> int:
    return max(60, _setting_int("API_IDEMPOTENCY_TTL_SECONDS", 172800))


def _max_response_bytes() -> int:
    return max(1024, _setting_int("API_IDEMPOTENCY_MAX_RESPONSE_BYTES", 65536))


def _purge_interval_seconds() -> int:
    return max(30, _setting_int("API_IDEMPOTENCY_PURGE_INTERVAL_SECONDS", 300))


def _purge_batch_size() -> int:
    return max(10, _setting_int("API_IDEMPOTENCY_PURGE_BATCH_SIZE", 500))


def max_request_body_bytes() -> int:
    return max(1024, _setting_int("API_IDEMPOTENCY_MAX_REQUEST_BYTES", 131072))


def normalize_idempotency_key(raw_key: str | None) -> str | None:
    raw = (raw_key or "").strip()
    if not raw:
        return None
    if len(raw) < MIN_KEY_LEN or len(raw) > MAX_KEY_LEN:
        return None
    return raw


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_scope_fingerprint(*, request, normalized_path: str) -> str:
    auth_header = (request.headers.get("authorization") or "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    if token:
        token_hash = _hash_bytes(token.encode("utf-8"))[:24]
        return f"token:{token_hash}:{normalized_path[:64]}"

    client_id = (request.headers.get("x-client-id") or "").strip()
    device_id = (request.headers.get("x-device-id") or "").strip()
    if client_id or device_id:
        base = f"{client_id}|{device_id}|{normalized_path}".encode("utf-8")
        return f"anon:{_hash_bytes(base)[:24]}"
    return f"anon:{normalized_path[:64]}"


def _canonicalize_body(body_bytes: bytes) -> bytes:
    if not body_bytes:
        return b""
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return body_bytes
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_request_hash(
    *,
    method: str,
    normalized_path: str,
    query_string: str,
    body_bytes: bytes,
) -> str:
    canonical = (
        method.upper().encode("utf-8")
        + b"\n"
        + normalized_path.encode("utf-8")
        + b"\n"
        + (query_string or "").encode("utf-8")
        + b"\n"
        + _canonicalize_body(body_bytes or b"")
    )
    return _hash_bytes(canonical)


def purge_expired_records_if_due(*, session: Session) -> int:
    if not _enabled():
        return 0

    global _NEXT_PURGE_AT_TS
    now_ts = time.monotonic()
    if now_ts < _NEXT_PURGE_AT_TS:
        return 0

    with _PURGE_LOCK:
        if now_ts < _NEXT_PURGE_AT_TS:
            return 0
        cutoff = utcnow()
        stale_ids = list(
            session.exec(
                select(ApiIdempotencyRecord.id)
                .where(ApiIdempotencyRecord.expires_at < cutoff)
                .order_by(ApiIdempotencyRecord.expires_at.asc())
                .limit(_purge_batch_size())
            ).all()
        )
        purged = 0
        if stale_ids:
            result = session.exec(
                delete(ApiIdempotencyRecord).where(ApiIdempotencyRecord.id.in_(stale_ids))
            )
            purged = int(getattr(result, "rowcount", 0) or 0)
            session.commit()
        _NEXT_PURGE_AT_TS = now_ts + _purge_interval_seconds()
        return purged


def load_replay_decision(
    *,
    session: Session,
    scope_fingerprint: str,
    idempotency_key: str,
    request_hash: str,
) -> IdempotencyReplayDecision:
    if not _enabled():
        return IdempotencyReplayDecision(status="miss")

    purge_expired_records_if_due(session=session)
    row = session.exec(
        select(ApiIdempotencyRecord).where(
            ApiIdempotencyRecord.scope_fingerprint == scope_fingerprint,
            ApiIdempotencyRecord.idempotency_key == idempotency_key,
        )
    ).first()
    if row is None:
        return IdempotencyReplayDecision(status="miss")

    now = utcnow()
    if row.expires_at < now:
        try:
            session.delete(row)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
        return IdempotencyReplayDecision(status="miss")

    if not hmac.compare_digest(row.request_hash, request_hash):
        return IdempotencyReplayDecision(status="mismatch")

    if not row.response_payload_json:
        return IdempotencyReplayDecision(status="miss")

    try:
        payload = json.loads(row.response_payload_json)
    except json.JSONDecodeError:
        return IdempotencyReplayDecision(status="miss")
    return IdempotencyReplayDecision(
        status="replay",
        status_code=int(row.status_code or 200),
        payload=payload if isinstance(payload, dict) else {"data": payload},
    )


def save_idempotency_response(
    *,
    session: Session,
    scope_fingerprint: str,
    idempotency_key: str,
    request_hash: str,
    method: str,
    route_path: str,
    status_code: int,
    payload: dict[str, Any] | None,
) -> bool:
    if not _enabled():
        return False
    if status_code >= 500:
        return False
    if payload is None:
        return False

    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if len(encoded.encode("utf-8")) > _max_response_bytes():
        logger.warning(
            "Idempotency response skipped: payload_too_large status_code=%s route=%s",
            status_code,
            route_path,
        )
        return False

    now = utcnow()
    row = ApiIdempotencyRecord(
        scope_fingerprint=scope_fingerprint,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        method=method.upper()[:16],
        route_path=route_path[:255],
        status_code=int(status_code),
        response_payload_json=encoded,
        expires_at=now + timedelta(seconds=_ttl_seconds()),
        created_at=now,
        updated_at=now,
    )

    try:
        session.add(row)
        session.flush()
        return True
    except IntegrityError as exc:
        session.rollback()
        existing = session.exec(
            select(ApiIdempotencyRecord).where(
                ApiIdempotencyRecord.scope_fingerprint == scope_fingerprint,
                ApiIdempotencyRecord.idempotency_key == idempotency_key,
            )
        ).first()
        if existing is None:
            logger.warning(
                "Idempotency persistence integrity error without existing row: route=%s error_type=%s",
                route_path,
                type(exc).__name__,
            )
            return False
        if hmac.compare_digest(existing.request_hash, request_hash):
            return True
        logger.warning(
            "Idempotency persistence collision with mismatched payload: route=%s",
            route_path,
        )
        return False
    except SQLAlchemyError as exc:
        session.rollback()
        logger.warning(
            "Idempotency persistence SQLAlchemy error: route=%s error_type=%s",
            route_path,
            type(exc).__name__,
        )
        return False
