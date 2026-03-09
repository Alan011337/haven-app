# Module B3: Love Languages schemas.

from datetime import datetime
from typing import Any, Optional

from sqlmodel import SQLModel

LOVE_LANGUAGE_TYPES = ("words", "acts", "gifts", "time", "touch")

# Static task list (slug -> label); weekly rotation can pick by week number.
LOVE_LANGUAGE_TASKS = [
    ("task_drink", "今天下班順手帶一杯他/她最愛的飲料"),
    ("task_hug", "給他/她一個 20 秒的擁抱"),
    ("task_note", "寫一張小紙條謝謝他/她"),
    ("task_walk", "一起散步 10 分鐘"),
    ("task_compliment", "說一句具體的讚美"),
]


class LoveLanguagePreferenceCreate(SQLModel):
    preference: dict[str, Any]  # e.g. {"primary": "words", "secondary": "time"}
    model_config = {"extra": "forbid"}


class LoveLanguagePreferencePublic(SQLModel):
    preference: dict[str, Any]
    updated_at: datetime


class WeeklyTaskPublic(SQLModel):
    task_slug: str
    task_label: str
    assigned_at: datetime
    completed: bool
    completed_at: Optional[datetime] = None
