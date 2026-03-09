# P2-F Offline-First (RFC-004): idempotency for replay-safe write endpoints.
# One row per (user_id, idempotency_key); response_payload is the stored 200 body for replay.

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Index, Column, JSON
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class OfflineOperationLog(SQLModel, table=True):
    __tablename__ = "offline_operation_logs"
    __table_args__ = (
        Index(
            "uq_offline_operation_logs_user_key",
            "user_id",
            "idempotency_key",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    idempotency_key: str = Field(nullable=False, index=True, max_length=200)
    operation_type: str = Field(nullable=False, index=True, max_length=64)
    resource_id: str = Field(nullable=False, max_length=64)
    response_payload: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
