# P2-F Offline-First (RFC-004): idempotency lookup and store for replay-safe writes.

import uuid
import logging
from typing import Any, Dict, Optional

from sqlmodel import select

from app.models.offline_operation_log import OfflineOperationLog
from app.services.api_idempotency_store import normalize_idempotency_key as _normalize_http_idempotency_key

logger = logging.getLogger(__name__)


def normalize_idempotency_key(
    idempotency_key: Optional[str] = None,
    x_request_id: Optional[str] = None,
) -> Optional[str]:
    """Prefer Idempotency-Key; fallback X-Request-Id. Returns None if neither valid."""
    raw = (idempotency_key or x_request_id or "").strip()
    return _normalize_http_idempotency_key(raw)


def get_replayed_response(
    session,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> Optional[Dict[str, Any]]:
    """If a previous request with this key was already processed, return stored response body."""
    row = session.exec(
        select(OfflineOperationLog).where(
            OfflineOperationLog.user_id == user_id,
            OfflineOperationLog.idempotency_key == idempotency_key,
        )
    ).first()
    if not row:
        return None
    return row.response_payload


def save_idempotency_response(
    session,
    user_id: uuid.UUID,
    idempotency_key: str,
    operation_type: str,
    resource_id: str,
    response_payload: Dict[str, Any],
) -> None:
    """Store successful response for future replay (same key returns this payload)."""
    session.add(
        OfflineOperationLog(
            user_id=user_id,
            idempotency_key=idempotency_key,
            operation_type=operation_type,
            resource_id=resource_id,
            response_payload=response_payload,
        )
    )
