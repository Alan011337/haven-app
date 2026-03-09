from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import select

from app import models
from app.api.error_handling import commit_with_error_handling
from app.core.datetime_utils import utcnow
from app.core.log_redaction import redact_email
from app.middleware.request_context import mode_var, partner_id_var, request_id_var, session_id_var
from app.models.cuj_event import CujEvent
from app.models.growth_referral_event import GrowthReferralEventType
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
from app.services.events_log import (
    allow_core_loop_event_ingest,
    ensure_daily_loop_completed_for_today,
    record_core_loop_event,
)
from app.services.feature_flags import list_feature_flags_for_client
from app.services.posthog_events import capture_posthog_event
from app.services.referral_funnel import (
    normalize_invite_code,
    resolve_inviter_user_id_by_invite_code,
    track_referral_event,
)

logger = logging.getLogger(__name__)

_CUJ_METADATA_BLOCKED_KEY_FRAGMENTS = (
    "email",
    "name",
    "token",
    "password",
    "secret",
    "content",
    "journal",
    "message",
)


def _sanitize_cuj_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    if not isinstance(raw_metadata, dict):
        return sanitized

    for key, value in raw_metadata.items():
        if len(sanitized) >= 20:
            break
        if not isinstance(key, str):
            continue
        normalized_key = key.strip().lower()
        if not normalized_key:
            continue
        if any(fragment in normalized_key for fragment in _CUJ_METADATA_BLOCKED_KEY_FRAGMENTS):
            continue

        if isinstance(value, bool):
            sanitized[normalized_key] = value
            continue
        if isinstance(value, int):
            sanitized[normalized_key] = value
            continue
        if isinstance(value, float):
            sanitized[normalized_key] = round(value, 6)
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            if "@" in trimmed:
                trimmed = redact_email(trimmed)
            sanitized[normalized_key] = trimmed[:120]
    return sanitized


def _build_cuj_dedupe_key(
    *,
    user_id: uuid.UUID,
    event_name: str,
    event_id: str,
) -> str:
    raw = f"{user_id}:{event_name}:{event_id.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def handle_track_cuj_event(
    *,
    session,
    current_user: models.User,
    verified_partner_id: uuid.UUID | None,
    payload: CujEventTrackRequest,
) -> CujEventTrackResult:
    feature_payload = list_feature_flags_for_client(has_partner=verified_partner_id is not None)
    if bool(feature_payload["kill_switches"].get("disable_growth_events_ingest", False)):
        logger.info(
            "cuj_event_ingest_skipped reason=growth_events_ingest_kill_switch user_id=%s event_name=%s",
            current_user.id,
            payload.event_name.value,
        )
        return CujEventTrackResult(
            accepted=False,
            deduped=False,
            event_name=payload.event_name.value,
        )

    mode_value = payload.mode.value if payload.mode else None
    session_value = str(payload.session_id) if payload.session_id else ""
    partner_value = str(verified_partner_id) if verified_partner_id else ""

    partner_token = partner_id_var.set(partner_value)
    session_token = session_id_var.set(session_value)
    mode_token = mode_var.set(mode_value or "")
    try:
        dedupe_key = _build_cuj_dedupe_key(
            user_id=current_user.id,
            event_name=payload.event_name.value,
            event_id=payload.event_id,
        )
        existing = session.exec(select(CujEvent).where(CujEvent.dedupe_key == dedupe_key)).first()
        if existing:
            logger.info(
                (
                    "cuj_event_ingest event_name=%s source=%s user_id=%s partner_id=%s "
                    "session_id=%s mode=%s deduped=true"
                ),
                payload.event_name.value,
                payload.source,
                current_user.id,
                partner_value or "-",
                session_value or "-",
                mode_value or "-",
            )
            return CujEventTrackResult(
                accepted=True,
                deduped=True,
                event_name=payload.event_name.value,
            )

        metadata = _sanitize_cuj_metadata(payload.metadata_payload)
        now = utcnow()
        event = CujEvent(
            user_id=current_user.id,
            partner_user_id=verified_partner_id,
            event_name=payload.event_name.value,
            event_id=payload.event_id.strip(),
            source=payload.source.strip(),
            mode=mode_value,
            session_id=payload.session_id,
            occurred_at=payload.occurred_at,
            request_id=(payload.request_id and payload.request_id.strip()) or request_id_var.get() or None,
            dedupe_key=dedupe_key,
            metadata_json=json.dumps(metadata, ensure_ascii=True, sort_keys=True) if metadata else None,
            updated_at=now,
        )
        session.add(event)
        commit_with_error_handling(
            session,
            logger=logger,
            action="Track CUJ event",
            conflict_detail="CUJ event dedupe conflict, please retry.",
            failure_detail="CUJ event ingestion failed.",
        )
        logger.info(
            (
                "cuj_event_ingest event_name=%s source=%s user_id=%s partner_id=%s "
                "session_id=%s mode=%s deduped=false"
            ),
            payload.event_name.value,
            payload.source,
            current_user.id,
            partner_value or "-",
            session_value or "-",
            mode_value or "-",
        )
        return CujEventTrackResult(
            accepted=True,
            deduped=False,
            event_name=payload.event_name.value,
        )
    finally:
        mode_var.reset(mode_token)
        session_id_var.reset(session_token)
        partner_id_var.reset(partner_token)


