# Module D1: Love Map — layered cards and notes.

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.card import Card
from app.models.couple_goal import CoupleGoal
from app.models.love_map_note import LoveMapNote
from app.models.relationship_baseline import RelationshipBaseline
from app.models.user import User
from app.models.wishlist_item import WishlistItem
from app.schemas.baseline import BaselineSummaryPublic, CoupleGoalPublic, RelationshipBaselinePublic
from app.schemas.blueprint import WishlistItemPublic
from app.schemas.love_map import (
    LoveMapCardSummary,
    LoveMapCardsResponse,
    LoveMapNoteCreate,
    LoveMapNotePublic,
    LoveMapStoryCapsulePublic,
    LoveMapStoryMomentPublic,
    LoveMapStoryPublic,
    LoveMapSystemMePublic,
    LoveMapSystemPartnerPublic,
    LoveMapSystemResponse,
    LoveMapSystemStatsPublic,
    LoveMapNoteUpdate,
)
from app.services.memory_archive import get_relationship_story_slice

logger = logging.getLogger(__name__)
router = APIRouter(tags=["love-map"])


def _depth_to_layer(d: int) -> str:
    if d <= 1:
        return "safe"
    if d == 2:
        return "medium"
    return "deep"


def _to_note_public(row: LoveMapNote) -> LoveMapNotePublic:
    return LoveMapNotePublic(
        id=str(row.id),
        layer=row.layer,
        content=row.content,
        created_at=row.created_at.isoformat() + "Z",
        updated_at=row.updated_at.isoformat() + "Z",
    )


def _to_baseline_public(row: RelationshipBaseline) -> RelationshipBaselinePublic:
    return RelationshipBaselinePublic(
        user_id=str(row.user_id),
        partner_id=str(row.partner_id) if row.partner_id else None,
        filled_at=row.filled_at,
        scores=row.scores,
    )


def _to_wishlist_public(*, row: WishlistItem, current_user: CurrentUser) -> WishlistItemPublic:
    return WishlistItemPublic(
        id=str(row.id),
        title=row.title,
        notes=row.notes,
        created_at=row.created_at.isoformat() + "Z",
        added_by_me=row.user_id == current_user.id,
    )


def _resolve_partner_name(partner: User) -> str | None:
    return partner.full_name or partner.email.split("@")[0]


def _to_iso_z(value: object) -> str:
    if hasattr(value, "isoformat"):
        return f"{value.isoformat()}Z"
    return str(value)


def _to_story_public(story_slice: dict[str, object] | None) -> LoveMapStoryPublic:
    if not story_slice:
        return LoveMapStoryPublic()

    moment_rows = story_slice.get("moments")
    capsule_row = story_slice.get("time_capsule")

    return LoveMapStoryPublic(
        available=bool(story_slice.get("available")),
        moments=[
            LoveMapStoryMomentPublic(
                kind=str(row["kind"]),
                title=str(row["title"]),
                description=str(row["description"]),
                occurred_at=_to_iso_z(row["occurred_at"]),
                badges=[str(badge) for badge in row.get("badges", [])],
                why_text=str(row["why_text"]),
            )
            for row in moment_rows
            if isinstance(row, dict)
        ]
        if isinstance(moment_rows, list)
        else [],
        time_capsule=(
            LoveMapStoryCapsulePublic(
                summary_text=str(capsule_row["summary_text"]),
                from_date=str(capsule_row["from_date"]),
                to_date=str(capsule_row["to_date"]),
                journals_count=int(capsule_row["journals_count"]),
                cards_count=int(capsule_row["cards_count"]),
                appreciations_count=int(capsule_row["appreciations_count"]),
            )
            if isinstance(capsule_row, dict)
            else None
        ),
    )


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
    return [_to_note_public(r) for r in rows]


@router.get("/system", response_model=LoveMapSystemResponse)
def get_love_map_system(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> LoveMapSystemResponse:
    """Return the current relationship-system snapshot for the Love Map surface."""
    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)

    mine_baseline = session.exec(
        select(RelationshipBaseline).where(RelationshipBaseline.user_id == current_user.id)
    ).first()
    partner_baseline = None
    partner = None

    if verified_partner_id:
        partner = session.get(User, verified_partner_id)
        partner_baseline = session.exec(
            select(RelationshipBaseline).where(RelationshipBaseline.user_id == verified_partner_id)
        ).first()

    couple_goal = None
    notes: list[LoveMapNotePublic] = []
    wishlist_items: list[WishlistItemPublic] = []
    note_rows: list[LoveMapNote] = []
    wishlist_rows: list[WishlistItem] = []
    story = LoveMapStoryPublic()

    if verified_partner_id:
        uid1, uid2 = min(current_user.id, verified_partner_id), max(current_user.id, verified_partner_id)
        goal_row = session.exec(
            select(CoupleGoal).where(
                CoupleGoal.user_id == uid1,
                CoupleGoal.partner_id == uid2,
            )
        ).first()
        if goal_row:
            couple_goal = CoupleGoalPublic(goal_slug=goal_row.goal_slug, chosen_at=goal_row.chosen_at)

        note_rows = session.exec(
            select(LoveMapNote).where(
                LoveMapNote.user_id == current_user.id,
                LoveMapNote.partner_id == verified_partner_id,
            )
        ).all()
        notes = [_to_note_public(row) for row in note_rows]

        wishlist_rows = session.exec(
            select(WishlistItem).where(
                ((WishlistItem.user_id == uid1) & (WishlistItem.partner_id == uid2))
                | ((WishlistItem.user_id == uid2) & (WishlistItem.partner_id == uid1)),
            ).order_by(WishlistItem.created_at.desc())
        ).all()
        wishlist_items = [_to_wishlist_public(row=row, current_user=current_user) for row in wishlist_rows]
        story = _to_story_public(
            get_relationship_story_slice(
                session=session,
                user_id=current_user.id,
                partner_id=verified_partner_id,
            )
        )

    timestamps = []
    if mine_baseline:
        timestamps.append(mine_baseline.filled_at)
    if partner_baseline:
        timestamps.append(partner_baseline.filled_at)
    if couple_goal:
        timestamps.append(couple_goal.chosen_at)
    timestamps.extend(row.updated_at for row in note_rows)
    timestamps.extend(row.created_at for row in wishlist_rows)

    last_activity_at = max(timestamps).isoformat() + "Z" if timestamps else None

    return LoveMapSystemResponse(
        has_partner=verified_partner_id is not None,
        me=LoveMapSystemMePublic(
            id=str(current_user.id),
            full_name=current_user.full_name,
            email=current_user.email,
        ),
        partner=(
            LoveMapSystemPartnerPublic(
                id=str(partner.id),
                partner_name=_resolve_partner_name(partner),
            )
            if partner
            else None
        ),
        baseline=BaselineSummaryPublic(
            mine=_to_baseline_public(mine_baseline) if mine_baseline else None,
            partner=_to_baseline_public(partner_baseline) if partner_baseline else None,
        ),
        couple_goal=couple_goal,
        story=story,
        notes=notes,
        wishlist_items=wishlist_items,
        stats=LoveMapSystemStatsPublic(
            filled_note_layers=sum(1 for note in notes if note.content.strip()),
            baseline_ready_mine=mine_baseline is not None,
            baseline_ready_partner=partner_baseline is not None,
            wishlist_count=len(wishlist_items),
            last_activity_at=last_activity_at,
        ),
    )


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
    return _to_note_public(r)


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
    return _to_note_public(row)
