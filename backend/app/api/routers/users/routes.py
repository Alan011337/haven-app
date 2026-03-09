# backend/app/api/routers/users/routes.py

import uuid
import secrets
import logging
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, status
from sqlmodel import SQLModel, select, func

from app import models
from app.core.security import get_password_hash
from app.core.config import settings
from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.schemas.user import (
    DataEraseResult,
    DataExportPackagePublic,
    InviteCodeResponse,
    PairingRequest,
    UserCreate,
    UserPublic,
)
from app.models.journal import Journal # 確保引入 Journal
from app.models.notification_event import NotificationEvent
from app.models.growth_referral_event import GrowthReferralEventType
from app.core.datetime_utils import utcnow
from app.services.notification import (
    is_email_notification_enabled as _service_is_email_notification_enabled,
    queue_partner_notification,
)
from app.services.notification_payloads import build_partner_notification_payload
from app.services.referral_funnel import (
    track_referral_event,
)
from app.services.abuse_state_store_factory import create_abuse_state_store
from app.services.pairing_abuse_guard import PairingAbuseGuard
from app.services.rate_limit import enforce_registration_rate_limit
from app.services.rate_limit_runtime_metrics import rate_limit_runtime_metrics
from app.services.request_identity import resolve_client_ip
from app.services.audit_log import record_audit_event, record_audit_event_best_effort
from app.services.alpha_allowlist import enforce_alpha_allowlist_or_raise
from app.services.cuj_event_emitter import emit_cuj_event
from app.services.cuj_sli_runtime import EVENT_BIND_START, EVENT_BIND_SUCCESS
from app.services.posthog_events import capture_posthog_event
from app.api.routers.users.events_routes import router as events_router
from app.api.routers.users.growth_routes import router as growth_router
from app.api.routers.users.notification_routes import router as notification_router
from app.api.routers.users.data_consent_handlers import (
    handle_create_consent_receipt,
    handle_erase_my_data,
    handle_export_my_data,
    handle_get_my_onboarding_consent,
    handle_list_my_consents,
    handle_upsert_my_onboarding_consent,
)
from app.models.audit_event import AuditEventOutcome
from app.schemas.consent_receipt import ConsentReceiptCreate, ConsentReceiptPublic
from app.schemas.user_onboarding_consent import (
    UserOnboardingConsentCreate,
    UserOnboardingConsentPublic,
)
from app.core.log_redaction import redact_ip

router = APIRouter()
logger = logging.getLogger(__name__)

DATA_EXPORT_SECTION_KEYS: tuple[str, ...] = (
    "user",
    "journals",
    "analyses",
    "card_responses",
    "card_sessions",
    "notification_events",
)
DATA_ERASE_COUNT_KEYS: tuple[str, ...] = (
    "analyses",
    "journals",
    "card_responses",
    "card_sessions",
    "notification_events",
    "users",
)
# Contract marker for data-deletion lifecycle policy checks.
DATA_DELETION_AUDIT_ACTION_MARKERS: tuple[str, ...] = (
    "USER_DATA_ERASE",
    "USER_DATA_ERASE_ERROR",
)

pairing_abuse_guard = PairingAbuseGuard(
    limit_count=settings.PAIRING_ATTEMPT_RATE_LIMIT_COUNT,
    window_seconds=settings.PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS,
    failure_threshold=settings.PAIRING_FAILURE_COOLDOWN_THRESHOLD,
    cooldown_seconds=settings.PAIRING_FAILURE_COOLDOWN_SECONDS,
    state_store=create_abuse_state_store(scope="pairing-user"),
)
pairing_ip_abuse_guard = PairingAbuseGuard(
    limit_count=settings.PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT,
    window_seconds=settings.PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS,
    failure_threshold=settings.PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD,
    cooldown_seconds=settings.PAIRING_IP_FAILURE_COOLDOWN_SECONDS,
    state_store=create_abuse_state_store(scope="pairing-ip"),
)


def is_email_notification_enabled() -> bool:
    """Compatibility shim for route-level patching in tests and retry path."""
    return _service_is_email_notification_enabled()


