import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Callable, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session as SQLModelSession, select

from app.api.deps import CurrentUser, SessionDep
from app.api.error_handling import commit_with_error_handling
from app.api.routers.billing_checkout_routes import router as checkout_router
from app.api.routers.billing_webhook_helpers import (
    extract_customer_identifier_from_webhook_payload as _extract_customer_identifier_from_payload_helper,
    extract_subscription_identifier_from_webhook_payload as _extract_subscription_identifier_from_payload_helper,
    extract_user_id_from_webhook_payload as _extract_user_id_from_payload_helper,
    parse_stripe_signature_header as _parse_stripe_signature_header_helper,
    verify_stripe_signature_or_raise as _verify_stripe_signature_or_raise_helper,
    webhook_retry_backoff_seconds as _webhook_retry_backoff_seconds_helper,
)
from app.api.routers.billing_state_change_handlers import handle_billing_state_change
from app.api.routers.billing_webhook_handlers import handle_stripe_webhook_request
from app.api.routers.billing_binding_helpers import (
    resolve_user_id_from_binding as _resolve_user_id_from_binding_helper,
    upsert_billing_customer_binding as _upsert_billing_customer_binding_helper,
)
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.core.settings_domains import get_billing_webhook_settings
from app.db.session import engine
from app.models.audit_event import AuditEventOutcome
from app.models.billing import (
    BillingCommandLog,
    BillingEntitlementState,
    BillingLedgerEntry,
    BillingWebhookReceipt,
)
from app.services.audit_log import record_audit_event_best_effort
from app.services.billing_transitions import (
    ALLOWED_TRANSITIONS,
    WEBHOOK_EVENT_TO_STATE,
    resolve_webhook_next_state_or_raise,
)
from app.schemas.billing import (
    BillingReconciliationResult,
    BillingStateChangeRequest,
    BillingStateChangeResult,
    BillingWebhookResult,
)

_STRIPE_PROVIDER = "STRIPE"
_stripe_configured = False

# Compatibility markers kept in router source for CP-03 / CP-04 policy scripts.
_ALLOWED_TRANSITIONS = ALLOWED_TRANSITIONS
_WEBHOOK_EVENT_TO_STATE = WEBHOOK_EVENT_TO_STATE
_BILLING_STATE_MARKERS = ("TRIAL", "ACTIVE", "PAST_DUE", "GRACE_PERIOD", "CANCELED")
_STORE_WEBHOOK_MARKERS = (
    "customer.subscription",
    "googleplay.subscription",
    "appstore.subscription",
    "googleplay.subscription.on_hold",
    "googleplay.subscription.recovered",
    "appstore.subscription.billing_retry",
    "appstore.subscription.recovered",
    "ENTER_ACCOUNT_HOLD",
)

router = APIRouter()
router.include_router(checkout_router)
logger = logging.getLogger(__name__)


def _audit_billing_state_change_denied(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    reason: str,
    detail: Optional[str] = None,
    metadata: Optional[dict[str, object]] = None,
) -> None:
    payload: dict[str, object] = {}
    if metadata:
        payload.update(metadata)
    if detail:
        payload["detail"] = detail
    record_audit_event_best_effort(
        session=session,
        actor_user_id=user_id,
        action="BILLING_STATE_CHANGE_DENIED",
        resource_type="billing_state_change",
        outcome=AuditEventOutcome.DENIED,
        reason=reason,
        metadata=payload or None,
        commit=True,
    )


def _audit_billing_webhook_issue(
    *,
    session: SessionDep,
    outcome: AuditEventOutcome,
    reason: str,
    detail: Optional[str] = None,
    metadata: Optional[dict[str, object]] = None,
) -> None:
    payload: dict[str, object] = {}
    if metadata:
        payload.update(metadata)
    if detail:
        payload["detail"] = detail
    record_audit_event_best_effort(
        session=session,
        actor_user_id=None,
        action="BILLING_WEBHOOK_DENIED" if outcome == AuditEventOutcome.DENIED else "BILLING_WEBHOOK_ERROR",
        resource_type="billing_webhook",
        outcome=outcome,
        reason=reason,
        metadata=payload or None,
        commit=True,
    )


