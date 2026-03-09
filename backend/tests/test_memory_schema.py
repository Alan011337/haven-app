from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.memory import (
    TimelineResponse,
    TimelineJournalItem,
    TimelineCardItem,
    TimelineItem,
)


def test_timeline_response_accepts_valid_union():
    journal = TimelineJournalItem(
        id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        user_id=str(uuid4()),
        mood_label="happy",
        content_preview="hi",
        is_own=True,
    )
    card = TimelineCardItem(
        session_id=str(uuid4()),
        revealed_at=datetime.now(timezone.utc),
        card_title="Q?",
        card_question="What?",
        category="",
        is_own=False,
    )
    resp = TimelineResponse(items=[journal, card], has_more=False)
    assert isinstance(resp.items[0], TimelineItem)
    assert resp.items[0].type == "journal"
    assert resp.items[1].type == "card"


def test_timeline_response_rejects_bad_shape():
    # missing required field 'id' for journal
    bad = {"type": "journal", "created_at": datetime.now(timezone.utc), "user_id": "x"}
    with pytest.raises(Exception):
        TimelineResponse(items=[bad], has_more=False)