def _require_self_or_partner_access(
    *,
    session: SessionDep,
    current_user: models.User,
    target_user_id: uuid.UUID,
) -> None:
    if target_user_id == current_user.id:
        return
    if current_user.partner_id and target_user_id == current_user.partner_id:
        return
    record_audit_event_best_effort(
        session=session,
        actor_user_id=current_user.id,
        target_user_id=target_user_id,
        action="USER_READ_DENIED",
        resource_type="user",
        resource_id=target_user_id,
        outcome=AuditEventOutcome.DENIED,
        reason="not_self_or_partner",
        commit=True,
    )
    capture_posthog_event(
        event_name="authz_denied_object_level",
        distinct_id=str(current_user.id),
        properties={
            "resource_type": "user",
            "auth_stage": "read_user_profile",
        },
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not allowed to access this user.",
    )


def _resolve_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _build_user_public(*, session: SessionDep, current_user: CurrentUser) -> UserPublic:
    user_data = UserPublic.model_validate(current_user)
    if current_user.partner_id:
        partner = session.get(models.User, current_user.partner_id)
        if partner and partner.partner_id == current_user.id:
            user_data.partner_name = partner.full_name or partner.email.split("@")[0]
            user_data.mode = "paired"
        else:
            user_data.mode = "solo"
    else:
        user_data.mode = "solo"
    return user_data

# ==========================================
# 1. 取得當前使用者 (含伴侶名字邏輯)
# ==========================================
@router.get("/me", response_model=UserPublic)
def read_user_me(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    return _build_user_public(session=session, current_user=current_user)


class MeUpdateBody(SQLModel):
    """PATCH /me: allow updating profile fields (LEGAL-02 legacy_contact_email)."""
    full_name: Optional[str] = None
    legacy_contact_email: Optional[str] = None


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    session: SessionDep,
    current_user: CurrentUser,
    body: MeUpdateBody,
) -> Any:
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.legacy_contact_email is not None:
        current_user.legacy_contact_email = body.legacy_contact_email.strip() or None
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return _build_user_public(session=session, current_user=current_user)


@router.get("/me/data-export", response_model=DataExportPackagePublic)
def export_my_data(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> DataExportPackagePublic:
    return handle_export_my_data(
        session=session,
        current_user=current_user,
        build_user_public=_build_user_public,
    )


@router.delete("/me/data", response_model=DataEraseResult)
def erase_my_data(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> DataEraseResult:
    return handle_erase_my_data(
        session=session,
        current_user=current_user,
        logger=logger,
        commit_with_error_handling_fn=commit_with_error_handling,
    )


@router.get("/me/consents", response_model=list[ConsentReceiptPublic])
def list_my_consents(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[ConsentReceiptPublic]:
    return handle_list_my_consents(
        session=session,
        current_user=current_user,
    )


@router.post("/me/consents", response_model=ConsentReceiptPublic, status_code=status.HTTP_201_CREATED)
def create_consent_receipt(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    consent_in: ConsentReceiptCreate,
    request: Request,
) -> ConsentReceiptPublic:
    return handle_create_consent_receipt(
        session=session,
        current_user=current_user,
        consent_in=consent_in,
        request=request,
        logger=logger,
        resolve_client_ip=_resolve_client_ip,
    )


# --- Module A1: Onboarding consent (privacy scope, notification frequency, AI intensity) ---
@router.get("/me/onboarding-consent", response_model=UserOnboardingConsentPublic | None)
def get_my_onboarding_consent(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserOnboardingConsentPublic | None:
    return handle_get_my_onboarding_consent(
        session=session,
        current_user=current_user,
    )


@router.post("/me/onboarding-consent", response_model=UserOnboardingConsentPublic)
def upsert_my_onboarding_consent(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: UserOnboardingConsentCreate,
) -> UserOnboardingConsentPublic:
    return handle_upsert_my_onboarding_consent(
        session=session,
        current_user=current_user,
        body=body,
        logger=logger,
    )


# ==========================================
# 2. 註冊使用者
# ==========================================
@router.post("/", response_model=UserPublic)
def create_user(request: Request, user: UserCreate, session: SessionDep):
    # --- 年齡閘門驗證 (AGE-01) ---
    if not user.agreed_to_terms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="必須同意服務條款才能註冊",
        )
    if user.birth_year is not None:
        current_year = utcnow().year
        age = current_year - user.birth_year
        if age < 18:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="必須年滿 18 歲才能使用本服務",
            )
    enforce_alpha_allowlist_or_raise(email=user.email, auth_stage="register")

    statement = select(models.User).where(models.User.email == user.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # --- 註冊 rate limit (IP-based, abuse protection) ---
    client_ip = resolve_client_ip(request)
    enforce_registration_rate_limit(
        client_ip=client_ip,
        ip_limit_count=settings.REGISTRATION_RATE_LIMIT_IP_COUNT,
        ip_window_seconds=settings.REGISTRATION_RATE_LIMIT_IP_WINDOW_SECONDS,
    )

    if not user.age_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age confirmation is required.",
        )
    if not user.terms_version.strip() or not user.privacy_version.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent versions are required.",
        )

    now = utcnow()
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        terms_accepted_at=now,
        birth_year=user.birth_year,
    )
    session.add(db_user)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Create user",
        conflict_detail="Email already registered",
        failure_detail="Unable to create user.",
    )
    session.refresh(db_user)
    record_audit_event_best_effort(
        session=session,
        actor_user_id=db_user.id,
        target_user_id=db_user.id,
        action="USER_CONSENT_ACK",
        resource_type="user",
        resource_id=db_user.id,
        outcome=AuditEventOutcome.SUCCESS,
        metadata={
            "age_confirmed": bool(user.age_confirmed),
            "terms_version": user.terms_version,
            "privacy_version": user.privacy_version,
            "accepted_at_iso8601": utcnow().isoformat() + "Z",
        },
        commit=True,
    )
    capture_posthog_event(
        event_name="signup_completed",
        distinct_id=str(db_user.id),
        properties={"auth_stage": "register"},
    )
    return db_user

