# Module B3: Love Languages preference and weekly task.

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.love_language import LoveLanguagePreference, LoveLanguageTaskAssignment
from app.schemas.love_language import (
    LOVE_LANGUAGE_TASKS,
    LoveLanguagePreferenceCreate,
    LoveLanguagePreferencePublic,
    WeeklyTaskPublic,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["love-languages"])


def _canonical(u1: UUID, u2: UUID) -> tuple[UUID, UUID]:
    return (min(u1, u2), max(u1, u2))


def _week_number() -> int:
    return datetime.now(timezone.utc).isocalendar()[1]


@router.get("/preference", response_model=LoveLanguagePreferencePublic | None)
def get_preference(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> LoveLanguagePreferencePublic | None:
    row = session.get(LoveLanguagePreference, current_user.id)
    if not row:
        return None
    return LoveLanguagePreferencePublic(preference=row.preference, updated_at=row.updated_at)


@router.put("/preference", response_model=LoveLanguagePreferencePublic)
def upsert_preference(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: LoveLanguagePreferenceCreate,
) -> LoveLanguagePreferencePublic:
    from app.core.datetime_utils import utcnow
    row = session.get(LoveLanguagePreference, current_user.id)
    if row:
        row.preference = body.preference
        row.updated_at = utcnow()
        session.add(row)
    else:
        row = LoveLanguagePreference(user_id=current_user.id, preference=body.preference)
        session.add(row)
    commit_with_error_handling(
        session, logger=logger, action="Upsert love language preference",
        conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
    )
    session.refresh(row)
    return LoveLanguagePreferencePublic(preference=row.preference, updated_at=row.updated_at)


@router.get("/weekly-task", response_model=WeeklyTaskPublic | None)
def get_weekly_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> WeeklyTaskPublic | None:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return None
    uid1, uid2 = _canonical(current_user.id, partner_id)
    week = _week_number()
    task_idx = week % len(LOVE_LANGUAGE_TASKS)
    task_slug, task_label = LOVE_LANGUAGE_TASKS[task_idx]
    row = session.exec(
        select(LoveLanguageTaskAssignment).where(
            LoveLanguageTaskAssignment.user_id == uid1,
            LoveLanguageTaskAssignment.partner_id == uid2,
            LoveLanguageTaskAssignment.task_slug == task_slug,
        )
    ).first()
    if not row:
        row = LoveLanguageTaskAssignment(
            user_id=uid1,
            partner_id=uid2,
            task_slug=task_slug,
        )
        session.add(row)
        commit_with_error_handling(
            session, logger=logger, action="Create weekly task assignment",
            conflict_detail="建立時發生衝突。", failure_detail="建立失敗。",
        )
        session.refresh(row)
    completed = row.completed_at is not None
    return WeeklyTaskPublic(
        task_slug=row.task_slug,
        task_label=task_label,
        assigned_at=row.assigned_at,
        completed=completed,
        completed_at=row.completed_at,
    )


@router.post("/weekly-task/complete", response_model=WeeklyTaskPublic)
def complete_weekly_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> WeeklyTaskPublic:
    from app.core.datetime_utils import utcnow
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要先完成雙向綁定",
        )
    uid1, uid2 = _canonical(current_user.id, partner_id)
    week = _week_number()
    task_idx = week % len(LOVE_LANGUAGE_TASKS)
    task_slug, task_label = LOVE_LANGUAGE_TASKS[task_idx]
    row = session.exec(
        select(LoveLanguageTaskAssignment).where(
            LoveLanguageTaskAssignment.user_id == uid1,
            LoveLanguageTaskAssignment.partner_id == uid2,
            LoveLanguageTaskAssignment.task_slug == task_slug,
        )
    ).first()
    if not row:
        row = LoveLanguageTaskAssignment(user_id=uid1, partner_id=uid2, task_slug=task_slug)
        session.add(row)
        session.flush()
    row.completed_by_user_id = current_user.id
    row.completed_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session, logger=logger, action="Complete weekly task",
        conflict_detail="更新時發生衝突。", failure_detail="更新失敗。",
    )
    session.refresh(row)
    return WeeklyTaskPublic(
        task_slug=row.task_slug,
        task_label=task_label,
        assigned_at=row.assigned_at,
        completed=True,
        completed_at=row.completed_at,
    )
