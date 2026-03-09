# P2-I [ADMIN-02]: Content moderation — user reports and admin resolution

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class ContentReportResourceType(str, Enum):
    WHISPER_WALL = "whisper_wall"
    DECK_MARKETPLACE = "deck_marketplace"
    JOURNAL = "journal"
    CARD = "card"


class ContentReportStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"   # report upheld, content action taken
    DISMISSED = "dismissed" # report rejected
    HIDDEN = "hidden"      # content hidden without upholding report


class ContentReport(SQLModel, table=True):
    __tablename__ = "content_reports"
    __table_args__ = (
        Index("ix_content_reports_status_created_at", "status", "created_at"),
        Index("ix_content_reports_resource", "resource_type", "resource_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    resource_type: str = Field(nullable=False, max_length=64, index=True)
    resource_id: str = Field(nullable=False, max_length=128, index=True)
    reporter_user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    reason: Optional[str] = Field(default=None, max_length=500)

    status: str = Field(default=ContentReportStatus.PENDING.value, nullable=False, max_length=32, index=True)
    reviewed_at: Optional[datetime] = Field(default=None, nullable=True)
    reviewer_admin_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    resolution_note: Optional[str] = Field(default=None, max_length=500)
