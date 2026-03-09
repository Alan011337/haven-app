from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.middleware.request_context import request_id_var
from app.models.card_response import CardResponse
from app.models.cuj_event import CujEvent
from app.models.journal import Journal
from app.services.feature_flags import resolve_feature_flags

logger = logging.getLogger(__name__)

# Known client source values for first_delight; used to avoid logging arbitrary client input.
_ALLOWED_FIRST_DELIGHT_SOURCE_ALIASES = frozenset({"home", "home_header"})

FIRST_DELIGHT_EVENT_NAME = "FIRST_DELIGHT_DELIVERED"
DEFAULT_MIN_PAIR_JOURNALS = 2
DEFAULT_MIN_PAIR_CARD_RESPONSES = 2


@dataclass(frozen=True)
class FirstDelightEvaluation:
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    delivered: bool
    eligible: bool
    reason: str
    dedupe_key: str | None
    title: str | None
    description: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class FirstDelightAcknowledgeResult:
    accepted: bool
    deduped: bool
    reason: str
    dedupe_key: str


def _safe_count(session: Session, statement) -> int:
    value = session.exec(statement).one()
    return int(value or 0)


def _stable_pair_dedupe_key(*, user_id: uuid.UUID, partner_id: uuid.UUID) -> str:
    sorted_pair = sorted([str(user_id), str(partner_id)])
    seed = f"first_delight:{sorted_pair[0]}:{sorted_pair[1]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _resolve_pair_journal_count(*, session: Session, user_id: uuid.UUID, partner_id: uuid.UUID) -> int:
    statement = select(func.count(Journal.id)).where(
        col(Journal.user_id).in_([user_id, partner_id]),
        Journal.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _resolve_pair_card_response_count(*, session: Session, user_id: uuid.UUID, partner_id: uuid.UUID) -> int:
    statement = select(func.count(CardResponse.id)).where(
        col(CardResponse.user_id).in_([user_id, partner_id]),
        CardResponse.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _has_delivery_event(*, session: Session, dedupe_key: str) -> bool:
    existing = session.exec(
        select(CujEvent.id).where(
            CujEvent.event_name == FIRST_DELIGHT_EVENT_NAME,
            CujEvent.dedupe_key == dedupe_key,
        )
    ).first()
    return existing is not None


def evaluate_first_delight(
    *,
    session: Session,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
) -> FirstDelightEvaluation:
    has_partner_context = partner_user_id is not None
    resolved = resolve_feature_flags(has_partner=has_partner_context)
    kill_switch_active = bool(resolved.kill_switches.get("disable_growth_first_delight", False))
    feature_enabled = bool(resolved.flags.get("growth_first_delight_enabled", False))

    if not has_partner_context or kill_switch_active or not feature_enabled:
        growth_first_delight_runtime_metrics.record_evaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            eligible=False,
            delivered=False,
        )
        return FirstDelightEvaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            kill_switch_active=kill_switch_active,
            delivered=False,
            eligible=False,
            reason="disabled",
            dedupe_key=None,
            title=None,
            description=None,
            metadata={},
        )

    assert partner_user_id is not None
    dedupe_key = _stable_pair_dedupe_key(user_id=current_user_id, partner_id=partner_user_id)
    pair_journal_count = _resolve_pair_journal_count(
        session=session,
        user_id=current_user_id,
        partner_id=partner_user_id,
    )
    pair_card_response_count = _resolve_pair_card_response_count(
        session=session,
        user_id=current_user_id,
        partner_id=partner_user_id,
    )
    delivered = _has_delivery_event(session=session, dedupe_key=dedupe_key)

    eligible = (
        pair_journal_count >= DEFAULT_MIN_PAIR_JOURNALS
        and pair_card_response_count >= DEFAULT_MIN_PAIR_CARD_RESPONSES
        and not delivered
    )
    if delivered:
        reason = "delivered_already"
    elif pair_journal_count < DEFAULT_MIN_PAIR_JOURNALS:
        reason = "insufficient_pair_journals"
    elif pair_card_response_count < DEFAULT_MIN_PAIR_CARD_RESPONSES:
        reason = "insufficient_pair_card_responses"
    else:
        reason = "eligible"

    growth_first_delight_runtime_metrics.record_evaluation(
        enabled=True,
        has_partner_context=has_partner_context,
        eligible=eligible,
        delivered=delivered,
    )
    logger.info(
        "first_delight_evaluated enabled=true has_partner=%s eligible=%s delivered=%s",
        has_partner_context,
        eligible,
        delivered,
    )
    return FirstDelightEvaluation(
        enabled=True,
        has_partner_context=True,
        kill_switch_active=False,
        delivered=delivered,
        eligible=eligible,
        reason=reason,
        dedupe_key=dedupe_key,
        title="你們完成第一個同步里程碑",
        description="已達成首個雙人互動閉環，值得一起慶祝。",
        metadata={
            "pair_journal_count": pair_journal_count,
            "pair_card_response_count": pair_card_response_count,
            "target_pair_journal_count": DEFAULT_MIN_PAIR_JOURNALS,
            "target_pair_card_response_count": DEFAULT_MIN_PAIR_CARD_RESPONSES,
        },
    )


