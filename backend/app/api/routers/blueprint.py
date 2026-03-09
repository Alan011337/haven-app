# Module D2: Blueprint / wishlist and date suggestions.

import logging

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.wishlist_item import WishlistItem
from app.schemas.blueprint import (
    DateSuggestionPublic,
    WishlistItemCreate,
    WishlistItemPublic,
)
from app.services.date_suggestions_runtime import get_date_suggestion

logger = logging.getLogger(__name__)
router = APIRouter(tags=["blueprint"])


@router.get("/", response_model=list[WishlistItemPublic])
def list_blueprint(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[WishlistItemPublic]:
    """List wishlist items for the couple (both directions)."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return []
    uid1, uid2 = min(current_user.id, partner_id), max(current_user.id, partner_id)
    rows = session.exec(
        select(WishlistItem).where(
            ((WishlistItem.user_id == uid1) & (WishlistItem.partner_id == uid2))
            | ((WishlistItem.user_id == uid2) & (WishlistItem.partner_id == uid1)),
        ).order_by(WishlistItem.created_at.desc())
    ).all()
    return [
        WishlistItemPublic(
            id=str(r.id),
            title=r.title,
            notes=r.notes,
            created_at=r.created_at.isoformat() + "Z",
            added_by_me=r.user_id == current_user.id,
        )
        for r in rows
    ]


@router.post("/", response_model=WishlistItemPublic)
def add_blueprint_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: WishlistItemCreate,
) -> WishlistItemPublic:
    """Add a wishlist item for the couple."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")
    row = WishlistItem(
        user_id=current_user.id,
        partner_id=partner_id,
        title=(body.title or "").strip()[:500],
        notes=(body.notes or "").strip()[:2000],
    )
    session.add(row)
    commit_with_error_handling(
        session, logger=logger, action="Add blueprint item",
        conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
    )
    session.refresh(row)
    return WishlistItemPublic(
        id=str(row.id),
        title=row.title,
        notes=row.notes,
        created_at=row.created_at.isoformat() + "Z",
        added_by_me=True,
    )


@router.get("/date-suggestions", response_model=DateSuggestionPublic)
def get_date_suggestions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> DateSuggestionPublic:
    """Return whether to suggest a date (e.g. no pair activity for 2 weeks)."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    data = get_date_suggestion(session, current_user.id, partner_id)
    return DateSuggestionPublic(**data)
