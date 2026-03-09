from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.growth_referral_event import GrowthReferralEvent, GrowthReferralEventType
from app.models.user import User
from app.services.feature_flags import resolve_feature_flags

logger = logging.getLogger(__name__)

MAX_METADATA_JSON_LENGTH = 1024


@dataclass(frozen=True)
class ReferralTrackResult:
    accepted: bool
    deduped: bool


def normalize_invite_code(invite_code: str) -> str:
    return (invite_code or "").strip().upper()


def _sanitize_source(source: str) -> str:
    cleaned = (source or "").strip().lower()
    if not cleaned:
        return "unknown"
    safe_chars = []
    for ch in cleaned:
        if ch.isalnum() or ch in {"_", "-", "."}:
            safe_chars.append(ch)
    if not safe_chars:
        return "unknown"
    return "".join(safe_chars)[:64]


def _hash_invite_code(invite_code: str) -> str:
    return hashlib.sha256(invite_code.encode("utf-8")).hexdigest()


def _build_dedupe_key(
    *,
    event_type: GrowthReferralEventType,
    invite_code_hash: str,
    source: str,
    actor_user_id: Optional[uuid.UUID],
    dedupe_hint: Optional[str],
) -> str:
    normalized_hint = (dedupe_hint or "").strip()
    if not normalized_hint:
        normalized_hint = f"{actor_user_id or 'anon'}:{source}:{invite_code_hash}"
    seed = f"{event_type.value}:{normalized_hint}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def is_referral_funnel_enabled() -> bool:
    resolved = resolve_feature_flags(has_partner=True)
    if bool(resolved.kill_switches.get("disable_growth_events_ingest", False)):
        return False
    if bool(resolved.kill_switches.get("disable_referral_funnel", False)):
        return False
    return bool(resolved.flags.get("growth_referral_enabled", False))


def resolve_inviter_user_id_by_invite_code(
    *,
    session: Session,
    invite_code: str,
) -> Optional[uuid.UUID]:
    normalized_code = normalize_invite_code(invite_code)
    if not normalized_code:
        return None

    inviter_user_id = session.exec(
        select(User.id).where(User.invite_code == normalized_code)
    ).first()
    if inviter_user_id is None:
        return None
    return inviter_user_id


def track_referral_event(
    *,
    session: Session,
    event_type: GrowthReferralEventType,
    invite_code: str,
    source: str,
    actor_user_id: Optional[uuid.UUID] = None,
    inviter_user_id: Optional[uuid.UUID] = None,
    dedupe_hint: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ReferralTrackResult:
    if not is_referral_funnel_enabled():
        return ReferralTrackResult(accepted=False, deduped=False)

    normalized_code = normalize_invite_code(invite_code)
    if not normalized_code:
        return ReferralTrackResult(accepted=False, deduped=False)

    source_key = _sanitize_source(source)
    invite_code_hash = _hash_invite_code(normalized_code)
    dedupe_key = _build_dedupe_key(
        event_type=event_type,
        invite_code_hash=invite_code_hash,
        source=source_key,
        actor_user_id=actor_user_id,
        dedupe_hint=dedupe_hint,
    )

    existing = session.exec(
        select(GrowthReferralEvent.id).where(
            GrowthReferralEvent.dedupe_key == dedupe_key
        )
    ).first()
    if existing is not None:
        return ReferralTrackResult(accepted=True, deduped=True)

    if (
        actor_user_id
        and inviter_user_id
        and actor_user_id == inviter_user_id
        and event_type != GrowthReferralEventType.COUPLE_INVITE
    ):
        inviter_user_id = None

    metadata_json = None
    if metadata:
        metadata_json = json.dumps(
            metadata,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        if len(metadata_json) > MAX_METADATA_JSON_LENGTH:
            metadata_json = metadata_json[:MAX_METADATA_JSON_LENGTH]

    now = utcnow()
    event = GrowthReferralEvent(
        created_at=now,
        updated_at=now,
        event_type=event_type,
        source=source_key,
        invite_code_hash=invite_code_hash,
        dedupe_key=dedupe_key,
        inviter_user_id=inviter_user_id,
        actor_user_id=actor_user_id,
        metadata_json=metadata_json,
    )

    try:
        with session.begin_nested():
            session.add(event)
            session.flush()
    except IntegrityError:
        logger.info(
            "referral_event_deduped_race event_type=%s source=%s",
            event_type.value,
            source_key,
        )
        return ReferralTrackResult(accepted=True, deduped=True)

    logger.info(
        "referral_event_recorded event_type=%s source=%s attributed=%s",
        event_type.value,
        source_key,
        bool(inviter_user_id),
    )
    return ReferralTrackResult(accepted=True, deduped=False)
