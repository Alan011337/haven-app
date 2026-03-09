# Module A2: Relationship baseline and couple goal API.

from uuid import UUID
import logging

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.relationship_baseline import RelationshipBaseline
from app.models.couple_goal import CoupleGoal
from app.schemas.baseline import (
    BASELINE_DIMENSIONS,
    COUPLE_GOAL_SLUGS,
    RelationshipBaselineCreate,
    RelationshipBaselinePublic,
    BaselineSummaryPublic,
    CoupleGoalCreate,
    CoupleGoalPublic,
)

logger = logging.getLogger(__name__)

baseline_router = APIRouter(tags=["baseline"])
couple_goal_router = APIRouter(tags=["couple-goal"])


def _canonical_pair(u1: UUID, u2: UUID) -> tuple[UUID, UUID]:
    return (min(u1, u2), max(u1, u2))


# --- Relationship baseline ---
@baseline_router.get("", response_model=BaselineSummaryPublic)
def get_baseline(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> BaselineSummaryPublic:
    """Return own baseline and partner's (if both filled). Only self and partner can read."""
    mine = session.exec(select(RelationshipBaseline).where(RelationshipBaseline.user_id == current_user.id)).first()
    partner_row = None
    if current_user.partner_id:
        partner_row = session.exec(
            select(RelationshipBaseline).where(RelationshipBaseline.user_id == current_user.partner_id)
        ).first()
    def _to_public(r: RelationshipBaseline) -> RelationshipBaselinePublic:
        return RelationshipBaselinePublic(
            user_id=str(r.user_id),
            partner_id=str(r.partner_id) if r.partner_id else None,
            filled_at=r.filled_at,
            scores=r.scores,
        )

    return BaselineSummaryPublic(
        mine=_to_public(mine) if mine else None,
        partner=_to_public(partner_row) if partner_row else None,
    )


@baseline_router.post("", response_model=RelationshipBaselinePublic, status_code=status.HTTP_201_CREATED)
def create_or_update_baseline(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: RelationshipBaselineCreate,
) -> RelationshipBaselinePublic:
    """Create or update own 5-dimension baseline. Scores must include all BASELINE_DIMENSIONS."""
    for dim in BASELINE_DIMENSIONS:
        if dim not in body.scores:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing dimension: {dim}. Required: {list(BASELINE_DIMENSIONS)}",
            )
    scores = {k: body.scores[k] for k in BASELINE_DIMENSIONS}
    row = session.exec(select(RelationshipBaseline).where(RelationshipBaseline.user_id == current_user.id)).first()
    if row:
        row.scores = scores
        row.partner_id = current_user.partner_id
        session.add(row)
    else:
        row = RelationshipBaseline(
            user_id=current_user.id,
            partner_id=current_user.partner_id,
            scores=scores,
        )
        session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Upsert relationship baseline",
        conflict_detail="儲存時發生衝突，請稍後再試。",
        failure_detail="儲存失敗，請稍後再試。",
    )
    session.refresh(row)
    return RelationshipBaselinePublic(
        user_id=str(row.user_id),
        partner_id=str(row.partner_id) if row.partner_id else None,
        filled_at=row.filled_at,
        scores=row.scores,
    )


# --- Couple goal ---
@couple_goal_router.get("", response_model=CoupleGoalPublic | None)
def get_couple_goal(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> CoupleGoalPublic | None:
    """Return the couple's chosen north star goal. Requires partner."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    uid1, uid2 = _canonical_pair(current_user.id, partner_id)
    row = session.exec(
        select(CoupleGoal).where(
            CoupleGoal.user_id == uid1,
            CoupleGoal.partner_id == uid2,
        )
    ).first()
    if not row:
        return None
    return CoupleGoalPublic(goal_slug=row.goal_slug, chosen_at=row.chosen_at)


@couple_goal_router.post("", response_model=CoupleGoalPublic, status_code=status.HTTP_201_CREATED)
def set_couple_goal(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: CoupleGoalCreate,
) -> CoupleGoalPublic:
    """Set or update the couple's north star goal. Requires partner."""
    if body.goal_slug not in COUPLE_GOAL_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"goal_slug must be one of: {', '.join(sorted(COUPLE_GOAL_SLUGS))}",
        )
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    uid1, uid2 = _canonical_pair(current_user.id, partner_id)
    row = session.exec(
        select(CoupleGoal).where(
            CoupleGoal.user_id == uid1,
            CoupleGoal.partner_id == uid2,
        )
    ).first()
    if row:
        row.goal_slug = body.goal_slug
        session.add(row)
    else:
        row = CoupleGoal(user_id=uid1, partner_id=uid2, goal_slug=body.goal_slug)
        session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Set couple goal",
        conflict_detail="儲存時發生衝突，請稍後再試。",
        failure_detail="儲存失敗，請稍後再試。",
    )
    session.refresh(row)
    return CoupleGoalPublic(goal_slug=row.goal_slug, chosen_at=row.chosen_at)
