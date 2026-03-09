from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class AuthRefreshSession(SQLModel, table=True):
    __tablename__ = "auth_refresh_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    current_token_hash: str = Field(nullable=False, index=True, max_length=128)
    device_id: Optional[str] = Field(default=None, nullable=True, index=True, max_length=128)
    client_ip_hash: Optional[str] = Field(default=None, nullable=True, max_length=128)
    user_agent_hash: Optional[str] = Field(default=None, nullable=True, max_length=128)

    rotation_counter: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    last_rotated_at: datetime = Field(default_factory=utcnow, nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    revoked_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    replayed_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
