from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, select, and_, or_

from app.core.datetime_utils import utcnow
from app.models.events_log import EventsLog
from app.models.relationship_repair_outcome_capture import (
    RelationshipRepairOutcomeCapture,
)
from app.services.events_log import record_core_loop_event

logger = logging.getLogger(__name__)

REPAIR_STEP_COUNT = 5
EVENT_REPAIR_STARTED = "repair_started"
EVENT_REPAIR_STEP_COMPLETED = "repair_step_completed"
EVENT_REPAIR_COMPLETED = "repair_completed"
EVENT_SAFETY_MODE_ENTERED = "safety_mode_entered"
REPAIR_EVENT_SOURCE = "repair_flow_v1"
OUTCOME_CAPTURE_STATUS_COLLECTING = "collecting"
OUTCOME_CAPTURE_STATUS_PENDING = "pending"
OUTCOME_CAPTURE_STATUS_APPLIED = "applied"
OUTCOME_CAPTURE_STATUS_DISMISSED = "dismissed"

_HIGH_RISK_KEYWORDS = (
    "自殺",
    "自残",
    "自殘",
    "傷害自己",
    "殺了自己",
    "kill myself",
    "suicide",
    "hurt myself",
    "殺了他",
    "殺了她",
    "傷害他",
    "傷害她",
    "kill you",
    "hurt you",
)


class RepairFlowError(ValueError):
    pass


class RepairFlowNotFoundError(RepairFlowError):
    pass


class RepairFlowSafetyModeError(RepairFlowError):
    pass


class RepairFlowValidationError(RepairFlowError):
    pass


@dataclass(frozen=True)
class RepairFlowStartResult:
    accepted: bool
    deduped: bool
    session_id: str
    changed: bool


@dataclass(frozen=True)
class RepairFlowStepResult:
    accepted: bool
    deduped: bool
    completed: bool
    safety_mode_active: bool
    changed: bool


@dataclass(frozen=True)
class RepairFlowStatus:
    session_id: str
    safety_mode_active: bool
    completed: bool
    current_step: int
    my_completed_steps: list[int]
    partner_completed_steps: list[int]
    outcome_capture_pending: bool


def _parse_json_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _extract_steps(rows: list[EventsLog], *, user_id: uuid.UUID) -> set[int]:
    out: set[int] = set()
    for row in rows:
        if row.user_id != user_id:
            continue
        props = _parse_json_payload(row.props_json)
        step_value = props.get("step")
        if isinstance(step_value, int) and 1 <= step_value <= REPAIR_STEP_COUNT:
            out.add(step_value)
    return out


def _extract_started_event(
    *,
    session: Session,
    repair_session_id: str,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
) -> EventsLog | None:
    return session.exec(
        select(EventsLog).where(
            and_(
                EventsLog.event_name == EVENT_REPAIR_STARTED,
                EventsLog.session_id == repair_session_id,
                or_(
                    and_(
                        EventsLog.user_id == user_id,
                        EventsLog.partner_user_id == partner_user_id,
                    ),
                    and_(
                        EventsLog.user_id == partner_user_id,
                        EventsLog.partner_user_id == user_id,
                    ),
                ),
            )
        ).order_by(EventsLog.ts.desc())
    ).first()


def _list_repair_events(
    *,
    session: Session,
    repair_session_id: str,
) -> list[EventsLog]:
    return list(
        session.exec(
            select(EventsLog).where(
                and_(
                    EventsLog.session_id == repair_session_id,
                    EventsLog.event_name.in_(
                        (
                            EVENT_REPAIR_STEP_COMPLETED,
                            EVENT_REPAIR_COMPLETED,
                            EVENT_SAFETY_MODE_ENTERED,
                        )
                    ),
                )
            )
        ).all()
    )


def _is_safety_mode_active(rows: list[EventsLog]) -> bool:
    return any(row.event_name == EVENT_SAFETY_MODE_ENTERED for row in rows)