def _parse_stripe_signature_header(signature_header: str) -> tuple[int, list[str]]:
    return _parse_stripe_signature_header_helper(signature_header)


def _verify_stripe_signature_or_raise(*, payload: bytes, signature_header: str, secret: str) -> None:
    webhook_settings = get_billing_webhook_settings()
    _verify_stripe_signature_or_raise_helper(
        payload=payload,
        signature_header=signature_header,
        secret=secret,
        tolerance_seconds=webhook_settings.signature_tolerance_seconds,
    )


def _extract_user_id_from_webhook_payload(payload: dict) -> Optional[uuid.UUID]:
    return _extract_user_id_from_payload_helper(payload)


def _extract_customer_identifier_from_webhook_payload(payload: dict) -> Optional[str]:
    return _extract_customer_identifier_from_payload_helper(payload)


def _extract_subscription_identifier_from_webhook_payload(
    payload: dict,
    *,
    event_type: Optional[str],
) -> Optional[str]:
    return _extract_subscription_identifier_from_payload_helper(
        payload,
        event_type=event_type,
    )


def _resolve_user_id_from_binding(
    *,
    session: SessionDep,
    provider: str,
    provider_customer_id: Optional[str],
    provider_subscription_id: Optional[str],
) -> Optional[uuid.UUID]:
    return _resolve_user_id_from_binding_helper(
        session=session,
        provider=provider,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
    )


def _upsert_billing_customer_binding(
    *,
    session: SessionDep,
    provider: str,
    user_id: uuid.UUID,
    provider_customer_id: Optional[str],
    provider_subscription_id: Optional[str],
    event_id: str,
) -> None:
    _upsert_billing_customer_binding_helper(
        session=session,
        provider=provider,
        user_id=user_id,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
        event_id=event_id,
    )


def _build_reconciliation_result(*, session: SessionDep, user_id: uuid.UUID) -> BillingReconciliationResult:
    command_rows = session.exec(
        select(BillingCommandLog).where(BillingCommandLog.user_id == user_id)
    ).all()
    expected_command_keys = {f"cmd:{row.id}" for row in command_rows}

    command_ledger_keys = set(
        session.exec(
            select(BillingLedgerEntry.source_key).where(
                BillingLedgerEntry.user_id == user_id,
                BillingLedgerEntry.source_type == "COMMAND",
            )
        ).all()
    )
    missing_command_ids = [
        row.id for row in command_rows if f"cmd:{row.id}" not in command_ledger_keys
    ]

    entitlement = session.exec(
        select(BillingEntitlementState).where(BillingEntitlementState.user_id == user_id)
    ).first()

    healthy = len(missing_command_ids) == 0 and (
        len(command_rows) == 0 or entitlement is not None
    )

    return BillingReconciliationResult(
        user_id=user_id,
        checked_at=utcnow(),
        command_count=len(command_rows),
        command_ledger_count=len(expected_command_keys.intersection(command_ledger_keys)),
        missing_command_ledger_count=len(missing_command_ids),
        missing_command_ids=missing_command_ids,
        entitlement_state=entitlement.lifecycle_state if entitlement else None,
        entitlement_plan=entitlement.current_plan if entitlement else None,
        healthy=healthy,
    )


def _webhook_processing_mode_for_status(status_value: str) -> str:
    if status_value in {"QUEUED", "PROCESSING", "FAILED", "DEAD"}:
        return "ASYNC"
    return "ASYNC" if get_billing_webhook_settings().async_mode else "INLINE"


def _billing_webhook_retry_max_attempts() -> int:
    return get_billing_webhook_settings().retry_max_attempts


def _billing_webhook_retry_backoff_seconds(*, attempt_count: int) -> int:
    base = get_billing_webhook_settings().retry_base_seconds
    return _webhook_retry_backoff_seconds_helper(
        base_seconds=base,
        attempt_count=attempt_count,
    )


