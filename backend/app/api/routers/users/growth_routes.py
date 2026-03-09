from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.routers.users.growth_handlers import (
    handle_acknowledge_my_first_delight,
    handle_deliver_my_sync_nudge,
    handle_read_my_feature_flags,
    handle_read_my_first_delight,
    handle_read_my_gamification_summary,
    handle_read_my_onboarding_quest,
    handle_read_my_reengagement_hooks,
    handle_read_my_sync_nudges,
)
from app.schemas.growth import (
    FeatureFlagsPublic,
    FirstDelightAcknowledgeRequest,
    FirstDelightAcknowledgeResult,
    FirstDelightPublic,
    GamificationSummaryPublic,
    OnboardingQuestPublic,
    ReengagementHooksPublic,
    SyncNudgeDeliverRequest,
    SyncNudgeDeliverResult,
    SyncNudgeType,
    SyncNudgesPublic,
)

router = APIRouter()


@router.get("/feature-flags", response_model=FeatureFlagsPublic)
def read_my_feature_flags(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> FeatureFlagsPublic:
    return handle_read_my_feature_flags(
        session=session,
        current_user=current_user,
    )


@router.get("/gamification-summary", response_model=GamificationSummaryPublic)
def read_my_gamification_summary(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> GamificationSummaryPublic:
    return handle_read_my_gamification_summary(
        session=session,
        current_user=current_user,
    )


@router.get("/reengagement-hooks", response_model=ReengagementHooksPublic)
def read_my_reengagement_hooks(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> ReengagementHooksPublic:
    return handle_read_my_reengagement_hooks(
        session=session,
        current_user=current_user,
    )


@router.get("/onboarding-quest", response_model=OnboardingQuestPublic)
def read_my_onboarding_quest(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> OnboardingQuestPublic:
    return handle_read_my_onboarding_quest(
        session=session,
        current_user=current_user,
    )


@router.get("/sync-nudges", response_model=SyncNudgesPublic)
def read_my_sync_nudges(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> SyncNudgesPublic:
    return handle_read_my_sync_nudges(
        session=session,
        current_user=current_user,
    )


@router.get("/first-delight", response_model=FirstDelightPublic)
def read_my_first_delight(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> FirstDelightPublic:
    return handle_read_my_first_delight(
        session=session,
        current_user=current_user,
    )


@router.post("/first-delight/ack", response_model=FirstDelightAcknowledgeResult)
def acknowledge_my_first_delight(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: FirstDelightAcknowledgeRequest,
) -> FirstDelightAcknowledgeResult:
    return handle_acknowledge_my_first_delight(
        session=session,
        current_user=current_user,
        payload=payload,
    )


@router.post("/sync-nudges/{nudge_type}/deliver", response_model=SyncNudgeDeliverResult)
def deliver_my_sync_nudge(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    nudge_type: SyncNudgeType,
    payload: SyncNudgeDeliverRequest,
) -> SyncNudgeDeliverResult:
    return handle_deliver_my_sync_nudge(
        session=session,
        current_user=current_user,
        nudge_type=nudge_type,
        payload=payload,
    )

