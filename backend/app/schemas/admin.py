from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class AdminUserStatusPublic(SQLModel):
    id: uuid.UUID
    email: str
    is_active: bool
    deleted_at: Optional[datetime]
    partner_id: Optional[uuid.UUID]
    journals_count: int
    card_responses_count: int
    notifications_count: int
    audit_events_count: int


class AdminAuditEventPublic(SQLModel):
    id: uuid.UUID
    created_at: datetime
    actor_user_id: Optional[uuid.UUID]
    target_user_id: Optional[uuid.UUID]
    action: str
    resource_type: str
    resource_id: Optional[uuid.UUID]
    outcome: str
    reason: Optional[str]


class AdminUnbindResult(SQLModel):
    user_id: uuid.UUID
    previous_partner_id: Optional[uuid.UUID]
    unbound_bidirectional: bool
