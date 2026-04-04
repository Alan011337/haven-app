# backend/app/schemas/journal.py

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime

JOURNAL_CURRENT_WRITE_VISIBILITIES = frozenset(
    {
        "PRIVATE",
        "PARTNER_ORIGINAL",
        "PARTNER_TRANSLATED_ONLY",
    }
)
JOURNAL_READ_VISIBILITIES = frozenset(
    {
        "PRIVATE",
        "PRIVATE_LOCAL",
        "PARTNER_ORIGINAL",
        "PARTNER_TRANSLATED_ONLY",
        "PARTNER_ANALYSIS_ONLY",
    }
)
JOURNAL_CONTENT_FORMATS = frozenset({"markdown"})
JOURNAL_TRANSLATION_STATUSES = frozenset(
    {
        "FAILED",
        "NOT_REQUESTED",
        "PENDING",
        "READY",
    }
)


class JournalAttachmentPublic(BaseModel):
    id: UUID
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    caption: str | None = None
    url: str | None = None

# 1. 前端傳進來的資料 (Create)
class JournalCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    content: str = Field(default="", max_length=12000)
    is_draft: bool = False
    visibility: str = Field(default="PRIVATE")
    content_format: str = Field(default="markdown")
    model_config = {"extra": "forbid"}

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return value.strip()

    @field_validator("visibility")
    @classmethod
    def normalize_visibility(cls, value: str) -> str:
        cleaned = str(value or "").strip().upper()
        if cleaned not in JOURNAL_CURRENT_WRITE_VISIBILITIES:
            raise ValueError("invalid visibility")
        return cleaned

    @field_validator("content_format")
    @classmethod
    def normalize_content_format(cls, value: str) -> str:
        cleaned = str(value or "").strip().lower()
        if cleaned not in JOURNAL_CONTENT_FORMATS:
            raise ValueError("invalid content format")
        return cleaned


class JournalUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    content: str | None = Field(default=None, max_length=12000)
    is_draft: bool | None = None
    visibility: str | None = None
    request_analysis: bool = False
    model_config = {"extra": "forbid"}

    @field_validator("title")
    @classmethod
    def normalize_update_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("content")
    @classmethod
    def normalize_update_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("visibility")
    @classmethod
    def normalize_update_visibility(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value or "").strip().upper()
        if cleaned not in JOURNAL_CURRENT_WRITE_VISIBILITIES:
            raise ValueError("invalid visibility")
        return cleaned

# 2. 後端回傳給前端的資料 (Read)
class JournalRead(BaseModel):
    id: UUID
    title: str | None = None
    content: str
    is_draft: bool = False
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    visibility: str
    content_format: str = "markdown"
    partner_translation_status: str = "NOT_REQUESTED"
    partner_translation_ready_at: datetime | None = None
    attachments: list[JournalAttachmentPublic] = Field(default_factory=list)
    mood_label: str | None = None
    emotional_needs: str | None = None
    advice_for_user: str | None = None
    action_for_user: str | None = None
    action_for_partner: str | None = None
    advice_for_partner: str | None = None
    card_recommendation: str | None = None
    safety_tier: int | None = None

    @field_validator("visibility")
    @classmethod
    def validate_read_visibility(cls, value: str) -> str:
        cleaned = str(value or "").strip().upper()
        if cleaned not in JOURNAL_READ_VISIBILITIES:
            raise ValueError("invalid visibility")
        return cleaned

    @field_validator("content_format")
    @classmethod
    def validate_read_content_format(cls, value: str) -> str:
        cleaned = str(value or "").strip().lower()
        if cleaned not in JOURNAL_CONTENT_FORMATS:
            raise ValueError("invalid content format")
        return cleaned

    @field_validator("partner_translation_status")
    @classmethod
    def validate_translation_status(cls, value: str) -> str:
        cleaned = str(value or "").strip().upper()
        if cleaned not in JOURNAL_TRANSLATION_STATUSES:
            raise ValueError("invalid translation status")
        return cleaned


class JournalCreateResponse(JournalRead):
    new_savings_score: int
    score_gained: int

# 3. 傳給伴侶看的資料
class JournalPartnerRead(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    visibility: str
    content: str = ""
    partner_translation_status: str = "NOT_REQUESTED"
    partner_translated_content: str | None = None
    attachments: list[JournalAttachmentPublic] = Field(default_factory=list)
    mood_label: str | None = None
    emotional_needs: str | None = None
    action_for_partner: str | None = None
    advice_for_partner: str | None = None
    card_recommendation: str | None = None
    safety_tier: int | None = None
