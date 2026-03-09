# Module C1: SOS cool-down API.

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.schemas.cooldown import (
    CooldownRewriteBody,
    CooldownRewriteResponse,
    CooldownStartBody,
    CooldownStatusPublic,
)
from app.services.cooldown_runtime import get_status_for_user, start_cooldown
from app.services.notification_payloads import build_partner_notification_payload
from app.services.notification import queue_partner_notification
from app.services.ai import rewrite_aggressive_to_i_message

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cooldown"])


@router.get("/status", response_model=CooldownStatusPublic)
def get_cooldown_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> CooldownStatusPublic:
    """Return current user's cooldown status (with partner). No PII in logs."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    status_data = get_status_for_user(session, current_user.id, partner_id)
    return CooldownStatusPublic(**status_data)


@router.post("/start", response_model=CooldownStatusPublic)
def start_cooldown_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: CooldownStartBody,
) -> CooldownStatusPublic:
    """Start a cool-down session; notify partner. Requires active partner."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")
    existing = get_status_for_user(session, current_user.id, partner_id)
    if existing["in_cooldown"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已在冷卻中")
    row = start_cooldown(
        session, current_user.id, partner_id, body.duration_minutes
    )
    commit_with_error_handling(
        session, logger=logger, action="Start cooldown",
        conflict_detail="啟動冷卻時發生衝突。", failure_detail="啟動失敗。",
    )
    session.refresh(row)
    payload = build_partner_notification_payload(
        session=session,
        sender_user=current_user,
        event_type="cooldown_started",
        scope_id=row.id,
        partner_user_id=partner_id,
    )
    if payload:
        queue_partner_notification(
            action_type="cooldown_started",
            event_type="cooldown_started",
            **payload,
        )
    status_data = get_status_for_user(session, current_user.id, partner_id)
    return CooldownStatusPublic(**status_data)


@router.post("/rewrite-message", response_model=CooldownRewriteResponse)
async def rewrite_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: CooldownRewriteBody,
) -> CooldownRewriteResponse:
    """Rewrite aggressive message to I-statement style. Only when user is in active cooldown."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")
    status_data = get_status_for_user(session, current_user.id, partner_id)
    if not status_data["in_cooldown"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="僅在冷卻期間可使用訊息改寫",
        )
    rewritten = await rewrite_aggressive_to_i_message(body.message)
    return CooldownRewriteResponse(rewritten=rewritten)