# ==========================================
# 3. 產生邀請碼
# ==========================================
@router.post("/invite-code", response_model=InviteCodeResponse)
def generate_invite_code(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    code = secrets.token_hex(3).upper() 
    current_user.invite_code = code
    current_user.invite_code_created_at = utcnow()
    session.add(current_user)
    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        action="USER_INVITE_CODE_GENERATE",
        resource_type="user",
        resource_id=current_user.id,
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="Generate invite code",
        conflict_detail="Invite code conflict. Please try again.",
        failure_detail="Unable to generate invite code.",
    )
    session.refresh(current_user)
    return InviteCodeResponse(
        code=current_user.invite_code, 
        expires_at=current_user.invite_code_created_at + timedelta(hours=24)
    )

# ==========================================
# 4. 配對 API
# ==========================================
@router.post("/pair", response_model=UserPublic)
def pair_with_partner(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    pairing_in: PairingRequest,
    request: Request,
) -> Any:
    invite_code = pairing_in.invite_code.strip().upper()

    if current_user.partner_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already paired.",
        )

    client_ip = _resolve_client_ip(request)
    guard_entries = [
        ("user", pairing_abuse_guard, f"user:{current_user.id}:ip:{client_ip}"),
        ("ip", pairing_ip_abuse_guard, f"ip:{client_ip}"),
    ]
    blocked_reasons: list[str] = []
    blocked_retry_after: list[int] = []
    blocked_scopes: list[str] = []
    for scope_name, guard, guard_key in guard_entries:
        allowed, reason, retry_after_seconds = guard.allow_attempt(key=guard_key)
        if allowed:
            continue
        blocked_reasons.append(str(reason or "rate_limited"))
        blocked_retry_after.append(max(1, int(retry_after_seconds)))
        blocked_scopes.append(scope_name)

    if blocked_reasons:
        for blocked_scope in blocked_scopes:
            rate_limit_runtime_metrics.record_blocked(
                scope=blocked_scope,
                action="pairing_attempt",
                endpoint="/api/users/pair",
            )
        retry_after_seconds = max(blocked_retry_after) if blocked_retry_after else 1
        if "cooldown_active" in blocked_reasons:
            detail = (
                "Pairing attempts are temporarily locked due to repeated failures. "
                f"Please retry in {retry_after_seconds} seconds."
            )
        else:
            detail = f"Too many pairing attempts. Please retry in {retry_after_seconds} seconds."
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after_seconds)},
        )

    def _reject_pairing(detail: str, *, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        for _, guard, guard_key in guard_entries:
            guard.record_attempt(key=guard_key, success=False)
        raise HTTPException(status_code=status_code, detail=detail)

    # CUJ SLI: track bind start
    emit_cuj_event(
        session=session,
        user_id=current_user.id,
        event_name=EVENT_BIND_START,
        source="server",
    )

    if not invite_code:
        _reject_pairing("Invite code is required.")

    if current_user.invite_code and invite_code == current_user.invite_code:
        _reject_pairing("You cannot pair with yourself.")

    statement = select(models.User).where(models.User.invite_code == invite_code)
    partner = session.exec(statement).first()
    
    if not partner:
        _reject_pairing("Invalid or expired invite code.")

    if partner.id == current_user.id:
        _reject_pairing("You cannot pair with yourself.")

    if partner.partner_id and partner.partner_id != current_user.id:
        _reject_pairing("This user is already paired.", status_code=status.HTTP_409_CONFLICT)

    if partner.invite_code_created_at:
        expiry_time = partner.invite_code_created_at + timedelta(hours=24)
        if utcnow() > expiry_time:
            _reject_pairing("Invalid or expired invite code.")

    current_user.partner_id = partner.id
    partner.partner_id = current_user.id
    current_user.invite_code = None
    partner.invite_code = None
    current_user.invite_code_created_at = None
    partner.invite_code_created_at = None
    session.add(current_user)
    session.add(partner)
    try:
        track_referral_event(
            session=session,
            event_type=GrowthReferralEventType.BIND,
            invite_code=invite_code,
            source="pair_api",
            actor_user_id=current_user.id,
            inviter_user_id=partner.id,
            metadata={"event_version": "v1"},
        )
    except Exception:
        logger.exception("referral_bind_tracking_failed")
    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        target_user_id=partner.id,
        action="USER_PAIR",
        resource_type="user_pairing",
        resource_id=partner.id,
        metadata={"client_ip": redact_ip(client_ip)},
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="Pair users",
        conflict_detail="Pairing conflict. Please retry.",
        failure_detail="Pairing failed.",
    )
    session.refresh(current_user)
    for _, guard, guard_key in guard_entries:
        guard.record_attempt(key=guard_key, success=True)

    # CUJ SLI: track bind success
    emit_cuj_event(
        session=session,
        user_id=current_user.id,
        event_name=EVENT_BIND_SUCCESS,
        source="server",
        partner_user_id=partner.id,
    )

    # P1-C-MULTI-CHANNEL: notify partner of bind (partner_bound trigger)
    try:
        payload = build_partner_notification_payload(
            session=session,
            sender_user=current_user,
            event_type="partner_bound",
            scope_id=f"pair:{current_user.id}:{partner.id}",
            partner_user_id=partner.id,
        )
        if payload:
            queue_partner_notification(
                action_type="partner_bound",
                event_type="partner_bound",
                **payload,
            )
    except Exception:
        logger.exception("partner_bound_notification_failed")

    capture_posthog_event(
        event_name="partner_linked",
        distinct_id=str(current_user.id),
        properties={"source": "pair_api"},
    )

    return current_user

