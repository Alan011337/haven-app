# backend/app/api/routers/cards.py

import uuid
import logging
from enum import Enum
from typing import Any, List, Optional, Literal
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import select, col, or_, func

# 引入 models 和 deps
from app.api.deps import SessionDep, CurrentUser, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.card import Card, CardRead, CardCategory
from app.models.card_response import CardResponse, CardResponseCreate, CardResponseRead, ResponseStatus
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus 
from app.models.user import User
from app.core.socket_manager import manager
from app.services.depth_policy import iter_depth_caps, resolve_effective_depth_cap
from app.services.notification import queue_partner_notification
from app.services.notification_payloads import build_partner_notification_payload
from app.services.request_identity import resolve_client_ip, resolve_device_id
from app.services.rate_limit import enforce_card_response_create_rate_limit
from app.services.entitlement_runtime import resolve_quota_limit
from app.services.entitlement_usage_runtime import consume_daily_quota
from app.services.audit_log import record_audit_event
from app.services.cuj_event_emitter import emit_cuj_event
from app.services.cuj_sli_runtime import (
    EVENT_RITUAL_DRAW,
    EVENT_RITUAL_RESPOND,
    EVENT_RITUAL_UNLOCK,
)
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
from app.api.routers.card_helpers import (
    get_today_range as _get_today_range_helper,
    normalize_category_or_raise as _normalize_category_or_raise_helper,
)

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_CARD_CATEGORY_VALUES = {category.value for category in CardCategory}


class DrawSource(str, Enum):
    LIBRARY = "library"
    DAILY_RITUAL = "daily_ritual"


def _queue_partner_card_notification(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    action_event: Literal["card_waiting", "card_revealed"],
    scope_id: uuid.UUID,
    source_session_id: Optional[uuid.UUID],
) -> None:
    payload = build_partner_notification_payload(
        session=session,
        sender_user=current_user,
        event_type=action_event,
        scope_id=scope_id,
        source_session_id=source_session_id,
    )
    if not payload:
        return

    queue_partner_notification(
        action_type="card",
        **payload,
    )


def normalize_category_or_raise(category: Optional[str]) -> Optional[str]:
    return _normalize_category_or_raise_helper(
        category,
        valid_values=VALID_CARD_CATEGORY_VALUES,
    )


# 取得今天 UTC 的時間範圍，用來查詢今日 Session
def get_today_range():
    now = utcnow()
    return _get_today_range_helper(now_utc=now)


def _resolve_partner_name(session: SessionDep, *, partner_id: Optional[uuid.UUID]) -> str:
    if not partner_id:
        return "伴侶"
    partner_row = session.exec(
        select(User.full_name, User.email).where(
            User.id == partner_id,
            User.deleted_at.is_(None),
        )
    ).first()
    if not partner_row:
        return "伴侶"
    full_name, email = partner_row
    return full_name or str(email).split("@")[0]


def _get_daily_session_with_card(
    session: SessionDep,
    *,
    user_id: uuid.UUID,
    start_of_day,
    end_of_day,
) -> tuple[Optional[CardSession], Optional[Card]]:
    row = session.exec(
        select(CardSession, Card)
        .join(Card, Card.id == CardSession.card_id, isouter=True)
        .where(
            CardSession.mode == CardSessionMode.DAILY_RITUAL,
            or_(
                CardSession.creator_id == user_id,
                CardSession.partner_id == user_id,
            ),
            CardSession.created_at >= start_of_day,
            CardSession.created_at <= end_of_day,
            CardSession.deleted_at.is_(None),
        )
        .order_by(col(CardSession.created_at).desc())
    ).first()
    if not row:
        return None, None
    card_session, target_card = row
    return card_session, target_card