def _is_completed(rows: list[EventsLog], my_steps: set[int], partner_steps: set[int]) -> bool:
    if REPAIR_STEP_COUNT in my_steps and REPAIR_STEP_COUNT in partner_steps:
        return True
    return any(row.event_name == EVENT_REPAIR_COMPLETED for row in rows)


def _current_step(my_steps: set[int], partner_steps: set[int]) -> int:
    for step in range(1, REPAIR_STEP_COUNT + 1):
        if step not in my_steps or step not in partner_steps:
            return step
    return REPAIR_STEP_COUNT


def _contains_high_risk_phrase(*texts: str | None) -> bool:
    merged = " ".join((text or "").strip().lower() for text in texts if text)
    if not merged:
        return False
    return any(keyword in merged for keyword in _HIGH_RISK_KEYWORDS)


def _normalize_capture_text(value: str | None) -> str | None:
    trimmed = (value or "").strip()
    if not trimmed:
        return None
    return trimmed[:300]


def _build_safe_step_props(
    *,
    step: int,
    i_feel: str | None,
    i_need: str | None,
    mirror_text: str | None,
    shared_commitment: str | None,
    improvement_note: str | None,
) -> dict[str, Any]:
    return {
        "step": step,
        "flow_version": "v1",
        "i_feel_len": len((i_feel or "").strip()),
        "i_need_len": len((i_need or "").strip()),
        "mirror_text_len": len((mirror_text or "").strip()),
        "shared_commitment_len": len((shared_commitment or "").strip()),
        "improvement_note_len": len((improvement_note or "").strip()),
    }


def _validate_step_payload(
    *,
    step: int,
    i_feel: str | None,
    i_need: str | None,
    mirror_text: str | None,
    shared_commitment: str | None,
    improvement_note: str | None,
) -> None:
    if step == 1:
        return
    if step == 2 and (not (i_feel or "").strip() or not (i_need or "").strip()):
        raise RepairFlowValidationError("Step 2 requires both i_feel and i_need.")
    if step == 3 and not (mirror_text or "").strip():
        raise RepairFlowValidationError("Step 3 requires mirror_text.")
    if step == 4 and not (shared_commitment or "").strip():
        raise RepairFlowValidationError("Step 4 requires shared_commitment.")
    if step == 5 and not (improvement_note or "").strip():
        raise RepairFlowValidationError("Step 5 requires improvement_note.")


