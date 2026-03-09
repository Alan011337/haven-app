# P2-D / C3: Mediation mode API — status and submit answers (with answer text + next_sop).

import logging
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep, CurrentUser, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.services.mediation_runtime import get_mediation_status, record_mediation_answers
from app.services.feature_flags import list_feature_flags_for_client
from app.services.repair_flow_runtime import (
    RepairFlowNotFoundError,
    RepairFlowSafetyModeError,
    RepairFlowValidationError,
    complete_repair_step,
    get_repair_flow_status,
    start_repair_flow,
)
from app.schemas.repair_flow import (
    RepairFlowStartBody,
    RepairFlowStartResult,
    RepairFlowStatusPublic,
    RepairFlowStepCompleteBody,
    RepairFlowStepCompleteResult,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_repair_flow_partner_or_raise(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> uuid_mod.UUID:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Repair flow requires an active partner.",
        )

    feature_payload = list_feature_flags_for_client(has_partner=True)
    enabled = bool(feature_payload["flags"].get("repair_flow_v1", False))
    kill_switch_active = bool(feature_payload["kill_switches"].get("disable_repair_flow_v1", False))
    if not enabled or kill_switch_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repair flow is disabled.",
        )
    return partner_id


@router.get("/status")
def get_mediation_status_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Return whether user is in mediation, guided questions, answer status, and when both done: my_answers, partner_answers, next_sop."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    return get_mediation_status(
        session=session,
        current_user_id=current_user.id,
        partner_id=partner_id,
    )


@router.post("/answers")
def submit_mediation_answers(
    session: SessionDep,
    current_user: CurrentUser,
    body: dict[str, Any],
) -> dict[str, str]:
    """Record current user's mediation answers. Body: { session_id: string, answers?: [string, string, string] }."""
    session_id_raw = body.get("session_id")
    if not session_id_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session_id")
    try:
        med_id = uuid_mod.UUID(str(session_id_raw))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")
    answers = body.get("answers")
    if answers is not None and not isinstance(answers, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="answers must be a list")
    updated = record_mediation_answers(
        session=session,
        mediation_session_id=med_id,
        user_id=current_user.id,
        answers=answers if isinstance(answers, list) and len(answers) >= 3 else None,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or not your session")
    commit_with_error_handling(
        session, logger=logger, action="Submit mediation answers",
        conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
    )
    return {"status": "ok", "message": "已記錄你的回答"}


@router.post("/repair/start", response_model=RepairFlowStartResult)
def start_repair_flow_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    body: RepairFlowStartBody,
) -> RepairFlowStartResult:
    partner_id = _resolve_repair_flow_partner_or_raise(
        session=session, current_user=current_user
    )
    result = start_repair_flow(
        session=session,
        user_id=current_user.id,
        partner_user_id=partner_id,
        source_session_id=body.source_session_id,
        source=body.source,
    )
    if result.changed:
        commit_with_error_handling(
            session,
            logger=logger,
            action="Start repair flow",
            conflict_detail="建立修復流程時發生衝突。",
            failure_detail="建立修復流程失敗。",
        )
    return RepairFlowStartResult(
        accepted=result.accepted,
        deduped=result.deduped,
        session_id=result.session_id,
    )


@router.get("/repair/status", response_model=RepairFlowStatusPublic)
def get_repair_flow_status_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    session_id: str,
) -> RepairFlowStatusPublic:
    partner_id = _resolve_repair_flow_partner_or_raise(
        session=session, current_user=current_user
    )
    try:
        status_data = get_repair_flow_status(
            session=session,
            repair_session_id=session_id,
            user_id=current_user.id,
            partner_user_id=partner_id,
        )
    except RepairFlowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return RepairFlowStatusPublic(
        enabled=True,
        session_id=status_data.session_id,
        in_repair_flow=True,
        safety_mode_active=status_data.safety_mode_active,
        completed=status_data.completed,
        current_step=status_data.current_step,
        my_completed_steps=status_data.my_completed_steps,
        partner_completed_steps=status_data.partner_completed_steps,
    )


@router.post("/repair/step-complete", response_model=RepairFlowStepCompleteResult)
def complete_repair_flow_step_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    body: RepairFlowStepCompleteBody,
) -> RepairFlowStepCompleteResult:
    partner_id = _resolve_repair_flow_partner_or_raise(
        session=session, current_user=current_user
    )
    try:
        result = complete_repair_step(
            session=session,
            repair_session_id=body.session_id,
            step=body.step,
            user_id=current_user.id,
            partner_user_id=partner_id,
            source=body.source,
            i_feel=body.i_feel,
            i_need=body.i_need,
            mirror_text=body.mirror_text,
            shared_commitment=body.shared_commitment,
            improvement_note=body.improvement_note,
        )
    except RepairFlowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepairFlowValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RepairFlowSafetyModeError as exc:
        commit_with_error_handling(
            session,
            logger=logger,
            action="Enter repair flow safety mode",
            conflict_detail="進入安全模式時發生衝突。",
            failure_detail="進入安全模式失敗。",
        )
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc

    if result.changed:
        commit_with_error_handling(
            session,
            logger=logger,
            action="Complete repair flow step",
            conflict_detail="更新修復流程時發生衝突。",
            failure_detail="更新修復流程失敗。",
        )
    return RepairFlowStepCompleteResult(
        accepted=result.accepted,
        deduped=result.deduped,
        step=body.step,
        completed=result.completed,
        safety_mode_active=result.safety_mode_active,
    )