def _get_session_responses_by_user(
    session: SessionDep,
    *,
    session_id: uuid.UUID,
    user_ids: list[uuid.UUID],
) -> dict[uuid.UUID, CardResponse]:
    if not user_ids:
        return {}
    responses = session.exec(
        select(CardResponse).where(
            CardResponse.session_id == session_id,
            CardResponse.user_id.in_(user_ids),
            CardResponse.deleted_at.is_(None),
        )
    ).all()
    return {response.user_id: response for response in responses}


def _get_legacy_daily_response(
    session: SessionDep,
    *,
    user_id: Optional[uuid.UUID],
    card_id: uuid.UUID,
    start_of_day,
) -> Optional[CardResponse]:
    if not user_id:
        return None
    return session.exec(
        select(CardResponse).where(
            CardResponse.user_id == user_id,
            CardResponse.card_id == card_id,
            CardResponse.session_id.is_(None),
            CardResponse.created_at >= start_of_day,
            CardResponse.deleted_at.is_(None),
        )
    ).first()


def _count_answered_cards_in_library(
    session: SessionDep,
    *,
    user_id: uuid.UUID,
    normalized_category: Optional[str],
) -> int:
    statement = (
        select(func.count(func.distinct(CardResponse.card_id)))
        .join(Card, Card.id == CardResponse.card_id)
        .where(
            CardResponse.user_id == user_id,
            CardResponse.session_id.is_(None),
            CardResponse.deleted_at.is_(None),
        )
    )
    if normalized_category:
        statement = statement.where(Card.category == normalized_category)
    return int(session.exec(statement).one() or 0)


def _pick_unanswered_library_card(
    session: SessionDep,
    *,
    user_id: uuid.UUID,
    normalized_category: Optional[str],
    depth_cap: int,
) -> Optional[Card]:
    my_done_ids = select(CardResponse.card_id).where(
        CardResponse.user_id == user_id,
        CardResponse.session_id.is_(None),
        CardResponse.deleted_at.is_(None),
    )
    statement = select(Card).where(
        col(Card.id).not_in(my_done_ids),
        or_(Card.depth_level.is_(None), Card.depth_level <= depth_cap),
    )
    if normalized_category:
        statement = statement.where(Card.category == normalized_category)
    return session.exec(statement.order_by(func.random())).first()


def _count_answered_cards_in_daily_ritual(
    session: SessionDep,
    *,
    user_id: uuid.UUID,
    category_filter: str,
) -> int:
    statement = (
        select(func.count(func.distinct(CardResponse.card_id)))
        .join(CardSession, CardSession.id == CardResponse.session_id)
        .join(Card, Card.id == CardResponse.card_id)
        .where(
            CardResponse.user_id == user_id,
            CardSession.mode == CardSessionMode.DAILY_RITUAL,
            Card.category == category_filter,
            CardResponse.deleted_at.is_(None),
            CardSession.deleted_at.is_(None),
        )
    )
    return int(session.exec(statement).one() or 0)


def _pick_daily_card_with_depth_cap(
    session: SessionDep,
    *,
    category_filter: str,
    depth_cap: int,
) -> Optional[Card]:
    return session.exec(
        select(Card)
        .where(
            Card.category == category_filter,
            or_(Card.depth_level.is_(None), Card.depth_level <= depth_cap),
        )
        .order_by(func.random())
    ).first()


