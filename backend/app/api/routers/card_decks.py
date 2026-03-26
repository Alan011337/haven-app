# backend/app/api/routers/card_decks.py

import uuid
import logging
from datetime import date
from time import perf_counter
from typing import Any, List, Optional, Literal
from fastapi import APIRouter, Body, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, select, col, desc, and_, func

# 引入統一的依賴
from app.api.deps import ReadSessionDep, SessionDep, CurrentUser, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling, flush_with_error_handling
from app.core.config import settings

# Models
from app.models.journal import Journal
from app.models.card import Card, CardRead, CardCategory, CardDeck
from app.models.card_response import CardResponse, ResponseStatus
from app.models.card_session import (
    CardSession,
    CardSessionMode,
    CardSessionRead,
    DeckHistoryEntry,
    CardSessionStatus,
)
from app.core.datetime_utils import utcnow
from app.core.socket_manager import manager
from app.services.depth_policy import iter_depth_caps, resolve_effective_depth_cap
from app.services.notification import queue_partner_notification
from app.services.notification_payloads import build_partner_notification_payload
from app.services.request_identity import resolve_client_ip, resolve_device_id
from app.services.rate_limit import enforce_card_response_create_rate_limit
from app.services.entitlement_runtime import resolve_quota_limit
from app.services.entitlement_usage_runtime import consume_daily_quota
from app.services.audit_log import record_audit_event, record_audit_event_best_effort
from app.models.audit_event import AuditEventOutcome
from app.services.offline_idempotency import (
    get_replayed_response,
    save_idempotency_response,
    normalize_idempotency_key,
)
from app.services.offline_conflict import (
    parse_client_timestamp,
    lww_newer_is_client,
    HEADER_CLIENT_TS,
)
from app.api.routers.card_deck_route_support import (
    build_active_session_partner_filter,
    build_history_clauses,
    build_history_entries,
    build_participant_ids,
    build_ranked_session_read,
    build_reveal_message,
    build_responded_card_subquery,
    build_responses_by_user,
    build_top_category_summary,
    count_answered_cards_in_deck_category,
    format_history_date,
    pick_new_deck_card,
    queue_partner_deck_notification as queue_partner_deck_notification_from_module,
    rank_active_deck_sessions,
    resolve_deck_response_transition,
    resolve_history_month_bounds,
    resolve_session_partner_id,
    validate_deck_response_content,
    validate_history_date_range,
)

router = APIRouter()
logger = logging.getLogger(__name__)
HISTORY_MAX_DATE_RANGE_DAYS = 366


class DeckRespondResult(SQLModel):
    status: str
    session_status: CardSessionStatus


class DeckRespondRequest(SQLModel):
    content: str


class DeckCardCount(SQLModel):
    category: str
    total_cards: int
    answered_cards: int = 0
    completion_rate: float = 0.0


class DeckHistorySummary(SQLModel):
    total_records: int = 0
    this_month_records: int = 0
    top_category: Optional[str] = None
    top_category_count: int = 0


class DeckInfo(SQLModel):
    """P2-E: Deck list item (id, name, description) for 時事 and other decks."""
    id: int
    name: str
    description: Optional[str] = None


def _queue_partner_deck_notification(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    partner_id: uuid.UUID,
    session_id: uuid.UUID,
    action_event: Literal["card_waiting", "card_revealed"],
) -> None:
    queue_partner_deck_notification_from_module(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        session_id=session_id,
        action_event=action_event,
        build_partner_notification_payload=build_partner_notification_payload,
        queue_partner_notification=queue_partner_notification,
    )


def _log_history_metrics(
    *,
    endpoint: str,
    current_user: CurrentUser,
    category: Optional[CardCategory],
    revealed_from: Optional[date],
    revealed_to: Optional[date],
    duration_ms: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    result_count: Optional[int] = None,
    total_records: Optional[int] = None,
) -> None:
    logger.info(
        (
            "deck_history_metrics endpoint=%s user_id=%s category=%s "
            "revealed_from=%s revealed_to=%s limit=%s offset=%s "
            "result_count=%s total_records=%s duration_ms=%s"
        ),
        endpoint,
        current_user.id,
        category.value if category else None,
        format_history_date(revealed_from),
        format_history_date(revealed_to),
        limit,
        offset,
        result_count,
        total_records,
        duration_ms,
    )


