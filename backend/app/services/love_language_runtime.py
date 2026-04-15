from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.models.love_language import LoveLanguagePreference, LoveLanguageTaskAssignment
from app.schemas.love_language import LOVE_LANGUAGE_TASKS, LOVE_LANGUAGE_TYPES


@dataclass(frozen=True)
class LoveLanguagePreferenceSummary:
    primary: str | None
    secondary: str | None
    updated_at: datetime | None


@dataclass(frozen=True)
class WeeklyTaskResolution:
    task_slug: str
    task_label: str
    assigned_at: datetime | None
    completed: bool
    completed_at: datetime | None
    assignment: LoveLanguageTaskAssignment | None
    created_assignment: bool


def canonical_pair_scope(user_id: UUID, partner_id: UUID) -> tuple[UUID, UUID]:
    return min(user_id, partner_id), max(user_id, partner_id)


def current_love_language_week_number() -> int:
    return datetime.now(timezone.utc).isocalendar()[1]


def resolve_current_love_language_task_definition() -> tuple[str, str]:
    task_index = current_love_language_week_number() % len(LOVE_LANGUAGE_TASKS)
    return LOVE_LANGUAGE_TASKS[task_index]


def normalize_love_language_preference(value: object) -> dict[str, str | None]:
    allowed = set(LOVE_LANGUAGE_TYPES)
    if not isinstance(value, dict):
        return {"primary": None, "secondary": None}

    primary_value = value.get("primary")
    secondary_value = value.get("secondary")

    primary = primary_value if isinstance(primary_value, str) and primary_value in allowed else None
    secondary = secondary_value if isinstance(secondary_value, str) and secondary_value in allowed else None
    if secondary == primary:
        secondary = None

    return {
        "primary": primary,
        "secondary": secondary,
    }


def load_love_language_preference_summary(
    *,
    session: Session,
    user_id: UUID,
) -> LoveLanguagePreferenceSummary | None:
    row = session.get(LoveLanguagePreference, user_id)
    if not row:
        return None

    normalized = normalize_love_language_preference(row.preference)
    return LoveLanguagePreferenceSummary(
        primary=normalized["primary"],
        secondary=normalized["secondary"],
        updated_at=row.updated_at,
    )


def resolve_pair_weekly_task(
    *,
    session: Session,
    user_id: UUID,
    partner_id: UUID,
    ensure_assignment: bool,
) -> WeeklyTaskResolution:
    uid1, uid2 = canonical_pair_scope(user_id, partner_id)
    task_slug, task_label = resolve_current_love_language_task_definition()
    row = session.exec(
        select(LoveLanguageTaskAssignment).where(
            LoveLanguageTaskAssignment.user_id == uid1,
            LoveLanguageTaskAssignment.partner_id == uid2,
            LoveLanguageTaskAssignment.task_slug == task_slug,
        )
    ).first()

    created_assignment = False
    if not row and ensure_assignment:
        row = LoveLanguageTaskAssignment(
            user_id=uid1,
            partner_id=uid2,
            task_slug=task_slug,
        )
        session.add(row)
        session.flush()
        created_assignment = True

    return WeeklyTaskResolution(
        task_slug=task_slug,
        task_label=task_label,
        assigned_at=row.assigned_at if row else None,
        completed=row.completed_at is not None if row else False,
        completed_at=row.completed_at if row else None,
        assignment=row,
        created_assignment=created_assignment,
    )