# --- 1. 每日狀態同步 API ---
@router.get("/daily-status")
def get_daily_status(
    session: SessionDep,
    current_user: CurrentUser,
):
    """
    檢查今日卡片狀態。直接對接前端需要的 state。
    """
    partner_name = _resolve_partner_name(session, partner_id=current_user.partner_id)

    start_of_day, end_of_day = get_today_range()
    card_session, target_card = _get_daily_session_with_card(
        session,
        user_id=current_user.id,
        start_of_day=start_of_day,
        end_of_day=end_of_day,
    )

    # 情況 A: 今天還沒抽卡
    if not card_session:
        return {
            "state": "IDLE",
            "card": None,
            "partner_name": partner_name,
            "session_id": None,
        }

    if not target_card:
        return {
            "state": "IDLE",
            "card": None,
            "partner_name": partner_name,
            "session_id": str(card_session.id),
        }

    session_responses = _get_session_responses_by_user(
        session,
        session_id=card_session.id,
        user_ids=[
            current_user.id,
            *([current_user.partner_id] if current_user.partner_id else []),
        ],
    )
    my_response = session_responses.get(current_user.id)
    if not my_response:
        my_response = _get_legacy_daily_response(
            session,
            user_id=current_user.id,
            card_id=target_card.id,
            start_of_day=start_of_day,
        )

    # 情況 B: 雙方皆完成
    if card_session.status == CardSessionStatus.COMPLETED:
        partner_response = session_responses.get(current_user.partner_id) if current_user.partner_id else None
        if not partner_response:
            partner_response = _get_legacy_daily_response(
                session,
                user_id=current_user.partner_id,
                card_id=target_card.id,
                start_of_day=start_of_day,
            )
        return {
            "state": "COMPLETED",
            "card": target_card,
            "my_content": my_response.content if my_response else "",
            "partner_content": partner_response.content if partner_response else "",
            "partner_name": partner_name,
            "session_id": str(card_session.id),
        }

    # 情況 C: 我回答了，正在等伴侶
    if my_response:
        return {
            "state": "WAITING_PARTNER",
            "card": target_card,
            "my_content": my_response.content,
            "partner_name": partner_name,
            "session_id": str(card_session.id),
        }

    # 情況 D: 伴侶先回答了
    if card_session.status == CardSessionStatus.WAITING_PARTNER:
        return {
            "state": "PARTNER_STARTED",
            "card": target_card,
            "partner_name": partner_name,
            "session_id": str(card_session.id),
        }

    # 情況 E: 剛抽卡，雙方都還沒回
    return {
        "state": "IDLE",
        "card": target_card,
        "partner_name": partner_name,
        "session_id": str(card_session.id),
    }


