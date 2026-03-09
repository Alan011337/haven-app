# Module A1: Onboarding consent schemas.

from datetime import datetime
from sqlmodel import SQLModel


class UserOnboardingConsentCreate(SQLModel):
    privacy_scope_accepted: bool = True
    notification_frequency: str = "normal"  # off | low | normal | high
    ai_intensity: str = "gentle"  # gentle | direct
    model_config = {"extra": "forbid"}


class UserOnboardingConsentPublic(SQLModel):
    privacy_scope_accepted: bool
    notification_frequency: str
    ai_intensity: str
    updated_at: datetime