# ==========================================
# 5. 檢查伴侶狀態 (Poling API)
# ⚠️ 注意：這必須放在 `/{user_id}` 之前，否則會被攔截
# ==========================================
@router.get("/partner-status")
def get_partner_status(
    session: SessionDep,
    current_user: CurrentUser
):
    """
    讓前端輪詢：檢查伴侶是否有新動態
    """
    unread_notification_count = int(
        session.exec(
            select(func.count(NotificationEvent.id)).where(
                NotificationEvent.receiver_user_id == current_user.id,
                NotificationEvent.is_read.is_(False),
                NotificationEvent.deleted_at.is_(None),
            )
        ).one()
        or 0
    )

    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    if not verified_pid:
        return {
            "has_partner": False,
            "latest_journal_at": None,
            "current_score": current_user.savings_score,
            "unread_notification_count": unread_notification_count,
        }

    # 查詢伴侶最新的一篇日記時間（雙向驗證後）
    statement = (
        select(Journal.created_at)
        .where(Journal.user_id == verified_pid)
        .where(Journal.deleted_at.is_(None))
        .order_by(Journal.created_at.desc())
        .limit(1)
    )
    latest_date = session.exec(statement).first()

    return {
        "has_partner": True,
        "latest_journal_at": latest_date, 
        "current_score": current_user.savings_score,
        "unread_notification_count": unread_notification_count,
    }


# Split growth and events/referrals routes into dedicated modules to keep this
# file focused on user profile/pairing/notification APIs.
router.include_router(growth_router)
router.include_router(events_router)
router.include_router(notification_router)


# ==========================================
# 6. 讀取特定使用者 (動態路由放最後)
# ==========================================
@router.get("/{user_id}", response_model=UserPublic)
def read_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    _require_self_or_partner_access(
        session=session,
        current_user=current_user,
        target_user_id=user_id,
    )
    db_user = session.get(models.User, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user