def handle_track_core_loop_event(
    *,
    session,
    current_user: models.User,
    verified_partner_id: uuid.UUID | None,
    payload: CoreLoopEventTrackRequest,
) -> CoreLoopEventTrackResult:
    feature_payload = list_feature_flags_for_client(has_partner=verified_partner_id is not None)
    if bool(feature_payload["kill_switches"].get("disable_growth_events_ingest", False)):
        logger.info(
            "core_loop_event_ingest_skipped reason=growth_events_ingest_kill_switch user_id=%s event_name=%s",
            current_user.id,
            payload.event_name.value,
        )
        return CoreLoopEventTrackResult(
            accepted=False,
            deduped=False,
            event_name=payload.event_name.value,
            loop_completed_today=False,
        )

    partner_value = str(verified_partner_id) if verified_partner_id else ""
    session_value = (payload.session_id or "").strip()
    partner_token = partner_id_var.set(partner_value)
    session_token = session_id_var.set(session_value)
    try:
        allowed, retry_after_seconds = allow_core_loop_event_ingest(
            user_id=current_user.id,
            event_name=payload.event_name.value,
        )
        if not allowed:
            logger.info(
                (
                    "core_loop_event_ingest_skipped reason=rate_limited user_id=%s "
                    "event_name=%s retry_after_seconds=%s"
                ),
                current_user.id,
                payload.event_name.value,
                retry_after_seconds,
            )
            return CoreLoopEventTrackResult(
                accepted=False,
                deduped=False,
                event_name=payload.event_name.value,
                loop_completed_today=False,
            )
        loop_completed_today = False
        result = record_core_loop_event(
            session=session,
            user_id=current_user.id,
            partner_user_id=verified_partner_id,
            event_name=payload.event_name.value,
            event_id=payload.event_id,
            source=payload.source,
            session_id=payload.session_id,
            device_id=payload.device_id,
            occurred_at=payload.occurred_at,
            props=payload.props,
            context=payload.context,
            privacy=payload.privacy,
        )
        if payload.event_name.value != "daily_loop_completed":
            loop_completed_today = ensure_daily_loop_completed_for_today(
                session=session,
                user_id=current_user.id,
                partner_user_id=verified_partner_id,
            )
        if result.accepted and not result.deduped:
            commit_with_error_handling(
                session=session,
                logger=logger,
                action="Track core-loop event",
                conflict_detail="Core-loop event dedupe conflict, please retry.",
                failure_detail="Core-loop event ingestion failed.",
            )

        logger.info(
            (
                "core_loop_event_ingest event_name=%s source=%s user_id=%s "
                "partner_id=%s session_id=%s deduped=%s loop_completed_today=%s"
            ),
            payload.event_name.value,
            payload.source,
            current_user.id,
            partner_value or "-",
            session_value or "-",
            result.deduped,
            loop_completed_today,
        )
        if result.accepted:
            capture_posthog_event(
                event_name=payload.event_name.value,
                distinct_id=str(current_user.id),
                properties={
                    "source": payload.source,
                    "deduped": result.deduped,
                    "loop_completed_today": loop_completed_today,
                },
            )
        return CoreLoopEventTrackResult(
            accepted=result.accepted,
            deduped=result.deduped,
            event_name=payload.event_name.value,
            loop_completed_today=loop_completed_today,
        )
    finally:
        session_id_var.reset(session_token)
        partner_id_var.reset(partner_token)