# --- 2. 抽卡 API ---
@router.get("/draw", response_model=CardRead)
def draw_card(
    session: SessionDep,
    current_user: CurrentUser,
    category: Optional[str] = None,
    source: DrawSource = Query(DrawSource.LIBRARY),
    preferred_depth: Optional[int] = Query(None, ge=1, le=3),
):
    """
    抽卡邏輯：支援 daily_ritual (使用 Session) 與 library (一般抽卡)。
    """
    card_draw_quota_limit = resolve_quota_limit(
        session=session,
        user_id=current_user.id,
        feature="card_draws_per_day",
    )
    # 模式 A: 每日儀式
    normalized_category = normalize_category_or_raise(category)

    if source == DrawSource.DAILY_RITUAL:
        start_of_day, end_of_day = get_today_range()

        # Lock the User row (SELECT FOR UPDATE) to serialize concurrent
        # daily ritual draws between partners.  Without this, two requests
        # arriving at the same time would both see "no existing session"
        # and each create a duplicate CardSession (TOCTOU race).
        session.exec(
            select(User)
            .where(User.id == current_user.id)
            .with_for_update()
        ).first()

        existing_session = session.exec(
            select(CardSession).where(
                CardSession.mode == CardSessionMode.DAILY_RITUAL,
                or_(
                    CardSession.creator_id == current_user.id,
                    CardSession.partner_id == current_user.id
                ),
                CardSession.created_at >= start_of_day,
                CardSession.created_at <= end_of_day,
                CardSession.deleted_at.is_(None),
            ).order_by(col(CardSession.created_at).desc())
        ).first()

        if existing_session:
            existing_card = session.get(Card, existing_session.card_id)
            if not existing_card:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="找不到相關卡片",
                )
            return existing_card

        draw_allowed, _ = consume_daily_quota(
            session=session,
            user_id=current_user.id,
            feature_key="card_draws_per_day",
            quota_limit=card_draw_quota_limit,
        )
        if not draw_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current plan card quota reached. Upgrade plan to continue.",
            )

        # 每日儀式若無 Session 則按深度漸進抽一張
        cat_filter = normalized_category or CardCategory.DAILY_VIBE.value
        answered_count = _count_answered_cards_in_daily_ritual(
            session,
            user_id=current_user.id,
            category_filter=cat_filter,
        )
        start_depth_cap = resolve_effective_depth_cap(answered_count, preferred_depth)

        new_card = None
        for depth_cap in iter_depth_caps(start_depth_cap):
            new_card = _pick_daily_card_with_depth_cap(
                session,
                category_filter=cat_filter,
                depth_cap=depth_cap,
            )
            if new_card:
                break

        # 如果該分類沒卡，退回全分類抽卡
        if not new_card:
            new_card = session.exec(
                select(Card)
                .where(or_(Card.depth_level.is_(None), Card.depth_level <= 3))
                .order_by(func.random())
            ).first()

        if not new_card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到相關卡片",
            )

        # 建立今日 Session (使用雙向驗證過的 partner_id)
        verified_daily_pid = verify_active_partner_id(session=session, current_user=current_user)
        new_session = CardSession(
            card_id=new_card.id,
            creator_id=current_user.id,
            partner_id=verified_daily_pid,
            category=new_card.category,
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.PENDING
        )
        session.add(new_session)
        commit_with_error_handling(
            session,
            logger=logger,
            action="Draw daily ritual card",
            conflict_detail="建立每日抽卡記錄時發生衝突，請重試。",
            failure_detail="建立每日抽卡記錄失敗，請稍後再試。",
        )
        # CUJ SLI: track ritual draw
        emit_cuj_event(
            session=session,
            user_id=current_user.id,
            event_name=EVENT_RITUAL_DRAW,
            source="server",
            session_id=new_session.id,
        )
        return new_card

    # 模式 B: 圖書館/探索牌組 一般抽卡
    else:
        # 如果有伴侶（雙向驗證），先檢查是否有「伴侶抽了但我還沒回」的卡片
        verified_pid = verify_active_partner_id(session=session, current_user=current_user)
        if verified_pid:
            my_responded_card_ids = select(CardResponse.card_id).where(
                CardResponse.user_id == current_user.id,
                CardResponse.session_id.is_(None),
                CardResponse.deleted_at.is_(None),
            )
            partner_pending_card_ids = select(CardResponse.card_id).where(
                CardResponse.user_id == verified_pid,
                CardResponse.status == ResponseStatus.PENDING,
                CardResponse.session_id.is_(None),
                col(CardResponse.card_id).not_in(my_responded_card_ids),
                CardResponse.deleted_at.is_(None),
            )
            partner_pending_statement = select(Card).where(
                col(Card.id).in_(partner_pending_card_ids)
            )
            if normalized_category:
                partner_pending_statement = partner_pending_statement.where(
                    Card.category == normalized_category
                )
            
            backlog_card = session.exec(partner_pending_statement).first()
            if backlog_card:
                return backlog_card

        # MON-01: Library draw consumes daily quota (same feature key as daily ritual)
        draw_allowed, _ = consume_daily_quota(
            session=session,
            user_id=current_user.id,
            feature_key="card_draws_per_day",
            quota_limit=card_draw_quota_limit,
        )
        if not draw_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current plan card quota reached. Upgrade plan to continue.",
            )

        # 正常抽卡：先依深度漸進，若該深度無可用題目再升級深度
        answered_count = _count_answered_cards_in_library(
            session,
            user_id=current_user.id,
            normalized_category=normalized_category,
        )
        start_depth_cap = resolve_effective_depth_cap(answered_count, preferred_depth)

        result = None
        for depth_cap in iter_depth_caps(start_depth_cap):
            result = _pick_unanswered_library_card(
                session,
                user_id=current_user.id,
                normalized_category=normalized_category,
                depth_cap=depth_cap,
            )
            if result:
                break

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="你已經玩完這個分類的所有卡片了！",
            )
        return result