# ----------------------------------------------------------------
# 0. 牌組列表 (P2-E: 時事等動態牌組可由此取得 deck_id)
# ----------------------------------------------------------------
@router.get("/list", response_model=List[DeckInfo])
def list_decks(
    session: ReadSessionDep,
    current_user: CurrentUser,
) -> List[DeckInfo]:
    """Return all decks (id, name, description). Use deck_id with GET /{deck_id}/draw for 時事抽卡."""
    decks = session.exec(select(CardDeck)).all()
    return [DeckInfo(id=d.id, name=d.name, description=d.description) for d in decks]


# ----------------------------------------------------------------
# 0b. 牌組題數統計
# ----------------------------------------------------------------
@router.get("/stats", response_model=List[DeckCardCount])
def get_deck_card_counts(
    *,
    session: SessionDep,
    current_user: CurrentUser,
):
    total_rows = session.exec(
        select(Card.category, func.count(Card.id))
        .group_by(Card.category)
    ).all()

    answered_rows = session.exec(
        select(Card.category, func.count(func.distinct(CardResponse.card_id)))
        .join(CardResponse, CardResponse.card_id == Card.id)
        .join(CardSession, CardSession.id == CardResponse.session_id)
        .where(
            CardResponse.user_id == current_user.id,
            CardSession.mode == CardSessionMode.DECK,
            CardResponse.deleted_at.is_(None),
            CardSession.deleted_at.is_(None),
        )
        .group_by(Card.category)
    ).all()

    counts: dict[str, int] = {}
    for category_value, total in total_rows:
        key = category_value.value if isinstance(category_value, CardCategory) else str(category_value)
        counts[key] = int(total or 0)

    answered_counts: dict[str, int] = {}
    for category_value, answered in answered_rows:
        key = category_value.value if isinstance(category_value, CardCategory) else str(category_value)
        answered_counts[key] = int(answered or 0)

    result: list[DeckCardCount] = []
    for category in CardCategory:
        total_cards = counts.get(category.value, 0)
        answered_cards = min(answered_counts.get(category.value, 0), total_cards)
        completion_rate = round((answered_cards / total_cards) * 100, 1) if total_cards else 0.0
        result.append(
            DeckCardCount(
                category=category.value,
                total_cards=total_cards,
                answered_cards=answered_cards,
                completion_rate=completion_rate,
            )
        )
    return result


# ----------------------------------------------------------------
# 1. 智慧抽卡 API (終極同步版：精準優先權分類)
# ----------------------------------------------------------------
@router.post("/draw", response_model=CardSessionRead)
def deck_draw_card(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    category: CardCategory,
    skip_waiting: bool = False,
    preferred_depth: Optional[int] = Query(None, ge=1, le=3),
):
    card_draw_quota_limit = resolve_quota_limit(
        session=session,
        user_id=current_user.id,
        feature="card_draws_per_day",
    )

    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)

    partner_filter = build_active_session_partner_filter(
        current_user_id=current_user.id,
        verified_partner_id=verified_partner_id,
    )

    active_sessions = session.exec(
        select(CardSession).where(
            CardSession.mode == CardSessionMode.DECK,
            CardSession.category == category.value.upper(),
            col(CardSession.status).in_([CardSessionStatus.PENDING, CardSessionStatus.WAITING_PARTNER]),
            partner_filter,
            CardSession.deleted_at.is_(None),
        ).order_by(col(CardSession.created_at).asc())
    ).all()

    ranked_sessions = rank_active_deck_sessions(
        session=session,
        active_sessions=active_sessions,
        current_user_id=current_user.id,
        include_waiting=not skip_waiting,
    )

    existing_session = build_ranked_session_read(
        session=session,
        ranked_sessions=ranked_sessions,
        logger_warning=logger.warning,
    )
    if existing_session:
        return existing_session

    draw_allowed, _ = consume_daily_quota(
        session=session,
        user_id=current_user.id,
        feature_key="card_draws_per_day",
        quota_limit=card_draw_quota_limit,
    )
    if not draw_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "quota_exceeded",
                "message": "今日抽卡次數已達上限，升級方案可繼續使用。",
            },
        )

    # --- 5. 如果上面都清空了 (或是我把 waiting 都 skip 了) -> 抽一張全新的卡 ---
    
    # 1. 以子查詢排除我已回答的卡，避免把所有 card_id 拉回應用層。
    responded_card_subquery = build_responded_card_subquery(
        user_id=current_user.id,
    )

    answered_count = count_answered_cards_in_deck_category(
        session=session,
        user_id=current_user.id,
        category=category,
    )
    start_depth_cap = resolve_effective_depth_cap(answered_count, preferred_depth)

    chosen_card = None
    for depth_cap in iter_depth_caps(start_depth_cap):
        chosen_card = pick_new_deck_card(
            session=session,
            category=category,
            responded_card_subquery=responded_card_subquery,
            depth_cap=depth_cap,
        )
        if chosen_card:
            break

    if not chosen_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="恭喜！你已經完成了這個分類的所有卡片！快去催促伴侶回答吧！",
        )

    new_session = CardSession(
        card_id=chosen_card.id,
        creator_id=current_user.id,
        partner_id=verified_partner_id,
        category=category.value.upper(),
        mode=CardSessionMode.DECK,
        status=CardSessionStatus.PENDING
    )
    session.add(new_session)
    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        target_user_id=verified_partner_id,
        action="CARD_DECK_DRAW",
        resource_type="card_session",
        resource_id=new_session.id,
        metadata={
            "category": category.value.upper(),
            "card_id": str(chosen_card.id),
            "skip_waiting": skip_waiting,
        },
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="Draw deck card",
        conflict_detail="建立牌組會話時發生衝突，請重試。",
        failure_detail="建立牌組會話失敗，請稍後再試。",
    )
    session.refresh(new_session)
    
    return CardSessionRead(
        **new_session.model_dump(),
        card=chosen_card
    )