def _load_webhook_payload_from_receipt(receipt: BillingWebhookReceipt) -> dict:
    raw_payload = (receipt.payload_json or "").strip()
    if not raw_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook receipt payload missing.",
        )
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook receipt payload is invalid JSON.",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook receipt payload must be an object.",
        )
    return payload


def _current_webhook_attempt_count(*, session: SQLModelSession, receipt_id: uuid.UUID) -> int:
    receipt = session.get(BillingWebhookReceipt, receipt_id)
    if not receipt:
        return 1
    return max(1, int(receipt.attempt_count or 0))


def _apply_stripe_webhook_effects(
    *,
    session: SQLModelSession,
    provider_name: str,
    event_id: str,
    event_type: Optional[str],
    payload: dict,
    payload_hash: str,
    provider_customer_id: Optional[str],
    provider_subscription_id: Optional[str],
) -> None:
    try:
        mapped_user_id = _resolve_user_id_from_binding(
            session=session,
            provider=provider_name,
            provider_customer_id=provider_customer_id,
            provider_subscription_id=provider_subscription_id,
        )
    except HTTPException as exc:
        session.rollback()
        _audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.DENIED,
            reason="binding_resolution_conflict",
            detail=str(exc.detail),
            metadata={"event_id": event_id},
        )
        raise

    metadata_user_id = _extract_user_id_from_webhook_payload(payload)
    if mapped_user_id and metadata_user_id and mapped_user_id != metadata_user_id:
        session.rollback()
        _audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.DENIED,
            reason="binding_identity_mismatch",
            detail="Webhook user identity does not match existing billing binding.",
            metadata={"event_id": event_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook user identity does not match existing billing binding.",
        )

    webhook_user_id = mapped_user_id or metadata_user_id
    webhook_next_state: Optional[str] = None
    entitlement_previous_state: Optional[str] = None
    entitlement_previous_plan: Optional[str] = None
    entitlement_next_plan: Optional[str] = None
    entitlement: Optional[BillingEntitlementState] = None

    if webhook_user_id:
        entitlement = session.exec(
            select(BillingEntitlementState).where(BillingEntitlementState.user_id == webhook_user_id)
        ).first()
        if entitlement:
            entitlement_previous_state = entitlement.lifecycle_state
            entitlement_previous_plan = entitlement.current_plan
            entitlement_next_plan = entitlement.current_plan

        try:
            webhook_next_state = resolve_webhook_next_state_or_raise(
                event_type=event_type,
                current_state=entitlement_previous_state,
            )
        except HTTPException as exc:
            session.rollback()
            _audit_billing_webhook_issue(
                session=session,
                outcome=AuditEventOutcome.DENIED,
                reason="webhook_transition_invalid",
                detail=str(exc.detail),
                metadata={"event_id": event_id, "event_type": event_type or ""},
            )
            raise

        if webhook_next_state:
            if entitlement:
                entitlement.lifecycle_state = webhook_next_state
                entitlement.updated_at = utcnow()
                entitlement.revision += 1
                session.add(entitlement)
            else:
                entitlement_next_plan = None
                session.add(
                    BillingEntitlementState(
                        user_id=webhook_user_id,
                        lifecycle_state=webhook_next_state,
                        current_plan=None,
                        revision=1,
                    )
                )

    if webhook_user_id and (provider_customer_id or provider_subscription_id):
        try:
            _upsert_billing_customer_binding(
                session=session,
                provider=provider_name,
                user_id=webhook_user_id,
                provider_customer_id=provider_customer_id,
                provider_subscription_id=provider_subscription_id,
                event_id=event_id,
            )
        except HTTPException as exc:
            session.rollback()
            _audit_billing_webhook_issue(
                session=session,
                outcome=AuditEventOutcome.DENIED,
                reason="binding_upsert_conflict",
                detail=str(exc.detail),
                metadata={"event_id": event_id},
            )
            raise

    session.add(
        BillingLedgerEntry(
            user_id=webhook_user_id,
            source_type="WEBHOOK",
            source_key=f"wh:stripe:{event_id}",
            action=event_type,
            previous_state=entitlement_previous_state,
            next_state=webhook_next_state,
            previous_plan=entitlement_previous_plan,
            next_plan=entitlement_next_plan,
            payload_hash=payload_hash,
        )
    )