# --- 3. 回答卡片 API (🔥🔥 關鍵修復：解決解鎖不穩定的問題) ---
@router.post("/respond", response_model=CardResponseRead)
async def respond_to_card(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: Request,
    card_in: CardResponseCreate,
) -> Any:
    # P2-F: idempotency for offline replay (RFC-004)
    idem_key = normalize_idempotency_key(request.headers.get("Idempotency-Key"), None)
    if idem_key:
        replayed = get_replayed_response(session, current_user.id, idem_key)
        if replayed is not None:
            return JSONResponse(
                content=replayed,
                headers={"X-Idempotency-Replayed": "true"},
            )

    cleaned_content = card_in.content.strip()
    if not cleaned_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="回答內容不能為空白。",
        )

    target_card = session.get(Card, card_in.card_id)
    if not target_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到指定卡片",
        )

    # 1. 嘗試找出關聯的每日儀式 Session
    start_of_day, _end_of_day = get_today_range()
    card_session = session.exec(
        select(CardSession).where(
            CardSession.mode == CardSessionMode.DAILY_RITUAL,
            CardSession.card_id == card_in.card_id,
            or_(
                CardSession.creator_id == current_user.id,
                CardSession.partner_id == current_user.id
            ),
            # 這裡稍微放寬時間，避免跨日邊界的問題，或者可以直接拿最近的一筆
            CardSession.created_at >= start_of_day,
            CardSession.deleted_at.is_(None),
        ).order_by(col(CardSession.created_at).desc())
    ).first()

    # 2. 讀取目前 user/partner 的既有回覆，並隔離 daily vs library/deck 的資料範圍
    def get_existing_response_for_user(target_user_id: Optional[uuid.UUID]) -> Optional[CardResponse]:
        if not target_user_id:
            return None

        if card_session:
            in_session = session.exec(
                select(CardResponse)
                .where(
                    CardResponse.user_id == target_user_id,
                    CardResponse.session_id == card_session.id,
                    CardResponse.deleted_at.is_(None),
                )
                .order_by(col(CardResponse.created_at).desc())
            ).first()
            if in_session:
                return in_session

            # 向後相容：舊資料可能沒有 session_id，僅在今日範圍內 fallback。
            return session.exec(
                select(CardResponse)
                .where(
                    CardResponse.user_id == target_user_id,
                    CardResponse.card_id == card_in.card_id,
                    CardResponse.session_id.is_(None),
                    CardResponse.created_at >= start_of_day,
                    CardResponse.deleted_at.is_(None),
                )
                .order_by(col(CardResponse.created_at).desc())
            ).first()

        # library 模式僅使用未綁定 session_id 的回覆，避免污染 deck/daily 資料。
        return session.exec(
            select(CardResponse)
            .where(
                CardResponse.user_id == target_user_id,
                CardResponse.card_id == card_in.card_id,
                CardResponse.session_id.is_(None),
                CardResponse.deleted_at.is_(None),
            )
            .order_by(col(CardResponse.created_at).desc())
        ).first()

    existing_response = get_existing_response_for_user(current_user.id)
    partner_response = get_existing_response_for_user(current_user.partner_id)
    is_new_response = existing_response is None

    # P2-F P1: LWW — if updating and client timestamp older than server, 409
    client_ts_ms = parse_client_timestamp(request.headers.get(HEADER_CLIENT_TS))
    if existing_response is not None and client_ts_ms is not None:
        if not lww_newer_is_client(client_ts_ms, existing_response.created_at):
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
            partner_id=current_user.partner_id,
            client_ip=client_ip,
            device_id=device_id,
            ip_limit_count=settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT,
            device_limit_count=settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT,
            partner_pair_limit_count=settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT,
            endpoint="/api/cards/respond",
        )

    if existing_response:
        # 更新答案
        existing_response.content = cleaned_content
        session.add(existing_response)
        new_response = existing_response
    else:
        # 建立新答案
        new_response = CardResponse(
            card_id=card_in.card_id,
            user_id=current_user.id,
            content=cleaned_content,
            status=ResponseStatus.PENDING,
            is_initiator=partner_response is None
        )
        session.add(new_response)

    # 3. 如果找到 session，把 session_id 補進 response (有助於隔離 daily/deck 流程)
    if card_session and not new_response.session_id:
        new_response.session_id = card_session.id
        session.add(new_response)

    # 4. 判斷狀態變更與廣播標記
    should_broadcast_reveal = False
    should_broadcast_waiting = False
    should_queue_reveal_notification = False

    # (A) 如果有 Session (每日儀式邏輯)
    if card_session:
        if card_session.status == CardSessionStatus.PENDING:
            # 我是第一個回答的
            card_session.status = CardSessionStatus.WAITING_PARTNER
            session.add(card_session)
            should_broadcast_waiting = True
            
        elif card_session.status == CardSessionStatus.WAITING_PARTNER:
            # 狀態是等待中，且現在我也回了 -> 檢查是否雙方都齊了
            if partner_response:
                card_session.status = CardSessionStatus.COMPLETED
                new_response.status = ResponseStatus.REVEALED
                partner_response.status = ResponseStatus.REVEALED
                session.add(card_session)
                session.add(partner_response)
                # 我自己的狀態也要更新
                if existing_response:
                     existing_response.status = ResponseStatus.REVEALED
                     session.add(existing_response)
                else:
                     new_response.status = ResponseStatus.REVEALED
                     session.add(new_response)
                
                should_broadcast_reveal = True
                should_queue_reveal_notification = is_new_response

    # (B) 如果沒有 Session (圖書館/一般邏輯)
    else:
        if partner_response:
            # 伴侶已經回過了，現在我也回了 -> 解鎖
            new_response.status = ResponseStatus.REVEALED
            partner_response.status = ResponseStatus.REVEALED
            session.add(partner_response)
            session.add(new_response)
            should_broadcast_reveal = is_new_response
            should_queue_reveal_notification = is_new_response
        elif current_user.partner_id and is_new_response:
            # 我先回，伴侶還沒 -> 通知伴侶有新卡片
            should_broadcast_waiting = True

    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        target_user_id=current_user.partner_id,
        action="CARD_RESPOND",
        resource_type="card",
        resource_id=card_in.card_id,
        metadata={
            "session_id": str(card_session.id) if card_session else None,
            "is_new_response": is_new_response,
            "broadcast_reveal": should_broadcast_reveal,
        },
    )

    # 🔥🔥🔥 關鍵步驟：先寫入資料庫！ 🔥🔥🔥
    commit_with_error_handling(
        session,
        logger=logger,
        action="Respond to card",
        conflict_detail="卡片回覆發生衝突，請重試。",
        failure_detail="儲存卡片回覆失敗，請稍後再試。",
    )
    session.refresh(new_response)

    # CUJ SLI: track ritual respond
    emit_cuj_event(
        session=session,
        user_id=current_user.id,
        event_name=EVENT_RITUAL_RESPOND,
        source="server",
        session_id=card_session.id if card_session else None,
    )
    # CUJ SLI: track ritual unlock when both partners are done
    if should_broadcast_reveal:
        emit_cuj_event(
            session=session,
            user_id=current_user.id,
            event_name=EVENT_RITUAL_UNLOCK,
            source="server",
            session_id=card_session.id if card_session else None,
        )

    # 5. 資料庫確認寫入後，再發送 WebSocket
    # 這樣前端收到通知來撈資料時，才撈得到最新的狀態
    
    # 準備廣播 payload
    broadcast_payload = {
        "event": "CARD_REVEALED",
        "card_id": str(card_in.card_id),
        "session_id": str(card_session.id) if card_session else None,
        "message": "雙方皆已完成，卡片已解鎖！"
    }
    dedupe_scope_id = card_session.id if card_session else card_in.card_id

    if should_broadcast_reveal:
        logger.info("Card %s revealed. Broadcasting update.", card_in.card_id)
        if current_user.partner_id:
            await manager.send_personal_message(broadcast_payload, str(current_user.partner_id))
        await manager.send_personal_message(broadcast_payload, str(current_user.id))

        if should_queue_reveal_notification:
            _queue_partner_card_notification(
                session=session,
                current_user=current_user,
                action_event="card_revealed",
                scope_id=dedupe_scope_id,
                source_session_id=card_session.id if card_session else None,
            )

    elif should_broadcast_waiting and current_user.partner_id:
        logger.info("Notify partner %s for pending card response", current_user.partner_id)
        await manager.send_personal_message(
            {
                "event": "NEW_CARD_PICKED", 
                "session_id": str(card_session.id) if card_session else None,
                "message": f"{current_user.full_name or '對方'} 已經寫好了卡片！"
            },
            str(current_user.partner_id)
        )
        _queue_partner_card_notification(
            session=session,
            current_user=current_user,
            action_event="card_waiting",
            scope_id=dedupe_scope_id,
            source_session_id=card_session.id if card_session else None,
        )

    # P2-F: store idempotency for offline replay
    if idem_key:
        response_payload = CardResponseRead.model_validate(new_response).model_dump(mode="json")
        save_idempotency_response(
            session,
            current_user.id,
            idem_key,
            "card_respond",
            str(new_response.id),
            response_payload,
        )
        commit_with_error_handling(
            session,
            logger=logger,
            action="Save idempotency log",
            conflict_detail="卡片回覆發生衝突，請重試。",
            failure_detail="儲存卡片回覆失敗，請稍後再試。",
        )

    return new_response


