# Module D1: Love Map — layered cards and notes.

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.card import Card
from app.models.love_map_note import LoveMapNote
from app.schemas.love_map import (
    LoveMapCardSummary,
    LoveMapCardsResponse,
    LoveMapNoteCreate,
    LoveMapNotePublic,
    LoveMapNoteUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["love-map"])


def _depth_to_layer(d: int) -> str:
    if d <= 1:
        return "safe"
    if d == 2:
        return "medium"
    return "deep"


@router.get("/cards", response_model=LoveMapCardsResponse)
def get_love_map_cards(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> LoveMapCardsResponse:
    """Return cards grouped by layer (safe=depth 1, medium=2, deep=3). No partner required."""
    rows = session.exec(select(Card).where(Card.depth_level.is_(None) | (Card.depth_level >= 1))).all()
    safe, medium, deep = [], [], []
    for c in rows:
        layer = _depth_to_layer(c.depth_level if c.depth_level is not None else 1)
        summary = LoveMapCardSummary(
            id=str(c.id),
            title=c.title,
            description=c.description,
            question=c.question,
            depth_level=c.depth_level or 1,
            layer=layer,
        )
        if layer == "safe":
            safe.append(summary)
        elif layer == "medium":
            medium.append(summary)
        else:
            deep.append(summary)
    return LoveMapCardsResponse(safe=safe, medium=medium, deep=deep)


@router.get("/notes", response_model=list[LoveMapNotePublic])
def list_love_map_notes(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[LoveMapNotePublic]:
    """List current user's love map notes (for their partner pair)."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return []
    uid1, uid2 = min(current_user.id, partner_id), max(current_user.id, partner_id)
    rows = session.exec(
        select(LoveMapNote).where(
            ((LoveMapNote.user_id == uid1) & (LoveMapNote.partner_id == uid2))
            | ((LoveMapNote.user_id == uid2) & (LoveMapNote.partner_id == uid1)),
            LoveMapNote.user_id == current_user.id,
        )
    ).all()
    return [
        LoveMapNotePublic(
            id=str(r.id),
            layer=r.layer,
            content=r.content,
            created_at=r.created_at.isoformat() + "Z",
            updated_at=r.updated_at.isoformat() + "Z",
        )
        for r in rows
    ]


@router.post("/notes", response_model=LoveMapNotePublic)
def create_or_update_love_map_note(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: LoveMapNoteCreate,
) -> LoveMapNotePublic:
    """Upsert a note for the given layer (one note per user per layer per pair)."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")
    from app.core.datetime_utils import utcnow
    existing = session.exec(
        select(LoveMapNote).where(
            LoveMapNote.user_id == current_user.id,
            LoveMapNote.partner_id == partner_id,
            LoveMapNote.layer == body.layer,
        )
    ).first()
    now = utcnow()
    if existing:
        existing.content = (body.content or "")[:5000]
        existing.updated_at = now
        session.add(existing)
        commit_with_error_handling(
            session, logger=logger, action="Update love map note",
            conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
        )
        session.refresh(existing)
        r = existing
    else:
        row = LoveMapNote(
            user_id=current_user.id,
            partner_id=partner_id,
            layer=body.layer,
            content=(body.content or "")[:5000],
        )
        session.add(row)
        commit_with_error_handling(
            session, logger=logger, action="Create love map note",
            conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
        )
        session.refresh(row)
        r = row
    return LoveMapNotePublic(
        id=str(r.id),
        layer=r.layer,
        content=r.content,
        created_at=r.created_at.isoformat() + "Z",
        updated_at=r.updated_at.isoformat() + "Z",
    )


@router.put("/notes/{note_id}", response_model=LoveMapNotePublic)
def update_love_map_note(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    note_id: UUID,
    body: LoveMapNoteUpdate,
) -> LoveMapNotePublic:
    """Update a note by id. BOLA: only owner can update."""
    row = session.get(LoveMapNote, note_id)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該筆記")
    from app.core.datetime_utils import utcnow
    row.content = (body.content or "")[:5000]
    row.updated_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session, logger=logger, action="Update love map note by id",
        conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
    )
    session.refresh(row)
    return LoveMapNotePublic(
        id=str(row.id),
        layer=row.layer,
        content=row.content,
        created_at=row.created_at.isoformat() + "Z",
        updated_at=row.updated_at.isoformat() + "Z",
    )