def _pair_scope_ids(user_id: uuid.UUID, partner_user_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return min(user_id, partner_user_id), max(user_id, partner_user_id)


def _load_outcome_capture(
    *,
    session: Session,
    repair_session_id: str,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
) -> RelationshipRepairOutcomeCapture | None:
    uid1, uid2 = _pair_scope_ids(user_id, partner_user_id)
    return session.exec(
        select(RelationshipRepairOutcomeCapture).where(
            RelationshipRepairOutcomeCapture.user_id == uid1,
            RelationshipRepairOutcomeCapture.partner_id == uid2,
            RelationshipRepairOutcomeCapture.repair_session_id == repair_session_id,
        )
    ).first()


def _upsert_outcome_capture(
    *,
    session: Session,
    repair_session_id: str,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
    shared_commitment: str | None = None,
    improvement_note: str | None = None,
    status: str = OUTCOME_CAPTURE_STATUS_COLLECTING,
) -> RelationshipRepairOutcomeCapture:
    uid1, uid2 = _pair_scope_ids(user_id, partner_user_id)
    row = _load_outcome_capture(
        session=session,
        repair_session_id=repair_session_id,
        user_id=user_id,
        partner_user_id=partner_user_id,
    )
    if row is None:
        row = RelationshipRepairOutcomeCapture(
            user_id=uid1,
            partner_id=uid2,
            repair_session_id=repair_session_id,
            created_by_user_id=user_id,
        )

    if shared_commitment is not None:
        row.shared_commitment = _normalize_capture_text(shared_commitment)
    if improvement_note is not None:
        row.improvement_note = _normalize_capture_text(improvement_note)

    row.status = status
    row.created_by_user_id = user_id
    row.reviewed_by_user_id = None
    row.reviewed_at = None
    row.updated_at = utcnow()
    session.add(row)
    return row


def start_repair_flow(
    *,
    session: Session,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
    source_session_id: str | None = None,
    source: str = "web",
) -> RepairFlowStartResult:
    repair_session_id = str(uuid.uuid4())
    event_id = f"repair-start:{repair_session_id}:{user_id}"
    start_result = record_core_loop_event(
        session=session,
        user_id=user_id,
        partner_user_id=partner_user_id,
        event_name=EVENT_REPAIR_STARTED,
        event_id=event_id,
        source=source or REPAIR_EVENT_SOURCE,
        session_id=repair_session_id,
        props={
            "flow_version": "v1",
            "source_session_present": bool((source_session_id or "").strip()),
        },
    )
    first_step_result = record_core_loop_event(
        session=session,
        user_id=user_id,
        partner_user_id=partner_user_id,
        event_name=EVENT_REPAIR_STEP_COMPLETED,
        event_id=f"repair-step:{repair_session_id}:1:{user_id}",
        source=source or REPAIR_EVENT_SOURCE,
        session_id=repair_session_id,
        props={"step": 1, "flow_version": "v1"},
    )
    partner_first_step_result = record_core_loop_event(
        session=session,
        user_id=partner_user_id,
        partner_user_id=user_id,
        event_name=EVENT_REPAIR_STEP_COMPLETED,
        event_id=f"repair-step:{repair_session_id}:1:{partner_user_id}",
        source=source or REPAIR_EVENT_SOURCE,
        session_id=repair_session_id,
        props={"step": 1, "flow_version": "v1", "auto_generated": True},
    )
    return RepairFlowStartResult(
        accepted=bool(start_result.accepted),
        deduped=bool(start_result.deduped),
        session_id=repair_session_id,
        changed=bool(
            (not start_result.deduped)
            or (not first_step_result.deduped)
            or (not partner_first_step_result.deduped)
        ),
    )


def get_repair_flow_status(
    *,
    session: Session,
    repair_session_id: str,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
) -> RepairFlowStatus:
    started = _extract_started_event(
        session=session,
        repair_session_id=repair_session_id,
        user_id=user_id,
        partner_user_id=partner_user_id,
    )
    if not started:
        raise RepairFlowNotFoundError("Repair flow session not found for this pair.")

    rows = _list_repair_events(session=session, repair_session_id=repair_session_id)
    my_steps = _extract_steps(rows, user_id=user_id)
    partner_steps = _extract_steps(rows, user_id=partner_user_id)
    safety_mode_active = _is_safety_mode_active(rows)
    completed = _is_completed(rows, my_steps, partner_steps)
    outcome_capture = _load_outcome_capture(
        session=session,
        repair_session_id=repair_session_id,
        user_id=user_id,
        partner_user_id=partner_user_id,
    )
    return RepairFlowStatus(
        session_id=repair_session_id,
        safety_mode_active=safety_mode_active,
        completed=completed,
        current_step=_current_step(my_steps, partner_steps),
        my_completed_steps=sorted(my_steps),
        partner_completed_steps=sorted(partner_steps),
        outcome_capture_pending=bool(
            completed
            and outcome_capture
            and outcome_capture.status == OUTCOME_CAPTURE_STATUS_PENDING
        ),
    )


def complete_repair_step(
    *,
    session: Session,
    repair_session_id: str,
    step: int,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID,
    source: str = "web",
    i_feel: str | None = None,
    i_need: str | None = None,
    mirror_text: str | None = None,
    shared_commitment: str | None = None,
    improvement_note: str | None = None,
) -> RepairFlowStepResult:
    if step < 1 or step > REPAIR_STEP_COUNT:
        raise RepairFlowValidationError("step must be between 1 and 5.")

    started = _extract_started_event(
        session=session,
        repair_session_id=repair_session_id,
        user_id=user_id,
        partner_user_id=partner_user_id,
    )
    if not started:
        raise RepairFlowNotFoundError("Repair flow session not found for this pair.")

    rows = _list_repair_events(session=session, repair_session_id=repair_session_id)
    if _is_safety_mode_active(rows):
        raise RepairFlowSafetyModeError("Safety mode is active for this repair session.")

    _validate_step_payload(
        step=step,
        i_feel=i_feel,
        i_need=i_need,
        mirror_text=mirror_text,
        shared_commitment=shared_commitment,
        improvement_note=improvement_note,
    )

    if _contains_high_risk_phrase(
        i_feel, i_need, mirror_text, shared_commitment, improvement_note
    ):
        record_core_loop_event(
            session=session,
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name=EVENT_SAFETY_MODE_ENTERED,
            event_id=f"safety-mode:{repair_session_id}:{user_id}",
            source=source or REPAIR_EVENT_SOURCE,
            session_id=repair_session_id,
            props={"flow_version": "v1", "trigger": "keyword", "step": step},
        )
        raise RepairFlowSafetyModeError(
            "High-risk language detected. Safety mode has been enabled."
        ) from None

    my_steps = _extract_steps(rows, user_id=user_id)
    expected_step = min(
        max(my_steps) + 1 if my_steps else 1,
        REPAIR_STEP_COUNT,
    )
    if step > expected_step:
        raise RepairFlowValidationError(
            f"Step order violation: expected step {expected_step}."
        )

    record_result = record_core_loop_event(
        session=session,
        user_id=user_id,
        partner_user_id=partner_user_id,
        event_name=EVENT_REPAIR_STEP_COMPLETED,
        event_id=f"repair-step:{repair_session_id}:{step}:{user_id}",
        source=source or REPAIR_EVENT_SOURCE,
        session_id=repair_session_id,
        props=_build_safe_step_props(
            step=step,
            i_feel=i_feel,
            i_need=i_need,
            mirror_text=mirror_text,
            shared_commitment=shared_commitment,
            improvement_note=improvement_note,
        ),
    )
    changed = not record_result.deduped
    if not record_result.deduped and step == 4:
        _upsert_outcome_capture(
            session=session,
            repair_session_id=repair_session_id,
            user_id=user_id,
            partner_user_id=partner_user_id,
            shared_commitment=shared_commitment,
            status=OUTCOME_CAPTURE_STATUS_COLLECTING,
        )
    if not record_result.deduped and step == 5:
        _upsert_outcome_capture(
            session=session,
            repair_session_id=repair_session_id,
            user_id=user_id,
            partner_user_id=partner_user_id,
            improvement_note=improvement_note,
            status=OUTCOME_CAPTURE_STATUS_COLLECTING,
        )

    refreshed_status = get_repair_flow_status(
        session=session,
        repair_session_id=repair_session_id,
        user_id=user_id,
        partner_user_id=partner_user_id,
    )
    if (
        refreshed_status.completed
        and (not refreshed_status.safety_mode_active)
        and step == REPAIR_STEP_COUNT
    ):
        completed_result = record_core_loop_event(
            session=session,
            user_id=user_id,
            partner_user_id=partner_user_id,
            event_name=EVENT_REPAIR_COMPLETED,
            event_id=f"repair-complete:{repair_session_id}:{user_id}",
            source=source or REPAIR_EVENT_SOURCE,
            session_id=repair_session_id,
            props={"flow_version": "v1", "completion_step": REPAIR_STEP_COUNT},
        )
        if not completed_result.deduped:
            changed = True
        if not record_result.deduped:
            _upsert_outcome_capture(
                session=session,
                repair_session_id=repair_session_id,
                user_id=user_id,
                partner_user_id=partner_user_id,
                improvement_note=improvement_note,
                status=OUTCOME_CAPTURE_STATUS_PENDING,
            )
            changed = True
        refreshed_status = get_repair_flow_status(
            session=session,
            repair_session_id=repair_session_id,
            user_id=user_id,
            partner_user_id=partner_user_id,
        )

    return RepairFlowStepResult(
        accepted=bool(record_result.accepted),
        deduped=bool(record_result.deduped),
        completed=refreshed_status.completed,
        safety_mode_active=refreshed_status.safety_mode_active,
        changed=changed,
    )
