from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class EntitlementUsageDaily(SQLModel, table=True):
    __tablename__ = "entitlement_usage_daily"
    __table_args__ = (
        Index(
            "uq_entitlement_usage_daily_user_feature_date",
            "user_id",
            "feature_key",
            "usage_date",
            unique=True,
        ),
        Index("ix_entitlement_usage_daily_user_date", "user_id", "usage_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    feature_key: str = Field(nullable=False, max_length=128, index=True)
    usage_date: date = Field(nullable=False, index=True)
    used_count: int = Field(default=0, nullable=False)
