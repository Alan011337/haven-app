from __future__ import annotations

import hashlib
import json
from typing import Optional

from fastapi import HTTPException, status

STATE_FOR_ACTION: dict[str, str] = {
    "START_TRIAL": "TRIAL",
    "ACTIVATE": "ACTIVE",
    "UPGRADE": "ACTIVE",
    "DOWNGRADE": "ACTIVE",
    "MARK_PAST_DUE": "PAST_DUE",
    "ENTER_GRACE_PERIOD": "GRACE_PERIOD",
    "ENTER_ACCOUNT_HOLD": "GRACE_PERIOD",
    "CANCEL": "CANCELED",
    "REACTIVATE": "ACTIVE",
}

ALLOWED_TRANSITIONS: dict[Optional[str], set[str]] = {
    None: {"START_TRIAL", "ACTIVATE", "UPGRADE", "DOWNGRADE"},
    "TRIAL": {"ACTIVATE", "CANCEL", "UPGRADE", "DOWNGRADE"},
    "ACTIVE": {"UPGRADE", "DOWNGRADE", "MARK_PAST_DUE", "ENTER_GRACE_PERIOD", "ENTER_ACCOUNT_HOLD", "CANCEL"},
    "PAST_DUE": {"ACTIVATE", "ENTER_GRACE_PERIOD", "ENTER_ACCOUNT_HOLD", "CANCEL"},
    "GRACE_PERIOD": {"ACTIVATE", "MARK_PAST_DUE", "ENTER_GRACE_PERIOD", "ENTER_ACCOUNT_HOLD", "CANCEL"},
    "CANCELED": {"REACTIVATE"},
}

WEBHOOK_EVENT_TO_STATE: dict[str, str] = {
    "invoice.paid": "ACTIVE",
    "invoice.payment_failed": "PAST_DUE",
    "googleplay.subscription.on_hold": "GRACE_PERIOD",
    "googleplay.subscription.recovered": "ACTIVE",
    "appstore.subscription.billing_retry": "GRACE_PERIOD",
    "appstore.subscription.recovered": "ACTIVE",
    "customer.subscription.deleted": "CANCELED",
    "customer.subscription.trial_will_end": "TRIAL",
    "charge.refunded": "CANCELED",
    "charge.dispute.created": "CANCELED",
}

WEBHOOK_ALLOWED_FROM_STATES: dict[str, set[Optional[str]]] = {
    "invoice.paid": {None, "TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD"},
    "invoice.payment_failed": {None, "TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD"},
    "googleplay.subscription.on_hold": {None, "TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD"},
    "googleplay.subscription.recovered": {None, "TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD"},
    "appstore.subscription.billing_retry": {None, "TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD"},
    "appstore.subscription.recovered": {None, "TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD"},
    "customer.subscription.deleted": {
        None,
        "TRIAL",
        "ACTIVE",
        "PAST_DUE",
        "GRACE_PERIOD",
        "CANCELED",
    },
    "customer.subscription.trial_will_end": {None, "TRIAL"},
    "charge.refunded": {
        None,
        "TRIAL",
        "ACTIVE",
        "PAST_DUE",
        "GRACE_PERIOD",
        "CANCELED",
    },
    "charge.dispute.created": {
        None,
        "TRIAL",
        "ACTIVE",
        "PAST_DUE",
        "GRACE_PERIOD",
        "CANCELED",
    },
}


def hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_state_change_payload_hash(*, action: str, target_plan: Optional[str]) -> str:
    normalized_payload: dict[str, str] = {"action": action}
    if target_plan is not None:
        normalized_payload["target_plan"] = target_plan

    normalized_json = json.dumps(
        normalized_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hash_payload(normalized_json.encode("utf-8"))


def require_idempotency_key_or_raise(raw_key: Optional[str]) -> str:
    cleaned_key = (raw_key or "").strip()
    if cleaned_key:
        return cleaned_key
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Idempotency-Key header is required for billing state changes.",
    )


def normalize_action_or_raise(action: str) -> str:
    normalized_action = (action or "").strip().upper()
    if not normalized_action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing action cannot be blank.",
        )
    if normalized_action not in STATE_FOR_ACTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported billing action: {normalized_action}",
        )
    return normalized_action


def normalize_target_plan_or_raise(target_plan: Optional[str]) -> Optional[str]:
    if target_plan is None:
        return None
    normalized_plan = target_plan.strip().upper()
    if not normalized_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing target_plan cannot be blank when provided.",
        )
    return normalized_plan


def resolve_next_state_or_raise(*, current_state: Optional[str], action: str) -> str:
    normalized_state = current_state.strip().upper() if current_state else None
    allowed_actions = ALLOWED_TRANSITIONS.get(normalized_state)
    if allowed_actions is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported current billing state: {current_state}",
        )
    if action not in allowed_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: state={normalized_state or 'NONE'} action={action}",
        )
    return STATE_FOR_ACTION[action]


def resolve_webhook_next_state_or_raise(
    *,
    event_type: Optional[str],
    current_state: Optional[str],
) -> Optional[str]:
    normalized_event_type = (event_type or "").strip()
    if not normalized_event_type:
        return None

    next_state = WEBHOOK_EVENT_TO_STATE.get(normalized_event_type)
    if not next_state:
        return None

    normalized_state = current_state.strip().upper() if current_state else None
    if normalized_state not in ALLOWED_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported current billing state: {current_state}",
        )

    allowed_from_states = WEBHOOK_ALLOWED_FROM_STATES.get(normalized_event_type)
    if allowed_from_states and normalized_state not in allowed_from_states:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid webhook transition: "
                f"state={normalized_state or 'NONE'} event={normalized_event_type}"
            ),
        )

    return next_state