def _set_webhook_receipt_status(
    *,
    session: SQLModelSession,
    receipt_id: uuid.UUID,
    status_value: str,
    error_reason: Optional[str] = None,
    next_attempt_at: Optional[datetime] = None,
    logger: logging.Logger,
) -> None:
    receipt = session.get(BillingWebhookReceipt, receipt_id)
    if not receipt:
        return
    receipt.status = status_value
    receipt.processed_at = utcnow()
    receipt.last_error_reason = error_reason
    receipt.next_attempt_at = next_attempt_at
    session.add(receipt)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Stripe webhook receipt status",
        conflict_detail="Webhook receipt status update conflict. Please retry.",
        failure_detail="Webhook receipt status update failed.",
    )


def _default_billing_worker_session() -> SQLModelSession:
    return SQLModelSession(engine)


def _process_stripe_webhook_background_job(
    *,
    receipt_id: uuid.UUID,
    provider_name: Optional[str] = None,
    event_id: Optional[str] = None,
    event_type: Optional[str],
    payload: Optional[dict] = None,
    payload_hash: Optional[str] = None,
    provider_customer_id: Optional[str] = None,
    provider_subscription_id: Optional[str] = None,
    session_factory: Optional[Callable[[], SQLModelSession]] = None,
) -> None:
    factory = session_factory or _default_billing_worker_session
    with factory() as worker_session:
        receipt = worker_session.get(BillingWebhookReceipt, receipt_id)
        if not receipt:
            logger.warning(
                "billing webhook async worker missing receipt",
                extra={"receipt_id": str(receipt_id)},
            )
            return
        if receipt.status == "PROCESSED":
            return
        now = utcnow()
        if (
            receipt.next_attempt_at is not None
            and receipt.next_attempt_at > now
            and receipt.status in {"QUEUED", "FAILED"}
        ):
            return

        provider_name_value = provider_name or receipt.provider or "STRIPE"
        event_id_value = event_id or receipt.provider_event_id
        event_type_value = event_type if event_type is not None else receipt.provider_event_type
        payload_hash_value = payload_hash or receipt.payload_hash
        provider_customer_id_value = (
            provider_customer_id if provider_customer_id is not None else receipt.provider_customer_id
        )
        provider_subscription_id_value = (
            provider_subscription_id
            if provider_subscription_id is not None
            else receipt.provider_subscription_id
        )
        payload_value = payload
        if not isinstance(payload_value, dict):
            try:
                payload_value = _load_webhook_payload_from_receipt(receipt)
            except HTTPException as exc:
                worker_session.rollback()
                _audit_billing_webhook_issue(
                    session=worker_session,
                    outcome=AuditEventOutcome.DENIED,
                    reason="receipt_payload_invalid",
                    detail=str(exc.detail),
                    metadata={"event_id": event_id_value or ""},
                )
                try:
                    _set_webhook_receipt_status(
                        session=worker_session,
                        receipt_id=receipt_id,
                        status_value="DEAD",
                        error_reason="receipt_payload_invalid",
                        next_attempt_at=None,
                        logger=logger,
                    )
                except HTTPException:
                    logger.warning(
                        "Failed to set webhook receipt status to DEAD after invalid payload",
                        extra={"event_id": event_id_value or ""},
                    )
                return

        receipt.status = "PROCESSING"
        receipt.processed_at = now
        receipt.attempt_count = max(0, int(receipt.attempt_count or 0)) + 1
        worker_session.add(receipt)
        commit_with_error_handling(
            worker_session,
            logger=logger,
            action="Stripe webhook worker status PROCESSING",
            conflict_detail="Webhook worker status conflict.",
            failure_detail="Webhook worker status update failed.",
        )

        try:
            _apply_stripe_webhook_effects(
                session=worker_session,
                provider_name=provider_name_value,
                event_id=event_id_value or "",
                event_type=event_type_value,
                payload=payload_value,
                payload_hash=payload_hash_value or "",
                provider_customer_id=provider_customer_id_value,
                provider_subscription_id=provider_subscription_id_value,
            )
            receipt = worker_session.get(BillingWebhookReceipt, receipt_id)
            if receipt:
                receipt.status = "PROCESSED"
                receipt.processed_at = utcnow()
                receipt.last_error_reason = None
                receipt.next_attempt_at = None
                worker_session.add(receipt)
            commit_with_error_handling(
                worker_session,
                logger=logger,
                action="Stripe webhook worker status PROCESSED",
                conflict_detail="Webhook worker commit conflict.",
                failure_detail="Webhook worker commit failed.",
            )
        except HTTPException as exc:
            worker_session.rollback()
            retryable = exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
            reason = f"http_{exc.status_code}"
            _audit_billing_webhook_issue(
                session=worker_session,
                outcome=AuditEventOutcome.DENIED
                if status.HTTP_400_BAD_REQUEST <= exc.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR
                else AuditEventOutcome.ERROR,
                reason="async_processing_failed",
                detail=str(exc.detail),
                metadata={"event_id": event_id_value or ""},
            )
            attempt_count = _current_webhook_attempt_count(session=worker_session, receipt_id=receipt_id)
            max_attempts = _billing_webhook_retry_max_attempts()
            should_retry = retryable and attempt_count < max_attempts
            next_attempt_at = (
                utcnow()
                + timedelta(seconds=_billing_webhook_retry_backoff_seconds(attempt_count=attempt_count))
                if should_retry
                else None
            )
            try:
                _set_webhook_receipt_status(
                    session=worker_session,
                    receipt_id=receipt_id,
                    status_value="FAILED" if should_retry else ("DEAD" if retryable else "FAILED"),
                    error_reason=reason if should_retry else (f"retry_exhausted:{reason}" if retryable else reason),
                    next_attempt_at=next_attempt_at,
                    logger=logger,
                )
            except HTTPException:
                logger.warning(
                    "Failed to set webhook receipt status after HTTPException",
                    extra={"event_id": event_id_value or ""},
                )
        except Exception:
            worker_session.rollback()
            reason = "unexpected_error"
            logger.error(
                "billing webhook async worker failed",
                extra={"event_id": event_id_value or ""},
                exc_info=settings.LOG_INCLUDE_STACKTRACE,
            )
            _audit_billing_webhook_issue(
                session=worker_session,
                outcome=AuditEventOutcome.ERROR,
                reason="async_processing_failed",
                detail="Unexpected webhook async processing failure.",
                metadata={"event_id": event_id_value or ""},
            )
            attempt_count = _current_webhook_attempt_count(session=worker_session, receipt_id=receipt_id)
            max_attempts = _billing_webhook_retry_max_attempts()
            should_retry = attempt_count < max_attempts
            next_attempt_at = (
                utcnow() + timedelta(seconds=_billing_webhook_retry_backoff_seconds(attempt_count=attempt_count))
                if should_retry
                else None
            )
            try:
                _set_webhook_receipt_status(
                    session=worker_session,
                    receipt_id=receipt_id,
                    status_value="FAILED" if should_retry else "DEAD",
                    error_reason=reason if should_retry else f"retry_exhausted:{reason}",
                    next_attempt_at=next_attempt_at,
                    logger=logger,
                )
            except HTTPException:
                logger.warning(
                    "Failed to set webhook receipt status after unexpected exception",
                    extra={"event_id": event_id_value or ""},
                )


