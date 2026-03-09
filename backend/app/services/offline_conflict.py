# P2-F P1: Conflict policy — time source + LWW (last-write-wins).
# Time source: X-Client-Timestamp (ms since epoch). Server uses it to compare with resource.updated_at.

import logging
from datetime import datetime, timezone
from typing import Optional


logger = logging.getLogger(__name__)

HEADER_CLIENT_TS = "X-Client-Timestamp"


def parse_client_timestamp(header_value: Optional[str]) -> Optional[int]:
    """Parse X-Client-Timestamp (ms since epoch). Returns None if invalid."""
    if not header_value or not header_value.strip():
        return None
    try:
        ms = int(header_value.strip())
        if ms <= 0 or ms > 4102444800000:  # year 2100
            return None
        return ms
    except ValueError:
        return None


def server_ts_ms(dt: Optional[datetime]) -> int:
    """Convert server datetime to ms since epoch (UTC)."""
    if dt is None:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def lww_newer_is_client(
    client_ts_ms: int,
    server_updated_at: Optional[datetime],
) -> bool:
    """True if client write is newer (should overwrite); False if server wins (should 409)."""
    server_ms = server_ts_ms(server_updated_at)
    return client_ts_ms > server_ms


def same_utc_calendar_day(dt: datetime, reference_ms: int) -> bool:
    """True if dt's UTC date equals the date of reference_ms (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ref_date = datetime.fromtimestamp(reference_ms / 1000.0, tz=timezone.utc).date()
    return dt.date() == ref_date
