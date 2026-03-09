from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.api.error_handling import commit_with_error_handling
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.billing import BillingCustomerBinding
from app.schemas.billing import (
    BillingEntitlementSnapshot,
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResult,
    CreatePortalSessionRequest,
    CreatePortalSessionResult,
)
from app.services.entitlement_runtime import list_entitlements

logger = logging.getLogger(__name__)
router = APIRouter()

_STRIPE_PROVIDER = "STRIPE"
_stripe_configured = False


def _ensure_stripe_configured() -> None:
    """Set Stripe API key once (thread-safe: same value always). Raises 503 if not configured."""
    global _stripe_configured
    if _stripe_configured:
        return
    import stripe  # Lazy: optional dependency

    secret = (settings.BILLING_STRIPE_SECRET_KEY or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing checkout is not configured.",
        )
    stripe.api_key = secret
    _stripe_configured = True


def _get_or_create_stripe_customer_id(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    email: str,
) -> str:
    import stripe  # Lazy: optional dependency; 503 if not installed when endpoint used

    binding = session.exec(
        select(BillingCustomerBinding).where(
            BillingCustomerBinding.provider == _STRIPE_PROVIDER,
            BillingCustomerBinding.user_id == user_id,
        )
    ).first()
    if binding and binding.provider_customer_id:
        return binding.provider_customer_id
    _ensure_stripe_configured()
    customer = stripe.Customer.create(email=email or None)
    now = utcnow()
    session.add(
        BillingCustomerBinding(
            provider=_STRIPE_PROVIDER,
            user_id=user_id,
            provider_customer_id=customer.id,
            last_event_id="checkout_create",
            last_seen_at=now,
            updated_at=now,
        )
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="Stripe customer binding create",
        conflict_detail="Billing customer create conflict. Please retry.",
        failure_detail="Billing customer create failed.",
    )
    return customer.id


@router.get("/entitlements/me", response_model=BillingEntitlementSnapshot)
def read_my_entitlements(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingEntitlementSnapshot:
    snapshot = list_entitlements(session=session, user_id=current_user.id)
    return BillingEntitlementSnapshot(
        plan=str(snapshot.get("plan") or "free"),
        quotas=dict(snapshot.get("quotas") or {}),
    )


@router.post("/create-checkout-session", response_model=CreateCheckoutSessionResult)
def create_checkout_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: CreateCheckoutSessionRequest,
) -> CreateCheckoutSessionResult:
    price_id = (payload.price_id or (settings.BILLING_STRIPE_PRICE_ID or "").strip()) or None
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No price_id provided and BILLING_STRIPE_PRICE_ID is not set.",
        )
    _ensure_stripe_configured()
    import stripe  # Lazy: optional dependency

    success_url = (payload.success_url or settings.BILLING_STRIPE_SUCCESS_URL or "").strip() or "http://localhost:3000"
    cancel_url = (payload.cancel_url or settings.BILLING_STRIPE_CANCEL_URL or "").strip() or "http://localhost:3000"
    customer_id = _get_or_create_stripe_customer_id(
        session=session,
        user_id=current_user.id,
        email=(current_user.email or "").strip() or None,
    )
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except stripe.StripeError as e:
        logger.warning(
            "Stripe checkout session create failed: %s", type(e).__name__,
            exc_info=settings.LOG_INCLUDE_STACKTRACE,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error. Please try again.",
        ) from e
    url = (checkout_session.url or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider did not return a checkout URL.",
        )
    return CreateCheckoutSessionResult(url=url)


@router.post("/create-portal-session", response_model=CreatePortalSessionResult)
def create_portal_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: CreatePortalSessionRequest,
) -> CreatePortalSessionResult:
    _ensure_stripe_configured()
    import stripe  # Lazy: optional dependency

    binding = session.exec(
        select(BillingCustomerBinding).where(
            BillingCustomerBinding.provider == _STRIPE_PROVIDER,
            BillingCustomerBinding.user_id == current_user.id,
        )
    ).first()
    if not binding or not (binding.provider_customer_id or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing customer found. Complete checkout first.",
        )
    return_url = (payload.return_url or settings.BILLING_STRIPE_PORTAL_RETURN_URL or "").strip() or "http://localhost:3000"
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=binding.provider_customer_id,
            return_url=return_url,
        )
    except stripe.StripeError as e:
        logger.warning(
            "Stripe portal session create failed: %s", type(e).__name__,
            exc_info=settings.LOG_INCLUDE_STACKTRACE,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error. Please try again.",
        ) from e
    url = (portal_session.url or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider did not return a portal URL.",
        )
    return CreatePortalSessionResult(url=url)

