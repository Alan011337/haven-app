# Module A1: Onboarding consent (privacy scope, notification frequency, AI intensity).

import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class UserOnboardingConsent(SQLModel, table=True):
    __tablename__ = "user_onboarding_consent"

    user_id: uuid.UUID = Field(primary_key=True, foreign_key="users.id")
    privacy_scope_accepted: bool = Field(default=False)
    notification_frequency: str = Field(max_length=32, default="normal")  # off | low | normal | high
    ai_intensity: str = Field(max_length=32, default="gentle")  # gentle | direct
    updated_at: datetime = Field(default_factory=utcnow)