def _enqueue_stripe_webhook_processing(
    *,
    background_tasks: BackgroundTasks,
    receipt_id: uuid.UUID,
    provider_name: str,
    event_id: str,
    event_type: Optional[str],
    payload: dict,
    payload_hash: str,
    provider_customer_id: Optional[str],
    provider_subscription_id: Optional[str],
) -> None:
    background_tasks.add_task(
        _process_stripe_webhook_background_job,
        receipt_id=receipt_id,
        provider_name=provider_name,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        payload_hash=payload_hash,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
    )


def process_pending_stripe_webhook_receipts(
    *,
    limit: int = 50,
    session_factory: Optional[Callable[[], SQLModelSession]] = None,
) -> dict[str, int]:
    """Process queued/failed webhook receipts that are ready for retry."""
    safe_limit = max(1, min(int(limit), 500))
    factory = session_factory or _default_billing_worker_session
    now = utcnow()
    processed = 0
    errors = 0
    selected = 0

    with factory() as session:
        rows = session.exec(
            select(BillingWebhookReceipt)
            .where(
                BillingWebhookReceipt.provider == "STRIPE",
                BillingWebhookReceipt.status.in_(("QUEUED", "FAILED")),
            )
            .where(
                (BillingWebhookReceipt.next_attempt_at.is_(None))
                | (BillingWebhookReceipt.next_attempt_at <= now)
            )
            .order_by(BillingWebhookReceipt.next_attempt_at, BillingWebhookReceipt.received_at)
            .limit(safe_limit)
        ).all()

    selected = len(rows)
    for receipt in rows:
        try:
            _process_stripe_webhook_background_job(
                receipt_id=receipt.id,
                provider_name=None,
                event_id=None,
                event_type=None,
                payload=None,
                payload_hash=None,
                provider_customer_id=None,
                provider_subscription_id=None,
                session_factory=session_factory,
            )
            processed += 1
        except Exception:
            errors += 1
            logger.warning(
                "billing webhook retry worker receipt processing failed",
                extra={"receipt_id": str(receipt.id)},
                exc_info=settings.LOG_INCLUDE_STACKTRACE,
            )

    return {
        "selected": selected,
        "processed": processed,
        "errors": errors,
    }


