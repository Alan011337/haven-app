"""
Cursor-based pagination utilities for efficient timeline queries.

This module provides utilities for implementing cursor-based pagination
to avoid N+1 queries and offset performance degradation.
"""

import base64
import hashlib
import hmac
import json
from binascii import Error as BinasciiError
from datetime import datetime
from typing import Optional, TypeVar, Generic
from uuid import UUID

from app.core.config import settings
from app.core.settings_domains import get_timeline_cursor_settings

T = TypeVar('T')


class InvalidPageCursorError(ValueError):
    """Raised when an opaque page cursor cannot be decoded safely."""


def _cursor_signing_key_bytes() -> bytes:
    timeline_settings = get_timeline_cursor_settings()
    key = (timeline_settings.signing_key or settings.SECRET_KEY or "").strip()
    if key:
        return key.encode("utf-8")
    if bool(timeline_settings.allow_default_signing_key):
        # Local-only escape hatch for development recovery; disabled by default.
        return b"haven-cursor-signing-key"
    raise InvalidPageCursorError(
        "Cursor signing key is missing; configure TIMELINE_CURSOR_SIGNING_KEY."
    )


def _cursor_requires_signature() -> bool:
    return bool(get_timeline_cursor_settings().require_signature)


def _build_cursor_signature(*, timestamp: str, item_id: str | None) -> str:
    payload = f"{timestamp}|{item_id or ''}".encode("utf-8")
    return hmac.new(_cursor_signing_key_bytes(), payload, hashlib.sha256).hexdigest()


def normalize_timeline_page_limit(
    limit: int | None,
    *,
    default_limit: int = 50,
    max_limit: int = 100,
) -> int:
    """Normalize requested timeline page size to a safe bounded value."""
    safe_max = max(1, int(max_limit))
    safe_default = min(max(1, int(default_limit)), safe_max)
    if limit is None:
        return safe_default
    try:
        requested = int(limit)
    except (TypeError, ValueError):
        return safe_default
    if requested <= 0:
        return safe_default
    return min(requested, safe_max)


def estimate_timeline_query_budget(
    *,
    fetch_limit: int,
    query_fanout: int = 2,
    detail_query_count: int = 2,
) -> int:
    """
    Estimate SQL work units for unified timeline.

    The timeline performs two primary list queries (journals + card sessions)
    plus batched detail queries (cards + responses). This gives us a stable
    upper-bound estimate used for local budget guardrails.
    """
    safe_fetch_limit = max(1, int(fetch_limit))
    safe_fanout = max(1, int(query_fanout))
    safe_detail = max(0, int(detail_query_count))
    return (safe_fetch_limit * safe_fanout) + safe_detail


def enforce_timeline_query_budget(
    *,
    fetch_limit: int,
    budget_units: int = 500,
    query_fanout: int = 2,
    detail_query_count: int = 2,
) -> int:
    """
    Clamp fetch limit to fit the configured query budget.

    Returns a safe fetch limit and never raises to avoid breaking runtime calls.
    """
    safe_fetch_limit = max(1, int(fetch_limit))
    safe_fanout = max(1, int(query_fanout))
    safe_detail = max(0, int(detail_query_count))
    safe_budget = max(safe_fanout + safe_detail, int(budget_units))
    max_fetch_by_budget = max(1, (safe_budget - safe_detail) // safe_fanout)
    return min(safe_fetch_limit, max_fetch_by_budget)


class PageCursor(Generic[T]):
    """Cursor-based pagination cursor for efficient timeline traversal."""
    
    def __init__(self, last_timestamp: Optional[datetime] = None, last_id: Optional[UUID] = None):
        """
        Initialize cursor.
        
        Args:
            last_timestamp: The timestamp of the last item on the previous page
            last_id: The ID of the last item on the previous page (for tiebreaking)
        """
        self.last_timestamp = last_timestamp
        self.last_id = last_id
    
    @classmethod
    def from_encoded(cls, encoded: Optional[str]) -> 'PageCursor':
        """Decode cursor from base64-encoded string."""
        if not encoded:
            return cls(None, None)
        
        try:
            decoded = base64.b64decode(encoded.encode()).decode()
            data = json.loads(decoded)
            if not isinstance(data, dict):
                raise InvalidPageCursorError("Cursor payload must be an object.")
            timestamp_raw = data.get("ts")
            last_id_raw = data.get("id")
            signature = data.get("sig")
            if timestamp_raw is not None and not isinstance(timestamp_raw, str):
                raise InvalidPageCursorError("Cursor timestamp field must be a string.")
            if last_id_raw is not None and not isinstance(last_id_raw, str):
                raise InvalidPageCursorError("Cursor id field must be a string.")
            if signature is not None and not isinstance(signature, str):
                raise InvalidPageCursorError("Cursor signature field must be a string.")
            if timestamp_raw and _cursor_requires_signature():
                if not signature:
                    raise InvalidPageCursorError("Cursor signature is required.")
                expected_signature = _build_cursor_signature(
                    timestamp=timestamp_raw,
                    item_id=last_id_raw,
                )
                if not hmac.compare_digest(signature, expected_signature):
                    raise InvalidPageCursorError("Invalid page cursor signature.")
            timestamp = datetime.fromisoformat(timestamp_raw) if timestamp_raw else None
            last_id = UUID(last_id_raw) if last_id_raw else None
            return cls(timestamp, last_id)
        except (ValueError, KeyError, json.JSONDecodeError, BinasciiError, UnicodeDecodeError) as exc:
            raise InvalidPageCursorError("Invalid page cursor.") from exc
    
    def encode(self) -> Optional[str]:
        """Encode cursor to base64-encoded string."""
        if self.last_timestamp is None:
            return None
        
        data = {
            'ts': self.last_timestamp.isoformat(),
            'id': str(self.last_id) if self.last_id else None,
        }
        if _cursor_requires_signature():
            data["sig"] = _build_cursor_signature(
                timestamp=self.last_timestamp.isoformat(),
                item_id=str(self.last_id) if self.last_id else None,
            )
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        return encoded


class PaginationResult:
    """Result of a paginated query."""
    
    def __init__(self, items: list, next_cursor: Optional[str] = None):
        self.items = items
        self.next_cursor = next_cursor  # None = no more pages
    
    @property
    def has_more(self) -> bool:
        """Whether there are more pages."""
        return self.next_cursor is not None
