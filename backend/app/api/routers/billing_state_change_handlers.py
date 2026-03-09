from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.api.error_handling import commit_with_error_handling
from app.core.datetime_utils import utcnow
from app.models.billing import BillingCommandLog, BillingEntitlementState, BillingLedgerEntry
from app.schemas.billing import BillingStateChangeRequest, BillingStateChangeResult
from app.services.billing_transitions import (
    canonical_state_change_payload_hash,
    normalize_action_or_raise,
    normalize_target_plan_or_raise,
    require_idempotency_key_or_raise,
    resolve_next_state_or_raise,
)


def handle_billing_state_change(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: BillingStateChangeRequest,
    idempotency_key: Optional[str],
    audit_billing_state_change_denied: Callable[..., None],
    logger: logging.Logger,
) -> BillingStateChangeResult:
    try:
        cleaned_idempotency_key = require_idempotency_key_or_raise(idempotency_key)
        action_value = normalize_action_or_raise(payload.action)
        target_plan_value = normalize_target_plan_or_raise(payload.target_plan)
    except HTTPException as exc:
        audit_billing_state_change_denied(
            session=session,
            user_id=current_user.id,
            reason="validation_error",
            detail=str(exc.detail),
        )
        raise

    payload_hash = canonical_state_change_payload_hash(
        action=action_value,
        target_plan=target_plan_value,
    )

    existing = session.exec(
        select(BillingCommandLog).where(
            BillingCommandLog.user_id == current_user.id,
            BillingCommandLog.idempotency_key == cleaned_idempotency_key,
        )
    ).first()

    if existing:
        if existing.payload_hash != payload_hash:
            audit_billing_state_change_denied(
                session=session,
                user_id=current_user.id,
                reason="idempotency_payload_mismatch",
                detail="Idempotency-Key reuse with different payload",
                metadata={"idempotency_key": cleaned_idempotency_key},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key reuse with a different payload is not allowed.",
            )
        existing_ledger = session.exec(
            select(BillingLedgerEntry).where(
                BillingLedgerEntry.source_type == "COMMAND",
                BillingLedgerEntry.source_key == f"cmd:{existing.id}",
            )
        ).first()
        return BillingStateChangeResult(
            status=existing.status,
            idempotency_replayed=True,
            command_id=existing.id,
            idempotency_key=existing.idempotency_key,
            action=existing.action,
            lifecycle_state=existing_ledger.next_state if existing_ledger else None,
            current_plan=existing_ledger.next_plan if existing_ledger else existing.target_plan,
            target_plan=existing.target_plan,
            processed_at=existing.processed_at,
        )

    entitlement = session.exec(
        select(BillingEntitlementState).where(BillingEntitlementState.user_id == current_user.id)
    ).first()
    previous_state = entitlement.lifecycle_state if entitlement else None
    previous_plan = entitlement.current_plan if entitlement else None
    try:
        next_state = resolve_next_state_or_raise(current_state=previous_state, action=action_value)
    except HTTPException as exc:
        audit_billing_state_change_denied(
            session=session,
            user_id=current_user.id,
            reason="invalid_transition",
            detail=str(exc.detail),
            metadata={"current_state": previous_state, "action": action_value},
        )
        raise
    next_plan = target_plan_value if target_plan_value is not None else previous_plan
    if next_state == "TRIAL" and not next_plan:
        next_plan = "FREE"

    command = BillingCommandLog(
        user_id=current_user.id,
        action=action_value,
        target_plan=target_plan_value,
        idempotency_key=cleaned_idempotency_key,
        payload_hash=payload_hash,
        status="APPLIED",
        processed_at=utcnow(),
    )
    session.add(command)

    ledger_entry = BillingLedgerEntry(
        user_id=current_user.id,
        source_type="COMMAND",
        source_key=f"cmd:{command.id}",
        action=action_value,
        previous_state=previous_state,
        next_state=next_state,
        previous_plan=previous_plan,
        next_plan=next_plan,
        payload_hash=payload_hash,
    )
    session.add(ledger_entry)

    if entitlement:
        entitlement.lifecycle_state = next_state
        entitlement.current_plan = next_plan
        entitlement.last_command_id = command.id
        entitlement.updated_at = utcnow()
        entitlement.revision += 1
        session.add(entitlement)
    else:
        session.add(
            BillingEntitlementState(
                user_id=current_user.id,
                lifecycle_state=next_state,
                current_plan=next_plan,
                last_command_id=command.id,
                revision=1,
            )
        )

    commit_with_error_handling(
        session,
        logger=logger,
        action="Billing state change",
        conflict_detail="Billing state change conflict. Please retry.",
        failure_detail="Billing state change failed.",
    )
    session.refresh(command)

    return BillingStateChangeResult(
        status=command.status,
        idempotency_replayed=False,
        command_id=command.id,
        idempotency_key=command.idempotency_key,
        action=command.action,
        lifecycle_state=next_state,
        current_plan=next_plan,
        target_plan=command.target_plan,
        processed_at=command.processed_at,
    )
