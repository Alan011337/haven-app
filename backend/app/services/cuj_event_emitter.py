"""Server-side CUJ event emission utility.

Emits CUJ stage events directly from backend code paths for SLI metrics.
Used for events that originate server-side (analysis completion, persist, etc.)
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from sqlmodel import Session

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.cuj_event import CujEvent

logger = logging.getLogger(__name__)


def _build_dedupe_key(
    user_id: uuid.UUID,
    event_name: str,
    event_id: str,
) -> str:
    raw = f"{user_id}:{event_name}:{event_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def emit_cuj_event(
    *,
    session: Session,
    user_id: uuid.UUID,
    event_name: str,
    event_id: str | None = None,
    source: str = "server",
    mode: str | None = None,
    session_id: uuid.UUID | None = None,
    partner_user_id: uuid.UUID | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit a CUJ event server-side. Best-effort — never raises."""
    try:
        safe_event_id = event_id or f"srv-{uuid.uuid4().hex[:16]}"
        dedupe_key = _build_dedupe_key(user_id, event_name, safe_event_id)
        now = utcnow()

        event = CujEvent(
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name=event_name,
            event_id=safe_event_id,
            source=source,
            mode=mode,
            session_id=session_id,
            request_id=(request_id.strip() or None) if request_id else None,
            dedupe_key=dedupe_key,
            occurred_at=now,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        )
        session.add(event)
        session.flush()
        logger.info(
            "cuj_event_emitted event_name=%s source=%s user_id=%s",
            event_name,
            source,
            user_id,
        )
    except Exception:
        logger.warning(
            "cuj_event_emit_failed event_name=%s user_id=%s",
            event_name,
            user_id,
            exc_info=settings.LOG_INCLUDE_STACKTRACE,
        )
        session.rollback()
