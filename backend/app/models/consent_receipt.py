import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class ConsentReceipt(SQLModel, table=True):
    __tablename__ = "consent_receipts"
    __table_args__ = (
        Index(
            "ix_consent_receipts_user_type",
            "user_id",
            "consent_type",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(index=True, foreign_key="users.id")
    consent_type: str = Field(index=True, max_length=64)  # "terms_of_service", "privacy_policy", "ai_analysis"
    policy_version: str = Field(max_length=32)  # e.g. "1.0.0"
    granted_at: datetime = Field(default_factory=utcnow)
    revoked_at: Optional[datetime] = Field(default=None, nullable=True)
    ip_address: Optional[str] = Field(default=None, nullable=True, max_length=45)
