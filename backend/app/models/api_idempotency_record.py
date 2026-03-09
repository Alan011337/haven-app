from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class ApiIdempotencyRecord(SQLModel, table=True):
    __tablename__ = "api_idempotency_records"
    __table_args__ = (
        Index(
            "uq_api_idempotency_scope_key",
            "scope_fingerprint",
            "idempotency_key",
            unique=True,
        ),
        Index("ix_api_idempotency_expires_at", "expires_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    expires_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    scope_fingerprint: str = Field(nullable=False, max_length=128)
    idempotency_key: str = Field(nullable=False, max_length=200)
    request_hash: str = Field(nullable=False, max_length=64)
    method: str = Field(nullable=False, max_length=16, index=True)
    route_path: str = Field(nullable=False, max_length=255, index=True)
    status_code: int = Field(default=0, nullable=False)
    response_payload_json: str | None = Field(default=None, nullable=True, max_length=65535)
