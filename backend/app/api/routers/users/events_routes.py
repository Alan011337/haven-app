from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.routers.users.events_referrals_handlers import (
    handle_track_core_loop_event,
    handle_track_cuj_event,
    handle_track_referral_couple_invite,
    handle_track_referral_landing_view,
    handle_track_referral_signup,
)
from app.schemas.growth import (
    CoreLoopEventTrackRequest,
    CoreLoopEventTrackResult,
    CujEventTrackRequest,
    CujEventTrackResult,
    ReferralCoupleInviteTrackRequest,
    ReferralEventTrackResult,
    ReferralLandingViewTrackRequest,
    ReferralSignupTrackRequest,
)

router = APIRouter()


@router.post("/events/cuj", response_model=CujEventTrackResult, status_code=status.HTTP_202_ACCEPTED)
def track_cuj_event(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: CujEventTrackRequest,
) -> CujEventTrackResult:
    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    return handle_track_cuj_event(
        session=session,
        current_user=current_user,
        verified_partner_id=verified_partner_id,
        payload=payload,
    )


@router.post(
    "/events/core-loop",
    response_model=CoreLoopEventTrackResult,
    status_code=status.HTTP_202_ACCEPTED,
)
def track_core_loop_event(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: CoreLoopEventTrackRequest,
) -> CoreLoopEventTrackResult:
    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    return handle_track_core_loop_event(
        session=session,
        current_user=current_user,
        verified_partner_id=verified_partner_id,
        payload=payload,
    )


@router.post(
    "/referrals/landing-view",
    response_model=ReferralEventTrackResult,
    status_code=status.HTTP_202_ACCEPTED,
)
def track_referral_landing_view(
    *,
    session: SessionDep,
    payload: ReferralLandingViewTrackRequest,
) -> ReferralEventTrackResult:
    return handle_track_referral_landing_view(
        session=session,
        payload=payload,
    )


@router.post("/referrals/signup", response_model=ReferralEventTrackResult)
def track_referral_signup(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: ReferralSignupTrackRequest,
) -> ReferralEventTrackResult:
    return handle_track_referral_signup(
        session=session,
        current_user=current_user,
        payload=payload,
    )


@router.post("/referrals/couple-invite", response_model=ReferralEventTrackResult)
def track_referral_couple_invite(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: ReferralCoupleInviteTrackRequest,
) -> ReferralEventTrackResult:
    return handle_track_referral_couple_invite(
        session=session,
        current_user=current_user,
        payload=payload,
    )

