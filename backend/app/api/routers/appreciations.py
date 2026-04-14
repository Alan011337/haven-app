# Module B2: Appreciation Bank API.

import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.appreciation import Appreciation
from app.schemas.appreciation import AppreciationCreate, AppreciationPublic

logger = logging.getLogger(__name__)
router = APIRouter(tags=["appreciations"])


@router.get("", response_model=list[AppreciationPublic])
def list_appreciations(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_date: Optional[str] = Query(None, description="ISO date"),
    to_date: Optional[str] = Query(None, description="ISO date"),
) -> list[AppreciationPublic]:
    """List appreciations I sent to my partner (or received from partner). Only self+partner can read."""
    verify_active_partner_id(session=session, current_user=current_user)
    # Show appreciations where I am sender (to partner) or recipient (from partner)
    stmt = select(Appreciation).where(
        (Appreciation.user_id == current_user.id) | (Appreciation.partner_id == current_user.id)
    )
    if from_date:
        try:
            d = date.fromisoformat(from_date[:10])
            stmt = stmt.where(Appreciation.created_at >= datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc))
        except ValueError:
            pass
    if to_date:
        try:
            d = date.fromisoformat(to_date[:10])
            end = datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc)
            stmt = stmt.where(Appreciation.created_at <= end)
        except ValueError:
            pass
    stmt = stmt.order_by(Appreciation.created_at.desc()).offset(offset).limit(limit)
    rows = list(session.exec(stmt).all())
    return [
        AppreciationPublic(
            id=r.id,
            body_text=r.body_text,
            created_at=r.created_at,
            is_mine=(r.user_id == current_user.id),
        )
        for r in rows
    ]


@router.get("/{appreciation_id}", response_model=AppreciationPublic)
def get_appreciation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    appreciation_id: int,
) -> AppreciationPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    row = session.exec(
        select(Appreciation).where(
            Appreciation.id == appreciation_id,
            (
                ((Appreciation.user_id == current_user.id) & (Appreciation.partner_id == partner_id))
                | ((Appreciation.user_id == partner_id) & (Appreciation.partner_id == current_user.id))
            ),
        )
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到這則感謝。")

    return AppreciationPublic(
        id=row.id,
        body_text=row.body_text,
        created_at=row.created_at,
        is_mine=(row.user_id == current_user.id),
    )


@router.post("", response_model=AppreciationPublic, status_code=status.HTTP_201_CREATED)
def create_appreciation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: AppreciationCreate,
) -> AppreciationPublic:
    """Send one gratitude note to partner."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    text = (body.body_text or "").strip()[:500]
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="body_text 不可為空")
    row = Appreciation(
        user_id=current_user.id,
        partner_id=partner_id,
        body_text=text,
    )
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Create appreciation",
        conflict_detail="儲存時發生衝突，請稍後再試。",
        failure_detail="儲存失敗，請稍後再試。",
    )
    session.refresh(row)
    return AppreciationPublic(
        id=row.id,
        body_text=row.body_text,
        created_at=row.created_at,
        is_mine=True,
    )