def handle_track_referral_landing_view(
    *,
    session,
    payload: ReferralLandingViewTrackRequest,
) -> ReferralEventTrackResult:
    inviter_user_id = resolve_inviter_user_id_by_invite_code(
        session=session,
        invite_code=payload.invite_code,
    )
    metadata: dict[str, str] = {"event_version": "v1"}
    if payload.landing_path:
        metadata["landing_path"] = payload.landing_path

    track_result = track_referral_event(
        session=session,
        event_type=GrowthReferralEventType.LANDING_VIEW,
        invite_code=payload.invite_code,
        source=payload.source,
        inviter_user_id=inviter_user_id,
        dedupe_hint=payload.event_id,
        metadata=metadata,
    )
    if track_result.accepted and not track_result.deduped:
        commit_with_error_handling(
            session,
            logger=logger,
            action="referral_track_landing_view",
            conflict_detail="Referral event conflict. Please retry.",
            failure_detail="Referral event save failed.",
        )

    return ReferralEventTrackResult(
        accepted=track_result.accepted,
        deduped=track_result.deduped,
        event_type=GrowthReferralEventType.LANDING_VIEW.value,
    )


def handle_track_referral_signup(
    *,
    session,
    current_user: models.User,
    payload: ReferralSignupTrackRequest,
) -> ReferralEventTrackResult:
    inviter_user_id = resolve_inviter_user_id_by_invite_code(
        session=session,
        invite_code=payload.invite_code,
    )
    track_result = track_referral_event(
        session=session,
        event_type=GrowthReferralEventType.SIGNUP,
        invite_code=payload.invite_code,
        source=payload.source,
        actor_user_id=current_user.id,
        inviter_user_id=inviter_user_id,
        dedupe_hint=payload.event_id,
        metadata={"event_version": "v1"},
    )
    if track_result.accepted and not track_result.deduped:
        commit_with_error_handling(
            session,
            logger=logger,
            action="referral_track_signup",
            conflict_detail="Referral event conflict. Please retry.",
            failure_detail="Referral event save failed.",
        )

    return ReferralEventTrackResult(
        accepted=track_result.accepted,
        deduped=track_result.deduped,
        event_type=GrowthReferralEventType.SIGNUP.value,
    )


def handle_track_referral_couple_invite(
    *,
    session,
    current_user: models.User,
    payload: ReferralCoupleInviteTrackRequest,
) -> ReferralEventTrackResult:
    current_user_invite_code = normalize_invite_code(current_user.invite_code or "")
    requested_invite_code = normalize_invite_code(payload.invite_code)
    if not current_user_invite_code or current_user_invite_code != requested_invite_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invite code does not belong to current user.",
        )

    metadata: dict[str, str] = {"event_version": "v1"}
    if payload.share_channel:
        metadata["share_channel"] = payload.share_channel
    if payload.landing_path:
        metadata["landing_path"] = payload.landing_path

    track_result = track_referral_event(
        session=session,
        event_type=GrowthReferralEventType.COUPLE_INVITE,
        invite_code=payload.invite_code,
        source=payload.source,
        actor_user_id=current_user.id,
        inviter_user_id=current_user.id,
        dedupe_hint=payload.event_id,
        metadata=metadata,
    )
    if track_result.accepted and not track_result.deduped:
        commit_with_error_handling(
            session,
            logger=logger,
            action="referral_track_couple_invite",
            conflict_detail="Referral event conflict. Please retry.",
            failure_detail="Referral event save failed.",
        )

    return ReferralEventTrackResult(
        accepted=track_result.accepted,
        deduped=track_result.deduped,
        event_type=GrowthReferralEventType.COUPLE_INVITE.value,
    )
