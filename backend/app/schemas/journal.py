# backend/app/schemas/journal.py

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
# from app.schemas.ai import CardRecommendation # 如果這行報錯，可以先註解掉，用 str 代替

# 1. 前端傳進來的資料 (Create)
class JournalCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    model_config = {"extra": "forbid"}

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        return cleaned

# 2. 後端回傳給前端的資料 (Read)
class JournalRead(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    user_id: UUID
    mood_label: str | None = None
    emotional_needs: str | None = None
    advice_for_user: str | None = None
    action_for_user: str | None = None
    action_for_partner: str | None = None
    advice_for_partner: str | None = None
    card_recommendation: str | None = None
    safety_tier: int | None = None

# 3. 傳給伴侶看的資料
class JournalPartnerRead(BaseModel):
    id: UUID
    created_at: datetime
    user_id: UUID
    mood_label: str | None = None
    emotional_needs: str | None = None
    action_for_partner: str | None = None
    advice_for_partner: str | None = None
    card_recommendation: str | None = None
    safety_tier: int | None = None