# --- 4. 取得所有卡片 (列表用) ---
@router.get("/", response_model=List[CardRead])
def read_cards(
    session: SessionDep,
    _current_user: CurrentUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    category: Optional[str] = None,
):
    normalized_category = normalize_category_or_raise(category)
    statement = select(Card)
    if normalized_category:
        statement = statement.where(Card.category == normalized_category)
    return session.exec(statement.offset(offset).limit(limit)).all()


# --- 5. 待回覆清單 API ---
@router.get("/backlog", response_model=List[CardRead])
def get_card_backlog(
    session: SessionDep,
    current_user: CurrentUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    if not current_user.partner_id:
        return []

    my_done_ids = select(CardResponse.card_id).where(
        CardResponse.user_id == current_user.id,
        CardResponse.session_id.is_(None),
        CardResponse.deleted_at.is_(None),
    )
    backlog_card_ids = select(CardResponse.card_id).where(
        CardResponse.user_id == current_user.partner_id,
        CardResponse.is_initiator.is_(True),
        CardResponse.session_id.is_(None),
        col(CardResponse.card_id).not_in(my_done_ids),
        CardResponse.deleted_at.is_(None),
    )
    statement = (
        select(Card)
        .where(col(Card.id).in_(backlog_card_ids))
        .order_by(col(Card.id).asc())
        .offset(offset)
        .limit(limit)
    )
    return session.exec(statement).all()


# --- 6. 對話紀錄 API ---
@router.get("/{card_id}/conversation", response_model=List[CardResponseRead])
def get_card_conversation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    card_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> Any:
    user_ids = [current_user.id]
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    if verified_pid:
        user_ids.append(verified_pid)
        
    statement = (
        select(CardResponse)
        .where(CardResponse.card_id == card_id)
        .where(col(CardResponse.user_id).in_(user_ids))
        .where(CardResponse.deleted_at.is_(None))
    )
    if session_id:
        statement = statement.where(CardResponse.session_id == session_id)

    responses = session.exec(
        statement.order_by(col(CardResponse.created_at).asc()).offset(offset).limit(limit)
    ).all()
    
    return responses
