from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class ConsentReceiptCreate(SQLModel):
    consent_type: str  # "terms_of_service", "privacy_policy", "ai_analysis"
    policy_version: str  # e.g. "1.0.0"
    model_config = {"extra": "forbid"}


class ConsentReceiptPublic(SQLModel):
    id: int
    consent_type: str
    policy_version: str
    granted_at: datetime
    revoked_at: Optional[datetime] = None
