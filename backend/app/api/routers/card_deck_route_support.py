"""Shared helper logic for card deck routes."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import col, func, or_, select

from app.models.card import Card, CardCategory
from app.models.card_response import CardResponse
from app.models.card_session import (
    CardSession,
    CardSessionMode,
    CardSessionRead,
    CardSessionStatus,
    DeckHistoryEntry,
)


def queue_partner_deck_notification(
    *,
    session: Any,
    current_user: Any,
    partner_id: uuid.UUID,
    session_id: uuid.UUID,
    action_event: str,
    build_partner_notification_payload: Callable[..., dict[str, Any] | None],
    queue_partner_notification: Callable[..., None],
) -> None:
    payload = build_partner_notification_payload(
        session=session,
        sender_user=current_user,
        event_type=action_event,
        scope_id=session_id,
        source_session_id=session_id,
        partner_user_id=partner_id,
    )
    if not payload:
        return

    queue_partner_notification(
        action_type="card",
        **payload,
    )


def validate_history_date_range(
    *,
    revealed_from: date | None,
    revealed_to: date | None,
    max_date_range_days: int,
) -> None:
    if revealed_from and revealed_to and revealed_from > revealed_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="revealed_from 不能晚於 revealed_to。",
        )
    if (
        revealed_from
        and revealed_to
        and (revealed_to - revealed_from).days > max_date_range_days
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"查詢區間不可超過 {max_date_range_days} 天。",
        )


def build_history_clauses(
    *,
    current_user_id: uuid.UUID,
    category: CardCategory | None,
    revealed_from: date | None,
    revealed_to: date | None,
) -> list[Any]:
    clauses: list[Any] = [
        CardSession.mode == CardSessionMode.DECK,
        CardSession.status == CardSessionStatus.COMPLETED,
        or_(CardSession.creator_id == current_user_id, CardSession.partner_id == current_user_id),
        CardSession.deleted_at.is_(None),
    ]

    if category:
        clauses.append(CardSession.category == category.value.upper())

    if revealed_from:
        clauses.append(CardSession.created_at >= datetime.combine(revealed_from, time.min))
    if revealed_to:
        clauses.append(CardSession.created_at <= datetime.combine(revealed_to, time.max))

    return clauses


def format_history_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def build_active_session_partner_filter(
    *,
    current_user_id: uuid.UUID,
    verified_partner_id: uuid.UUID | None,
) -> Any:
    if verified_partner_id:
        return or_(
            CardSession.creator_id == current_user_id,
            CardSession.partner_id == current_user_id,
        )
    return CardSession.creator_id == current_user_id


def count_answered_cards_in_deck_category(
    *,
    session: Any,
    user_id: uuid.UUID,
    category: CardCategory,
) -> int:
    statement = (
        select(func.count(func.distinct(CardResponse.card_id)))
        .join(CardSession, CardSession.id == CardResponse.session_id)
        .where(
            CardResponse.user_id == user_id,
            CardSession.mode == CardSessionMode.DECK,
            CardSession.category == category.value.upper(),
            CardResponse.deleted_at.is_(None),
            CardSession.deleted_at.is_(None),
        )
    )
    return int(session.exec(statement).one() or 0)


def build_responded_card_subquery(*, user_id: uuid.UUID) -> Any:
    return (
        select(CardResponse.card_id)
        .join(CardSession, CardSession.id == CardResponse.session_id)
        .where(
            CardResponse.user_id == user_id,
            CardSession.mode == CardSessionMode.DECK,
            CardResponse.deleted_at.is_(None),
            CardSession.deleted_at.is_(None),
        )
    )


def pick_new_deck_card(
    *,
    session: Any,
    category: CardCategory,
    responded_card_subquery: Any,
    depth_cap: int,
) -> Card | None:
    return session.exec(
        select(Card)
        .where(
            Card.category == category.value.upper(),
            col(Card.id).not_in(responded_card_subquery),
            or_(Card.depth_level.is_(None), Card.depth_level <= depth_cap),
        )
        .order_by(func.random())
    ).first()


def rank_active_deck_sessions(
    *,
    session: Any,
    active_sessions: list[CardSession],
    current_user_id: uuid.UUID,
    include_waiting: bool,
) -> list[tuple[CardSession, CardSessionStatus]]:
    session_ids = [item.id for item in active_sessions]
    response_keys: set[tuple[uuid.UUID, uuid.UUID]] = set()
    if session_ids:
        response_rows = session.exec(
            select(CardResponse.session_id, CardResponse.user_id).where(
                col(CardResponse.session_id).in_(session_ids),
                CardResponse.deleted_at.is_(None),
            )
        ).all()
        response_keys = {(resp_session_id, resp_user_id) for resp_session_id, resp_user_id in response_rows}

    catch_up_sessions: list[CardSession] = []
    pending_sessions: list[CardSession] = []
    waiting_sessions: list[CardSession] = []

    for item in active_sessions:
        my_resp_exists = (item.id, current_user_id) in response_keys
        partner_target_id = item.partner_id if current_user_id == item.creator_id else item.creator_id
        partner_resp_exists = bool(partner_target_id) and (item.id, partner_target_id) in response_keys

        if partner_resp_exists and not my_resp_exists:
            catch_up_sessions.append(item)
        elif not my_resp_exists and not partner_resp_exists:
            pending_sessions.append(item)
        elif my_resp_exists and not partner_resp_exists:
            waiting_sessions.append(item)

    ranked_sessions: list[tuple[CardSession, CardSessionStatus]] = []
    ranked_sessions.extend((item, CardSessionStatus.PENDING) for item in catch_up_sessions)
    ranked_sessions.extend((item, CardSessionStatus.PENDING) for item in pending_sessions)
    if include_waiting:
        ranked_sessions.extend((item, CardSessionStatus.WAITING_PARTNER) for item in waiting_sessions)
    return ranked_sessions


def build_ranked_session_read(
    *,
    session: Any,
    ranked_sessions: list[tuple[CardSession, CardSessionStatus]],
    logger_warning: Callable[..., None],
) -> CardSessionRead | None:
    if not ranked_sessions:
        return None

    candidate_card_ids = list({session_item.card_id for session_item, _ in ranked_sessions})
    cards = session.exec(select(Card).where(col(Card.id).in_(candidate_card_ids))).all()
    cards_by_id = {card.id: card for card in cards}

    for target_session, returned_status in ranked_sessions:
        card = cards_by_id.get(target_session.card_id)
        if not card:
            logger_warning(
                "Skip orphaned card session %s because card %s is missing.",
                target_session.id,
                target_session.card_id,
            )
            continue
        session_data = target_session.model_dump()
        session_data["status"] = returned_status
        return CardSessionRead(**session_data, card=card)

    return None


def validate_deck_response_content(
    *,
    raw_content: str | None,
    max_length: int,
) -> str:
    if raw_content is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="content 欄位為必填。",
        )

    cleaned_content = raw_content.strip()
    if not cleaned_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="回答內容不能為空白。",
        )
    if len(cleaned_content) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"content 長度不可超過 {max_length} 字元。",
        )
    return cleaned_content


def resolve_session_partner_id(
    *,
    current_user_id: uuid.UUID,
    card_session: CardSession,
) -> uuid.UUID | None:
    if current_user_id == card_session.creator_id:
        return card_session.partner_id
    return card_session.creator_id


def build_participant_ids(
    *,
    current_user_id: uuid.UUID,
    partner_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    participant_ids = [current_user_id]
    if partner_id:
        participant_ids.append(partner_id)
    return participant_ids


def build_responses_by_user(
    *,
    existing_responses: list[CardResponse],
) -> dict[uuid.UUID, CardResponse]:
    return {response.user_id: response for response in existing_responses}


def resolve_deck_response_transition(
    *,
    partner_resp: CardResponse | None,
    was_completed: bool,
) -> tuple[CardSessionStatus, bool]:
    new_session_status = (
        CardSessionStatus.COMPLETED if partner_resp else CardSessionStatus.WAITING_PARTNER
    )
    should_broadcast = bool(partner_resp and not was_completed)
    return new_session_status, should_broadcast


def build_reveal_message(
    *,
    card_id: int,
    session_id: uuid.UUID,
) -> dict[str, str]:
    return {
        "event": "CARD_REVEALED",
        "card_id": str(card_id),
        "session_id": str(session_id),
        "message": "雙方都已回答，答案揭曉！",
    }


def build_history_entries(
    *,
    completed_sessions: list[CardSession],
    cards_by_id: dict[int, Card],
    responses_by_key: dict[tuple[uuid.UUID, uuid.UUID], CardResponse],
    current_user_id: uuid.UUID,
) -> list[DeckHistoryEntry]:
    history_entries: list[DeckHistoryEntry] = []
    for item in completed_sessions:
        history_entry = build_history_entry(
            completed_session=item,
            cards_by_id=cards_by_id,
            responses_by_key=responses_by_key,
            current_user_id=current_user_id,
        )
        if history_entry:
            history_entries.append(history_entry)
    return history_entries


def build_history_entry(
    *,
    completed_session: CardSession,
    cards_by_id: dict[int, Card],
    responses_by_key: dict[tuple[uuid.UUID, uuid.UUID], CardResponse],
    current_user_id: uuid.UUID,
) -> DeckHistoryEntry | None:
    card = cards_by_id.get(completed_session.card_id)
    my_resp = responses_by_key.get((completed_session.id, current_user_id))
    partner_id = completed_session.partner_id if completed_session.creator_id == current_user_id else completed_session.creator_id
    partner_resp = responses_by_key.get((completed_session.id, partner_id)) if partner_id else None

    if not card or not my_resp or not partner_resp:
        return None

    return DeckHistoryEntry(
        session_id=completed_session.id,
        card_title=card.title,
        card_question=card.question,
        category=completed_session.category,
        depth_level=card.depth_level,
        my_answer=my_resp.content,
        partner_answer=partner_resp.content,
        revealed_at=completed_session.created_at,
    )


def resolve_history_month_bounds(*, now: datetime) -> tuple[datetime, datetime]:
    month_start = datetime(now.year, now.month, 1)
    if now.month == 12:
        return month_start, datetime(now.year + 1, 1, 1)
    return month_start, datetime(now.year, now.month + 1, 1)


def build_top_category_summary(top_category_row: Any) -> tuple[str | None, int]:
    if not top_category_row:
        return None, 0
    return (
        str(top_category_row[0]) if top_category_row[0] else None,
        int(top_category_row[1] or 0),
    )