def acknowledge_first_delight(
    *,
    session: Session,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
    dedupe_key: str,
    source: str | None,
) -> FirstDelightAcknowledgeResult:
    if partner_user_id is None:
        return FirstDelightAcknowledgeResult(
            accepted=False,
            deduped=False,
            reason="partner_required",
            dedupe_key=dedupe_key,
        )

    expected = _stable_pair_dedupe_key(user_id=current_user_id, partner_id=partner_user_id)
    if dedupe_key != expected:
        return FirstDelightAcknowledgeResult(
            accepted=False,
            deduped=False,
            reason="dedupe_key_mismatch",
            dedupe_key=dedupe_key,
        )

    if _has_delivery_event(session=session, dedupe_key=dedupe_key):
        growth_first_delight_runtime_metrics.record_delivery(deduped=True)
        return FirstDelightAcknowledgeResult(
            accepted=True,
            deduped=True,
            reason="deduped",
            dedupe_key=dedupe_key,
        )

    payload = {
        "source": (source or "home"),
        "event_version": "v1",
    }
    event = CujEvent(
        user_id=current_user_id,
        partner_user_id=partner_user_id,
        event_name=FIRST_DELIGHT_EVENT_NAME,
        event_id=dedupe_key,
        source="first_delight",
        mode="BIND",
        session_id=None,
        request_id=request_id_var.get() or None,
        dedupe_key=dedupe_key,
        metadata_json=json.dumps(payload, ensure_ascii=True, sort_keys=True),
    )
    session.add(event)
    growth_first_delight_runtime_metrics.record_delivery(deduped=False)
    raw_source = payload["source"]
    log_source = (
        raw_source
        if raw_source in _ALLOWED_FIRST_DELIGHT_SOURCE_ALIASES
        else (raw_source[:50] + "…" if len(raw_source) > 50 else raw_source)
    )
    logger.info("first_delight_acknowledged dedupe_key=%s source=%s", dedupe_key, log_source)
    return FirstDelightAcknowledgeResult(
        accepted=True,
        deduped=False,
        reason="accepted",
        dedupe_key=dedupe_key,
    )


class GrowthFirstDelightRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._counts: dict[str, int] = {}

    def _increment(self, key: str, value: int = 1) -> None:
        self._counts[key] = self._counts.get(key, 0) + value

    def record_evaluation(
        self,
        *,
        enabled: bool,
        has_partner_context: bool,
        eligible: bool,
        delivered: bool,
    ) -> None:
        with self._lock:
            self._increment("growth_first_delight_evaluations_total")
            if enabled:
                self._increment("growth_first_delight_enabled_total")
            else:
                self._increment("growth_first_delight_disabled_total")
            if has_partner_context:
                self._increment("growth_first_delight_partner_context_total")
            if eligible:
                self._increment("growth_first_delight_eligible_total")
            if delivered:
                self._increment("growth_first_delight_delivered_total")

    def record_delivery(self, *, deduped: bool) -> None:
        with self._lock:
            if deduped:
                self._increment("growth_first_delight_ack_deduped_total")
            else:
                self._increment("growth_first_delight_ack_total")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


growth_first_delight_runtime_metrics = GrowthFirstDelightRuntimeMetrics()
