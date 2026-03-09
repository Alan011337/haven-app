# Module B1: Daily sync schemas.

from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel


class DailySyncCreate(SQLModel):
    mood_score: int  # 1-5
    question_id: str
    answer_text: str
    model_config = {"extra": "forbid"}


class DailySyncStatusPublic(SQLModel):
    """Today's status: have I filled? has partner filled? If both, include both mood + answers."""
    today: date
    my_filled: bool
    partner_filled: bool
    unlocked: bool  # both filled -> can show partner's
    my_mood_score: Optional[int] = None
    my_question_id: Optional[str] = None
    my_answer_text: Optional[str] = None
    partner_mood_score: Optional[int] = None
    partner_question_id: Optional[str] = None
    partner_answer_text: Optional[str] = None
    today_question_id: Optional[str] = None
    today_question_label: Optional[str] = None


class DailySyncPublic(SQLModel):
    mood_score: int
    question_id: str
    answer_text: str
    created_at: datetime