# ----------------------------------------------------------------
# 2. 針對特定會話回答 (加入 WebSocket 廣播)
# ----------------------------------------------------------------
@router.post("/respond/{session_id}", response_model=DeckRespondResult)
async def deck_respond(  
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: Request,
    session_id: uuid.UUID,
    payload: Optional[DeckRespondRequest] = Body(default=None),
    content: Optional[str] = Query(default=None, min_length=1, max_length=2000),
    ):
    # P2-F: idempotency for offline replay (RFC-004)
    idem_key = normalize_idempotency_key(request.headers.get("Idempotency-Key"), None)
    if idem_key:
        replayed = get_replayed_response(session, current_user.id, idem_key)
        if replayed is not None:
            return JSONResponse(
                content=replayed,
                headers={"X-Idempotency-Replayed": "true"},
            )

    cleaned_content = validate_deck_response_content(
        raw_content=payload.content if payload else content,
        max_length=2000,
    )

    # 1. 找會話
    card_session = session.get(CardSession, session_id)
    if not card_session or card_session.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到該抽卡紀錄。",
        )
    if current_user.id not in {card_session.creator_id, card_session.partner_id}:
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=card_session.creator_id,
            action="CARD_DECK_RESPOND_DENIED",
            resource_type="card_session",
            resource_id=session_id,
            outcome=AuditEventOutcome.DENIED,
            reason="not_participant",
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你沒有權限回覆這個會話。",
        )
    if card_session.mode != CardSessionMode.DECK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此會話不是牌組模式，請改用對應流程回覆。",
        )
    partner_id = resolve_session_partner_id(
        current_user_id=current_user.id,
        card_session=card_session,
    )
    participant_ids = build_participant_ids(
        current_user_id=current_user.id,
        partner_id=partner_id,
    )

    # 2. 一次取回本 session 相關回覆，減少重複查詢
    existing_responses = session.exec(
        select(CardResponse).where(
            CardResponse.session_id == session_id,
            col(CardResponse.user_id).in_(participant_ids),
            CardResponse.deleted_at.is_(None),
        )
    ).all()
    responses_by_user = build_responses_by_user(existing_responses=existing_responses)

    my_resp = responses_by_user.get(current_user.id)
    partner_resp = responses_by_user.get(partner_id) if partner_id else None
    is_new_response = my_resp is None
    was_completed = card_session.status == CardSessionStatus.COMPLETED

    # P2-F P1: LWW — if updating and client timestamp older than server, 409
    client_ts_ms = parse_client_timestamp(request.headers.get(HEADER_CLIENT_TS))
    if my_resp is not None and client_ts_ms is not None:
        if not lww_newer_is_client(client_ts_ms, my_resp.created_at):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="已由其他裝置更新，以伺服器為準。",
                headers={"X-Conflict-Code": "CONFLICT_LWW"},
            )

    if is_new_response:
        client_ip = resolve_client_ip(request)
        device_id = resolve_device_id(
            request,
            header_name=settings.RATE_LIMIT_DEVICE_HEADER,
        )
        enforce_card_response_create_rate_limit(
            session=session,
            user_id=current_user.id,
            limit_count=settings.CARD_RESPONSE_RATE_LIMIT_COUNT,
            window_seconds=settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS,
            partner_id=partner_id,
            client_ip=client_ip,
            device_id=device_id,
            ip_limit_count=settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT,
            device_limit_count=settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT,
            partner_pair_limit_count=settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT,
            endpoint="/api/card-decks/respond/{session_id}",
        )

    if my_resp:
        my_resp.content = cleaned_content
        session.add(my_resp)
    else:
        new_resp = CardResponse(
            card_id=card_session.card_id,
            user_id=current_user.id,
            content=cleaned_content,
            session_id=session_id,
            status=ResponseStatus.PENDING,
            is_initiator=partner_resp is None
        )
        session.add(new_resp)
        my_resp = new_resp
    flush_with_error_handling(
        session,
        logger=logger,
        action="Persist deck response",
        conflict_detail="儲存牌組回覆發生衝突，請重試。",
        failure_detail="儲存牌組回覆失敗，請稍後再試。",
    )

    # 3. 檢查伴侶狀態與解鎖邏輯
    if partner_id and not partner_resp:
        # 競態保護：如果伴侶剛好在我回覆期間提交，重新檢查一次。
        partner_resp = session.exec(
            select(CardResponse).where(
                CardResponse.session_id == session_id,
                CardResponse.user_id == partner_id,
                CardResponse.deleted_at.is_(None),
            )
        ).first()

    new_session_status, should_broadcast = resolve_deck_response_transition(
        partner_resp=partner_resp,
        was_completed=was_completed,
    )

    if should_broadcast:
        # 更新我的狀態為 REVEALED
        my_resp.status = ResponseStatus.REVEALED
        session.add(my_resp)
            
        # 更新伴侶狀態為 REVEALED
        partner_resp.status = ResponseStatus.REVEALED
        session.add(partner_resp)

    # 4. 更新 Session 狀態
    card_session.status = new_session_status
    session.add(card_session)

    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        target_user_id=partner_id,
        action="CARD_DECK_RESPOND",
        resource_type="card_session",
        resource_id=session_id,
        metadata={
            "is_new_response": is_new_response,
            "session_status": new_session_status.value,
        },
    )
    
    # 🔥🔥🔥 關鍵修正：先 Commit 寫入資料庫，確認狀態已變更為 COMPLETED 🔥🔥🔥
    commit_with_error_handling(
        session,
        logger=logger,
        action="Finalize deck response",
        conflict_detail="更新牌組狀態時發生衝突，請重試。",
        failure_detail="更新牌組狀態失敗，請稍後再試。",
    )
    
    # 5. 資料庫確認寫入後，才發送廣播
    if should_broadcast:
        logger.info("Deck session completed. Broadcasting reveal event.")
        reveal_message = build_reveal_message(
            card_id=card_session.card_id,
            session_id=session_id,
        )
        
        # 廣播給雙方
        await manager.send_personal_message(reveal_message, str(current_user.id))
        if partner_id:
            await manager.send_personal_message(reveal_message, str(partner_id))

            if is_new_response:
                _queue_partner_deck_notification(
                    session=session,
                    current_user=current_user,
                    partner_id=partner_id,
                    session_id=session_id,
                    action_event="card_revealed",
                )
    elif partner_id and new_session_status == CardSessionStatus.WAITING_PARTNER and is_new_response:
        _queue_partner_deck_notification(
            session=session,
            current_user=current_user,
            partner_id=partner_id,
            session_id=session_id,
            action_event="card_waiting",
        )

    result = DeckRespondResult(status="success", session_status=new_session_status)
    # P2-F: store idempotency for offline replay
    if idem_key:
        response_payload = result.model_dump()
        save_idempotency_response(
            session,
            current_user.id,
            idem_key,
            "deck_respond",
            str(session_id),
            response_payload,
        )
        commit_with_error_handling(
            session,
            logger=logger,
            action="Save idempotency log",
            conflict_detail="儲存牌組回覆發生衝突，請重試。",
            failure_detail="儲存牌組回覆失敗，請稍後再試。",
        )

    return result


