# P2-I [ADMIN-02]: Content report and moderation schemas

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class ReportSubmitRequest(SQLModel):
    resource_type: str  # whisper_wall | deck_marketplace | journal | card
    resource_id: str
    reason: Optional[str] = None


class ReportSubmitResponse(SQLModel):
    id: uuid.UUID
    status: str = "pending"


class ModerationReportPublic(SQLModel):
    id: uuid.UUID
    created_at: datetime
    resource_type: str
    resource_id: str
    reporter_user_id: uuid.UUID
    reason: Optional[str]
    status: str
    reviewed_at: Optional[datetime]
    reviewer_admin_id: Optional[uuid.UUID]
    resolution_note: Optional[str]


class ModerationResolveRequest(SQLModel):
    status: str  # approved | dismissed | hidden
    resolution_note: Optional[str] = None


class ModerationResolveResponse(SQLModel):
    id: uuid.UUID
    status: str
