"""Schema contract for POST /api/users/events/core-loop ingest endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.growth import CoreLoopEventName, CoreLoopEventTrackRequest  # noqa: E402


def test_core_loop_ingest_request_schema_has_required_fields() -> None:
    assert hasattr(CoreLoopEventTrackRequest, "model_fields")
    fields = CoreLoopEventTrackRequest.model_fields
    assert "event_name" in fields
    assert "event_id" in fields
    assert "source" in fields
    assert "props" in fields
    assert "context" in fields
    assert "privacy" in fields


def test_core_loop_event_name_enum_includes_prd_v0_minimum_set() -> None:
    allowed = {event.value for event in CoreLoopEventName}
    assert "daily_sync_submitted" in allowed
    assert "daily_card_revealed" in allowed
    assert "card_answer_submitted" in allowed
    assert "appreciation_sent" in allowed
    assert "daily_loop_completed" in allowed