# ----------------------------------------------------------------
# 3. 歷史紀錄 (無限模式)
# ----------------------------------------------------------------
@router.get("/history", response_model=List[DeckHistoryEntry])
def get_deck_history(
    *,
    session: ReadSessionDep,
    current_user: CurrentUser,
    category: Optional[CardCategory] = None, 
    revealed_from: Optional[date] = Query(default=None),
    revealed_to: Optional[date] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query_started_at = perf_counter()
    validate_history_date_range(
        revealed_from=revealed_from,
        revealed_to=revealed_to,
        max_date_range_days=HISTORY_MAX_DATE_RANGE_DAYS,
    )
    clauses = build_history_clauses(
        current_user_id=current_user.id,
        category=category,
        revealed_from=revealed_from,
        revealed_to=revealed_to,
    )
    statement = select(CardSession).where(*clauses)
    
    statement = statement.order_by(col(CardSession.created_at).desc()).offset(offset).limit(limit)
    completed_sessions = session.exec(statement).all()
    if not completed_sessions:
        _log_history_metrics(
            endpoint="history",
            current_user=current_user,
            category=category,
            revealed_from=revealed_from,
            revealed_to=revealed_to,
            duration_ms=int((perf_counter() - query_started_at) * 1000),
            limit=limit,
            offset=offset,
            result_count=0,
        )
        return []
    
    session_ids = [s.id for s in completed_sessions]
    card_ids = list({s.card_id for s in completed_sessions})

    cards = session.exec(select(Card).where(col(Card.id).in_(card_ids))).all()
    cards_by_id = {card.id: card for card in cards}

    responses = session.exec(
        select(CardResponse).where(
            col(CardResponse.session_id).in_(session_ids),
            CardResponse.deleted_at.is_(None),
        )
    ).all()
    responses_by_key = {(resp.session_id, resp.user_id): resp for resp in responses}

    history_list = build_history_entries(
        completed_sessions=completed_sessions,
        cards_by_id=cards_by_id,
        responses_by_key=responses_by_key,
        current_user_id=current_user.id,
    )

    _log_history_metrics(
        endpoint="history",
        current_user=current_user,
        category=category,
        revealed_from=revealed_from,
        revealed_to=revealed_to,
        duration_ms=int((perf_counter() - query_started_at) * 1000),
        limit=limit,
        offset=offset,
        result_count=len(history_list),
    )
    return history_list


# ----------------------------------------------------------------
# 4. 歷史摘要 (全量統計)
# ----------------------------------------------------------------
@router.get("/history/summary", response_model=DeckHistorySummary)
def get_deck_history_summary(
    *,
    session: ReadSessionDep,
    current_user: CurrentUser,
    category: Optional[CardCategory] = None,
    revealed_from: Optional[date] = Query(default=None),
    revealed_to: Optional[date] = Query(default=None),
):
    query_started_at = perf_counter()
    validate_history_date_range(
        revealed_from=revealed_from,
        revealed_to=revealed_to,
        max_date_range_days=HISTORY_MAX_DATE_RANGE_DAYS,
    )
    clauses = build_history_clauses(
        current_user_id=current_user.id,
        category=category,
        revealed_from=revealed_from,
        revealed_to=revealed_to,
    )

    total_records = int(
        session.exec(select(func.count(CardSession.id)).where(*clauses)).one() or 0
    )

    now = utcnow()
    month_start, next_month_start = resolve_history_month_bounds(now=now)

    this_month_records = int(
        session.exec(
            select(func.count(CardSession.id)).where(
                *clauses,
                CardSession.created_at >= month_start,
                CardSession.created_at < next_month_start,
            )
        ).one()
        or 0
    )

    top_category_row = session.exec(
        select(CardSession.category, func.count(CardSession.id))
        .where(*clauses)
        .group_by(CardSession.category)
        .order_by(desc(func.count(CardSession.id)))
        .limit(1)
    ).first()

    top_category, top_category_count = build_top_category_summary(top_category_row)

    summary = DeckHistorySummary(
        total_records=total_records,
        this_month_records=this_month_records,
        top_category=top_category,
        top_category_count=top_category_count,
    )
    _log_history_metrics(
        endpoint="history_summary",
        current_user=current_user,
        category=category,
        revealed_from=revealed_from,
        revealed_to=revealed_to,
        duration_ms=int((perf_counter() - query_started_at) * 1000),
        total_records=summary.total_records,
    )
    return summary


# ----------------------------------------------------------------
# 5. 指定牌組抽卡 (每日/Daily Vibe 模式)
# ----------------------------------------------------------------
@router.get("/{deck_id}/draw", response_model=CardRead)
def draw_card_from_deck(
    *,
    session: SessionDep,
    deck_id: int,
    current_user: CurrentUser,
) -> Any:
    target_card = None
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    if verified_pid:
        latest_partner_journal = session.exec(
            select(Journal)
            .where(
                and_(
                    Journal.deck_id == deck_id,
                    Journal.user_id == verified_pid,
                    Journal.deleted_at.is_(None),
                )
            )
            .order_by(desc(Journal.created_at))
        ).first()
        
        if latest_partner_journal:
             target_card = session.get(Card, latest_partner_journal.card_id)

    if target_card:
        return target_card

    card = session.exec(
        select(Card).where(Card.deck_id == deck_id).order_by(func.random())
    ).first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="此牌組目前沒有卡片。",
        )

    return card
