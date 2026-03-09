"""CUJ-01: Schema contract for POST /api/users/events/cuj ingest endpoint."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.growth import CujEventTrackRequest, CujEventName  # noqa: E402


def test_cuj_ingest_request_schema_has_required_fields() -> None:
    """CUJ-01: Ingest endpoint request must have event_name, source, event_id."""
    # CujEventTrackRequest is the canonical schema for POST /api/users/events/cuj
    assert hasattr(CujEventTrackRequest, "model_fields")
    fields = CujEventTrackRequest.model_fields
    assert "event_name" in fields
    assert "event_id" in fields
    assert "source" in fields
    assert "session_id" in fields or "session_id" in getattr(
        CujEventTrackRequest, "__annotations__", {}
    )


def test_cuj_event_name_enum_includes_ritual_stages() -> None:
    """CUJ-01: Ritual stages (draw/respond/unlock) and bind/journal must be in enum."""
    allowed = {e.value for e in CujEventName}
    assert "RITUAL_DRAW" in allowed
    assert "RITUAL_RESPOND" in allowed
    assert "RITUAL_UNLOCK" in allowed
    assert "BIND_SUCCESS" in allowed
    assert "JOURNAL_SUBMIT" in allowed
