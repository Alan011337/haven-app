# P2-C Memory Lane: Archive, Calendar, Time Capsule, Report schemas.

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ----- Timeline (unified feed) -----
class TimelineAttachmentMeta(BaseModel):
    """Attachment metadata surfaced in timeline journal items."""
    id: str
    file_name: str
    caption: Optional[str] = None
    mime_type: str
    url: Optional[str] = None  # signed URL; None if storage not configured


class TimelineJournalItem(BaseModel):
    type: Literal["journal"] = "journal"
    id: str
    created_at: datetime
    user_id: str
    mood_label: Optional[str] = None
    content_preview: Optional[str] = None  # truncated or redacted for partner
    is_own: bool = True
    attachment_count: int = 0
    attachments: list[TimelineAttachmentMeta] = Field(default_factory=list)


class TimelineCardItem(BaseModel):
    type: Literal["card"] = "card"
    session_id: str
    revealed_at: datetime
    card_title: str
    card_question: str
    category: str
    my_answer: Optional[str] = None
    partner_answer: Optional[str] = None
    is_own: bool = True


class TimelineAppreciationItem(BaseModel):
    type: Literal["appreciation"] = "appreciation"
    id: str  # string-cast integer PK
    created_at: datetime
    user_id: str  # who wrote it (sender)
    partner_id: str  # who received it (recipient)
    body_text: str
    is_mine: bool = True


class TimelinePhotoItem(BaseModel):
    """Placeholder for future photo integration."""
    type: Literal["photo"] = "photo"
    id: str
    created_at: datetime
    user_id: str
    caption: Optional[str] = None
    is_own: bool = True


TimelineItem = TimelineJournalItem | TimelineCardItem | TimelineAppreciationItem | TimelinePhotoItem


class TimelineResponse(BaseModel):
    # concrete union ensures each element validates against one of the
    # known item schemas instead of an untyped dict.
    items: list[TimelineItem]
    has_more: bool = False
    next_cursor: Optional[str] = None


# ----- Calendar (month view) -----
class CalendarDay(BaseModel):
    date: date
    mood_color: Optional[str] = None  # tailwind gradient key or hex
    journal_count: int = 0
    card_count: int = 0
    appreciation_count: int = 0
    has_photo: bool = False


class CalendarResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDay]


# ----- Time Capsule -----
class TimeCapsuleItem(BaseModel):
    type: str  # "journal" | "card" | "appreciation"
    preview_text: str
    created_at: Optional[datetime] = None


class TimeCapsuleMemory(BaseModel):
    date: date        # anchor date (exact anniversary, e.g. today - 365)
    from_date: date   # actual query window start (may equal date or be earlier)
    to_date: date     # actual query window end (may equal date or be later)
    journals_count: int = 0
    cards_count: int = 0
    appreciations_count: int = 0
    summary_text: Optional[str] = None
    items: list[TimeCapsuleItem] = Field(default_factory=list)


class TimeCapsuleResponse(BaseModel):
    available: bool = False
    memory: Optional[TimeCapsuleMemory] = None


# ----- AI Report -----
class RelationshipReportResponse(BaseModel):
    period: Literal["week", "month"]
    from_date: date
    to_date: date
    emotion_trend_summary: Optional[str] = None
    top_topics: list[str] = Field(default_factory=list)
    health_suggestion: Optional[str] = None
    generated_at: datetime
