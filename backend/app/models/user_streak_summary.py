# DATA-READ-01: Precomputed read model for gamification streak summary.
# One row per user; refreshed on read when stale or on journal create (optional).
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class UserStreakSummary(SQLModel, table=True):
    __tablename__ = "user_streak_summary"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    partner_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    has_partner_context: bool = Field(default=False)
    streak_days: int = Field(default=0)
    best_streak_days: int = Field(default=0)
    streak_eligible_today: bool = Field(default=False)
    level: int = Field(default=1)
    level_points_total: int = Field(default=0)
    level_points_current: int = Field(default=0)
    level_points_target: int = Field(default=100)
    love_bar_percent: float = Field(default=0.0)
    level_title: str = Field(max_length=64, default="Warm Starter")
    anti_cheat_enabled: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=utcnow)
