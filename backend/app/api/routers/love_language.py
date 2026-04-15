# Module B3: Love Languages preference and weekly task.

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.love_language import LoveLanguagePreference
from app.schemas.love_language import (
    LoveLanguagePreferenceCreate,
    LoveLanguagePreferencePublic,
    WeeklyTaskPublic,
)
from app.services.love_language_runtime import (
    normalize_love_language_preference,
    resolve_pair_weekly_task,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["love-languages"])


@router.get("/preference", response_model=LoveLanguagePreferencePublic | None)
def get_preference(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> LoveLanguagePreferencePublic | None:
    row = session.get(LoveLanguagePreference, current_user.id)
    if not row:
        return None
    normalized = normalize_love_language_preference(row.preference)
    return LoveLanguagePreferencePublic(
        preference={key: value for key, value in normalized.items() if value is not None},
        updated_at=row.updated_at,
    )


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
    task = resolve_pair_weekly_task(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
        ensure_assignment=True,
    )
    if task.created_assignment and task.assignment is not None:
        commit_with_error_handling(
            session,
            logger=logger,
            action="Create weekly task assignment",
            conflict_detail="建立時發生衝突。",
            failure_detail="建立失敗。",
        )
        session.refresh(task.assignment)
        task = resolve_pair_weekly_task(
            session=session,
            user_id=current_user.id,
            partner_id=partner_id,
            ensure_assignment=False,
        )

    return WeeklyTaskPublic(
        task_slug=task.task_slug,
        task_label=task.task_label,
        assigned_at=task.assigned_at,
        completed=task.completed,
        completed_at=task.completed_at,
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
    task = resolve_pair_weekly_task(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
        ensure_assignment=True,
    )
    row = task.assignment
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="本週任務尚未初始化")

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
        task_label=task.task_label,
        assigned_at=row.assigned_at,
        completed=True,
        completed_at=row.completed_at,
    )
