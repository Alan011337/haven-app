# Module A2: Relationship baseline and couple goal schemas.

from datetime import datetime
from typing import Any, Optional

from sqlmodel import SQLModel


# --- Relationship baseline ---
BASELINE_DIMENSIONS = ("intimacy", "conflict", "trust", "communication", "commitment")


class RelationshipBaselineCreate(SQLModel):
    scores: dict[str, Any]  # e.g. {"intimacy": 4, "conflict": 2, ...}
    model_config = {"extra": "forbid"}


class RelationshipBaselinePublic(SQLModel):
    user_id: str
    partner_id: Optional[str] = None
    filled_at: datetime
    scores: dict[str, Any]


class BaselineSummaryPublic(SQLModel):
    """Own baseline and optional partner summary (if both filled)."""
    mine: Optional[RelationshipBaselinePublic] = None
    partner: Optional[RelationshipBaselinePublic] = None


# --- Couple goal ---
COUPLE_GOAL_SLUGS = ("reduce_argument", "increase_intimacy", "better_communication", "more_trust", "other")


class CoupleGoalCreate(SQLModel):
    goal_slug: str  # one of COUPLE_GOAL_SLUGS
    model_config = {"extra": "forbid"}


class CoupleGoalPublic(SQLModel):
    goal_slug: str
    chosen_at: datetime