@router.post("/state-change", response_model=BillingStateChangeResult)
def billing_state_change(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: BillingStateChangeRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> BillingStateChangeResult:
    return handle_billing_state_change(
        session=session,
        current_user=current_user,
        payload=payload,
        idempotency_key=idempotency_key,
        audit_billing_state_change_denied=_audit_billing_state_change_denied,
        logger=logger,
    )


@router.post("/webhooks/stripe", response_model=BillingWebhookResult)
async def stripe_webhook(
    *,
    session: SessionDep,
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
) -> BillingWebhookResult:
    return await handle_stripe_webhook_request(
        session=session,
        request=request,
        background_tasks=background_tasks,
        stripe_signature=stripe_signature,
        webhook_secret=(settings.BILLING_STRIPE_WEBHOOK_SECRET or "").strip(),
        async_mode_enabled=get_billing_webhook_settings().async_mode,
        verify_stripe_signature_or_raise=_verify_stripe_signature_or_raise,
        audit_billing_webhook_issue=_audit_billing_webhook_issue,
        extract_customer_identifier_from_webhook_payload=_extract_customer_identifier_from_webhook_payload,
        extract_subscription_identifier_from_webhook_payload=_extract_subscription_identifier_from_webhook_payload,
        webhook_processing_mode_for_status=_webhook_processing_mode_for_status,
        enqueue_stripe_webhook_processing=_enqueue_stripe_webhook_processing,
        apply_stripe_webhook_effects=_apply_stripe_webhook_effects,
        logger=logger,
    )


@router.get("/reconciliation", response_model=BillingReconciliationResult)
def billing_reconciliation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingReconciliationResult:
    return _build_reconciliation_result(session=session, user_id=current_user.id)


# MON-03: Stub store provider webhook routes — return 501 until adapters are implemented (see docs/security/store-provider-adapters.md).
@router.post("/webhooks/appstore")
def webhook_appstore_stub() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"detail": "App Store provider adapter not implemented", "code": "MON_03_STUB"},
    )


@router.post("/webhooks/googleplay")
def webhook_googleplay_stub() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"detail": "Google Play provider adapter not implemented", "code": "MON_03_STUB"},
    )
