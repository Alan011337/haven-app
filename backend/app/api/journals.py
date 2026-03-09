# backend/app/api/journals.py

from datetime import timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_
from sqlmodel import col, select
import uuid
import logging

from app.models.journal import Journal
from app.models.analysis import Analysis 
from app.schemas.journal import JournalCreate
from app.api.deps import CurrentUser, ReadSessionDep, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling, flush_with_error_handling
from app.core.config import settings
from app.services.ai import analyze_journal 
from app.services.ai_persona import infer_relationship_weather
from app.services.notification import queue_partner_notification
from app.services.notification_payloads import build_partner_notification_payload
from app.services.request_identity import resolve_client_ip, resolve_device_id
from app.services.rate_limit import enforce_journal_create_rate_limit
from app.services.entitlement_runtime import resolve_quota_limit
from app.services.entitlement_usage_runtime import consume_daily_quota
from app.services.audit_log import record_audit_event, record_audit_event_best_effort
from app.models.audit_event import AuditEventOutcome
from app.services.trace_span import trace_span
from app.core.log_redaction import redact_content
from app.services.gamification import apply_journal_score_once, compute_journal_score_delta
from app.queue import is_async_journal_analysis_enabled, enqueue_journal_analysis
from app.middleware.request_context import request_id_var
from app.services.cuj_event_emitter import emit_cuj_event
from app.services.cuj_sli_runtime import (
    EVENT_JOURNAL_SUBMIT,
    EVENT_JOURNAL_PERSIST,
    EVENT_JOURNAL_ANALYSIS_QUEUED,
    EVENT_JOURNAL_ANALYSIS_DELIVERED,
)
from app.core.datetime_utils import utcnow
from app.core.settings_domains import get_timeline_cursor_settings
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
from app.services.pagination import (
    InvalidPageCursorError,
    PageCursor,
    enforce_timeline_query_budget,
    estimate_timeline_query_budget,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_DYNAMIC_CONTEXT_LOOKBACK_HOURS = 48
_DYNAMIC_CONTEXT_MAX_SAMPLES = 6


def _resolve_relationship_weather_hint(
    *,
    session: SessionDep,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
) -> str | None:
    if not settings.AI_DYNAMIC_CONTEXT_INJECTION_ENABLED:
        return None

    user_ids: list[uuid.UUID] = [current_user_id]
    if partner_user_id:
        user_ids.append(partner_user_id)

    window_floor = utcnow() - timedelta(hours=_DYNAMIC_CONTEXT_LOOKBACK_HOURS)
    recent_contents = session.exec(
        select(Journal.content)
        .where(
            col(Journal.user_id).in_(user_ids),
            Journal.deleted_at.is_(None),
            Journal.created_at >= window_floor,
        )
        .order_by(col(Journal.created_at).desc())
        .limit(_DYNAMIC_CONTEXT_MAX_SAMPLES)
    ).all()

    conflict_count = 0
    repair_count = 0
    for content in recent_contents:
        weather = infer_relationship_weather(str(content or ""))
        if weather == "conflict":
            conflict_count += 1
        elif weather == "repair":
            repair_count += 1

    if conflict_count == repair_count:
        return None
    return "conflict" if conflict_count > repair_count else "repair"


def _queue_partner_journal_notification(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    journal_id: uuid.UUID,
) -> None:
    payload = build_partner_notification_payload(
        session=session,
        sender_user=current_user,
        event_type="journal",
        scope_id=journal_id,
        source_session_id=journal_id,
    )
    if not payload:
        return

    queue_partner_notification(
        action_type="journal",
        **payload,
    )

# 1. 寫日記 (Create) - 含計分與通知
@router.post("/", response_model=Dict[str, Any]) # 修正回傳型別以容納分數
async def create_journal( 
    journal_data: JournalCreate, 
    session: SessionDep,
    current_user: CurrentUser,
    request: Request,
):
    # P2-F: idempotency for offline replay (RFC-004)
    idem_key = normalize_idempotency_key(
        request.headers.get("Idempotency-Key"),
        request.headers.get("X-Request-Id"),
    )
    if idem_key:
        replayed = get_replayed_response(session, current_user.id, idem_key)
        if replayed is not None:
            return JSONResponse(
                content=replayed,
                headers={"X-Idempotency-Replayed": "true"},
            )

    # P2-F P1: LWW conflict — same user + same UTC day journal
    client_ts_ms = parse_client_timestamp(request.headers.get(HEADER_CLIENT_TS))
    if client_ts_ms is not None:
        from datetime import timezone
        from datetime import datetime as dt_class
        ref_date = dt_class.fromtimestamp(client_ts_ms / 1000.0, tz=timezone.utc).date()
        day_start_utc = dt_class(ref_date.year, ref_date.month, ref_date.day, tzinfo=timezone.utc).replace(tzinfo=None)
        day_end_utc = day_start_utc + timedelta(days=1)
        existing_same_day = session.exec(
            select(Journal)
            .where(
                Journal.user_id == current_user.id,
                Journal.deleted_at.is_(None),
                Journal.created_at >= day_start_utc,
                Journal.created_at < day_end_utc,
            )
        ).first()
        if existing_same_day is not None:
            if lww_newer_is_client(client_ts_ms, existing_same_day.updated_at):
                existing_same_day.content = journal_data.content
                existing_same_day.updated_at = utcnow()
                session.add(existing_same_day)
                flush_with_error_handling(
                    session,
                    logger=logger,
                    action="LWW update journal",
                    conflict_detail="日記資料衝突，請重試。",
                    failure_detail="更新日記失敗，請稍後再試。",
                )
                commit_with_error_handling(
                    session,
                    logger=logger,
                    action="Commit LWW journal",
                    conflict_detail="日記資料衝突，請重試。",
                    failure_detail="寫入日記失敗，請稍後再試。",
                )
                session.refresh(existing_same_day)
                if is_async_journal_analysis_enabled():
                    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)
                    relationship_mode = "paired" if verified_partner_id else "solo"
                    relationship_weather_hint = _resolve_relationship_weather_hint(
                        session=session,
                        current_user_id=current_user.id,
                        partner_user_id=verified_partner_id,
                    )
                    enqueue_journal_analysis(
                        journal_id=existing_same_day.id,
                        user_id=current_user.id,
                        relationship_weather_hint=relationship_weather_hint,
                        relationship_mode=relationship_mode,
                    )
                response_data = existing_same_day.model_dump()
                response_data["new_savings_score"] = current_user.savings_score
                response_data["score_gained"] = 0
                if idem_key:
                    save_idempotency_response(
                        session,
                        current_user.id,
                        idem_key,
                        "journal_create",
                        str(existing_same_day.id),
                        response_data,
                    )
                    commit_with_error_handling(
                        session,
                        logger=logger,
                        action="Save idempotency log",
                        conflict_detail="日記資料衝突，請重試。",
                        failure_detail="寫入日記失敗，請稍後再試。",
                    )
                return response_data
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已由其他裝置更新，以伺服器為準。",
                    headers={"X-Conflict-Code": "CONFLICT_LWW"},
                )

    journal_quota_limit = resolve_quota_limit(
        session=session,
        user_id=current_user.id,
        feature="journals_per_day",
    )
    journal_allowed, _ = consume_daily_quota(
        session=session,
        user_id=current_user.id,
        feature_key="journals_per_day",
        quota_limit=journal_quota_limit,
    )
    if not journal_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current plan journal quota reached. Upgrade plan to continue.",
        )

    client_ip = resolve_client_ip(request)
    device_id = resolve_device_id(
        request,
        header_name=settings.RATE_LIMIT_DEVICE_HEADER,
    )
    enforce_journal_create_rate_limit(
        session=session,
        user_id=current_user.id,
        limit_count=settings.JOURNAL_RATE_LIMIT_COUNT,
        window_seconds=settings.JOURNAL_RATE_LIMIT_WINDOW_SECONDS,
        partner_id=current_user.partner_id,
        client_ip=client_ip,
        device_id=device_id,
        ip_limit_count=settings.JOURNAL_RATE_LIMIT_IP_COUNT,
        device_limit_count=settings.JOURNAL_RATE_LIMIT_DEVICE_COUNT,
        partner_pair_limit_count=settings.JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT,
        endpoint="/api/journals/",
    )

    # CUJ SLI: track journal submit intent (same request_id for full journal stage timeline; use X-Request-Id when client sends it)
    journal_request_id = (request_id_var.get() or "").strip() or str(uuid.uuid4())
    emit_cuj_event(
        session=session,
        user_id=current_user.id,
        event_name=EVENT_JOURNAL_SUBMIT,
        source="server",
        request_id=journal_request_id,
    )

    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    relationship_mode = "paired" if verified_partner_id else "solo"
    relationship_weather_hint = _resolve_relationship_weather_hint(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=verified_partner_id,
    )

    # P2-B QUEUE-01: Async path — write journal only, enqueue analysis/notify; return immediately
    if is_async_journal_analysis_enabled():
        emit_cuj_event(
            session=session,
            user_id=current_user.id,
            event_name=EVENT_JOURNAL_ANALYSIS_QUEUED,
            source="server",
            request_id=journal_request_id,
        )
        try:
            new_journal = Journal(
                content=journal_data.content,
                user_id=current_user.id,
            )
            session.add(new_journal)
            flush_with_error_handling(
                session,
                logger=logger,
                action="Create journal",
                conflict_detail="日記資料衝突，請重試。",
                failure_detail="建立日記失敗，請稍後再試。",
            )
            logger.info("日記本體已暫存 (ID: %s)", new_journal.id)
            record_audit_event(
                session=session,
                actor_user_id=current_user.id,
                action="JOURNAL_CREATE",
                resource_type="journal",
                resource_id=new_journal.id,
                metadata={"has_analysis": False, "async_queued": True},
            )
            commit_with_error_handling(
                session,
                logger=logger,
                action="Finalize journal",
                conflict_detail="日記資料衝突，請重試。",
                failure_detail="寫入日記失敗，請稍後再試。",
            )
            session.refresh(new_journal)
            enqueue_journal_analysis(
                journal_id=new_journal.id,
                user_id=current_user.id,
                relationship_weather_hint=relationship_weather_hint,
                relationship_mode=relationship_mode,
            )
            emit_cuj_event(
                session=session,
                user_id=current_user.id,
                event_name=EVENT_JOURNAL_PERSIST,
                source="server",
                request_id=journal_request_id,
                metadata={"journal_write_ms": 0, "async": True},
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Unexpected error when writing journal (async): reason=%s", type(exc).__name__)
            session.rollback()
            record_audit_event_best_effort(
                session=session,
                actor_user_id=current_user.id,
                action="JOURNAL_CREATE_ERROR",
                resource_type="journal",
                outcome=AuditEventOutcome.ERROR,
                reason=exc.__class__.__name__,
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="寫入日記時發生錯誤，請稍後再試。"
            )
        response_data = new_journal.model_dump()
        response_data["new_savings_score"] = current_user.savings_score
        response_data["score_gained"] = 0
        if idem_key:
            save_idempotency_response(
                session,
                current_user.id,
                idem_key,
                "journal_create",
                str(new_journal.id),
                response_data,
            )
            commit_with_error_handling(
                session,
                logger=logger,
                action="Save idempotency log",
                conflict_detail="日記資料衝突，請重試。",
                failure_detail="寫入日記失敗，請稍後再試。",
            )
        return response_data

    # 步驟 1: 先執行 AI 分析 (sync path when queue not enabled)
    ai_failed = False
    logger.info(
        "開始 AI 分析日記內容 preview=%s",
        redact_content(journal_data.content, max_visible=10),
    )
    emit_cuj_event(
        session=session,
        user_id=current_user.id,
        event_name=EVENT_JOURNAL_ANALYSIS_QUEUED,
        source="server",
        request_id=journal_request_id,
    )
    analysis_start_ms = int(utcnow().timestamp() * 1000)
    try:
        with trace_span("api.journals.create.ai_analyze", user_id=str(current_user.id)):
            ai_result = await analyze_journal(
                journal_data.content,
                relationship_weather_hint=relationship_weather_hint,
                relationship_mode=relationship_mode,
            )
        analysis_lag_ms = int(utcnow().timestamp() * 1000) - analysis_start_ms
        emit_cuj_event(
            session=session,
            user_id=current_user.id,
            event_name=EVENT_JOURNAL_ANALYSIS_DELIVERED,
            source="server",
            request_id=journal_request_id,
            metadata={"analysis_async_lag_ms": analysis_lag_ms},
        )
        logger.info("AI 分析完成")
    except Exception as e:
        logger.error("AI Service Error: %s", type(e).__name__)
        ai_result = {}
        ai_failed = True

    # 步驟 2: 資料庫寫入
    try:
        # A. 準備日記物件
        new_journal = Journal(
            content=journal_data.content,
            user_id=current_user.id,
        )
        session.add(new_journal)
        flush_with_error_handling(
            session,
            logger=logger,
            action="Create journal",
            conflict_detail="日記資料衝突，請重試。",
            failure_detail="建立日記失敗，請稍後再試。",
        )
        logger.info("日記本體已暫存 (ID: %s)", new_journal.id)

        # B. 準備分析物件 & 計算情感存款 (Gamification Logic) 💰
        new_analysis = None
        score_delta = 0
        score_replay_blocked = False

        if ai_result:
            new_analysis = Analysis(
                journal_id=new_journal.id,
                mood_label=ai_result.get("mood_label"),
                emotional_needs=ai_result.get("emotional_needs"),
                advice_for_user=ai_result.get("advice_for_user"),
                action_for_user=ai_result.get("action_for_user"),
                advice_for_partner=ai_result.get("advice_for_partner"),
                action_for_partner=ai_result.get("action_for_partner"),
                card_recommendation=ai_result.get("card_recommendation"),
                safety_tier=ai_result.get("safety_tier", 0),
                prompt_version=ai_result.get("prompt_version", "unknown"),
                model_version=ai_result.get("model_version"),
                parse_success=bool(ai_result.get("parse_success", False)),
            )
            session.add(new_analysis)
            score_candidate = compute_journal_score_delta(ai_result)
        else:
            # AI exception: do NOT grant free points (data integrity).
            # Normal fallback responses from ai.py are non-empty dicts
            # and go through the `if ai_result:` branch above.
            score_candidate = 0

        if score_candidate > 0:
            score_apply_result = apply_journal_score_once(
                session=session,
                current_user=current_user,
                journal_id=new_journal.id,
                journal_content=journal_data.content,
                event_at=new_journal.created_at,
                candidate_delta=score_candidate,
            )
            score_delta = score_apply_result.applied_delta
            score_replay_blocked = score_apply_result.replay_blocked
            if score_delta > 0:
                logger.info("情感存款 +%s (New Total: %s)", score_delta, current_user.savings_score)
            elif score_replay_blocked:
                logger.info(
                    "情感存款 replay blocked user_id=%s journal_id=%s",
                    current_user.id,
                    new_journal.id,
                )

        record_audit_event(
            session=session,
            actor_user_id=current_user.id,
            action="JOURNAL_CREATE",
            resource_type="journal",
            resource_id=new_journal.id,
            metadata={
                "score_gained": score_delta,
                "score_candidate": score_candidate,
                "score_replay_blocked": score_replay_blocked,
                "has_analysis": bool(new_analysis),
                "ai_failed": ai_failed,
            },
        )

        # C. 提交變更
        with trace_span("api.journals.create.db_commit", user_id=str(current_user.id)):
            commit_with_error_handling(
                session,
                logger=logger,
                action="Finalize journal",
                conflict_detail="日記資料衝突，請重試。",
                failure_detail="寫入日記失敗，請稍後再試。",
            )

        # CUJ SLI: track journal persist success
        persist_lag_ms = int(utcnow().timestamp() * 1000) - analysis_start_ms
        emit_cuj_event(
            session=session,
            user_id=current_user.id,
            event_name=EVENT_JOURNAL_PERSIST,
            source="server",
            request_id=journal_request_id,
            metadata={"journal_write_ms": persist_lag_ms},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error when writing journal: reason=%s", type(exc).__name__)
        session.rollback()
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            action="JOURNAL_CREATE_ERROR",
            resource_type="journal",
            outcome=AuditEventOutcome.ERROR,
            reason=exc.__class__.__name__,
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="寫入日記時發生錯誤，請稍後再試。"
        )
        
    # D. 重新整理物件
    session.refresh(new_journal)
    if new_analysis:
        session.refresh(new_analysis)

    # 步驟 3: 發送通知 (Notification Loop)
    if current_user.partner_id:
        try:
            _queue_partner_journal_notification(
                session=session,
                current_user=current_user,
                journal_id=new_journal.id,
            )
        except Exception as n_err:
            logger.error("通知發送流程出錯: %s", type(n_err).__name__)

    # 步驟 4: 建構回傳資料
    response_data = new_journal.model_dump()
    if new_analysis:
        analysis_data = new_analysis.model_dump(exclude={"id", "created_at", "journal_id"})
        response_data.update(analysis_data)
    
    # 加入分數資訊供前端動畫使用
    response_data["new_savings_score"] = current_user.savings_score
    response_data["score_gained"] = score_delta

    # P2-F: store idempotency for offline replay
    if idem_key:
        save_idempotency_response(
            session,
            current_user.id,
            idem_key,
            "journal_create",
            str(new_journal.id),
            response_data,
        )
        commit_with_error_handling(
            session,
            logger=logger,
            action="Save idempotency log",
            conflict_detail="日記資料衝突，請重試。",
            failure_detail="寫入日記失敗，請稍後再試。",
        )

    return response_data

_JOURNAL_LIST_LIMIT_MAX = 100
_JOURNAL_LIST_LIMIT_DEFAULT = 50


def _decode_journal_cursor(cursor_raw: str | None) -> PageCursor:
    if not cursor_raw:
        return PageCursor()
    try:
        return PageCursor.from_encoded(cursor_raw)
    except InvalidPageCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid journal cursor.",
        ) from exc


def _set_journal_next_cursor_header(
    *,
    response: Response,
    rows: list[tuple[Journal, Analysis | None]],
    requested_limit: int,
) -> list[tuple[Journal, Analysis | None]]:
    if len(rows) <= requested_limit:
        return rows
    visible_rows = rows[:requested_limit]
    last_journal = visible_rows[-1][0]
    next_cursor = PageCursor(
        last_timestamp=last_journal.created_at,
        last_id=last_journal.id,
    ).encode()
    if next_cursor:
        response.headers["X-Next-Cursor"] = next_cursor
    return visible_rows


def _resolve_journal_fetch_limit(
    *,
    limit: int,
    offset: int,
    cursor_raw: str | None,
    timeline_settings,
) -> tuple[int, int, bool]:
    safe_limit = enforce_timeline_query_budget(
        fetch_limit=limit,
        budget_units=timeline_settings.query_budget,
        query_fanout=2,
        detail_query_count=1,
    )
    cursor_window_enabled = bool(cursor_raw) or offset == 0
    fetch_limit = safe_limit
    if cursor_window_enabled:
        probe_limit = safe_limit + 1
        probe_budget = estimate_timeline_query_budget(
            fetch_limit=probe_limit,
            query_fanout=2,
            detail_query_count=1,
        )
        if probe_budget <= timeline_settings.query_budget:
            fetch_limit = probe_limit
    return safe_limit, fetch_limit, cursor_window_enabled


def _apply_journal_cursor_or_offset(statement, *, page_cursor: PageCursor, offset: int):
    if page_cursor.last_timestamp:
        cursor_conditions = [col(Journal.created_at) < page_cursor.last_timestamp]
        if page_cursor.last_id:
            cursor_conditions.append(
                and_(
                    col(Journal.created_at) == page_cursor.last_timestamp,
                    col(Journal.id) < page_cursor.last_id,
                )
            )
        return statement.where(or_(*cursor_conditions))
    return statement.offset(offset)

# 2. 讀取「自己」的日記 (支援 limit/offset 分頁) — P2-B: uses read replica when configured
@router.get("/", response_model=List[Dict[str, Any]])
def read_my_journals(
    session: ReadSessionDep,
    current_user: CurrentUser,
    limit: int = Query(_JOURNAL_LIST_LIMIT_DEFAULT, ge=1, le=_JOURNAL_LIST_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(default=None),
    response: Response = None,
):
    timeline_settings = get_timeline_cursor_settings()
    if cursor and offset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset cannot be combined with cursor.",
        )
    page_cursor = _decode_journal_cursor(cursor)
    safe_limit, fetch_limit, cursor_window_enabled = _resolve_journal_fetch_limit(
        limit=limit,
        offset=offset,
        cursor_raw=cursor,
        timeline_settings=timeline_settings,
    )

    statement = (
        select(Journal, Analysis)
        .join(Analysis, Journal.id == Analysis.journal_id, isouter=True)
        .where(Journal.user_id == current_user.id)
        .where(Journal.deleted_at.is_(None))  # 🚀 Exclude soft-deleted journals
        .order_by(Journal.created_at.desc())
        .limit(fetch_limit)
    )
    statement = _apply_journal_cursor_or_offset(
        statement,
        page_cursor=page_cursor,
        offset=offset,
    )
    results = session.exec(statement).all()
    if response is not None:
        response.headers["X-Query-Budget-Units"] = str(
            estimate_timeline_query_budget(
                fetch_limit=fetch_limit,
                query_fanout=2,
                detail_query_count=1,
            )
        )
        if safe_limit != limit:
            response.headers["X-Query-Limit-Clamped"] = str(safe_limit)
    if cursor_window_enabled and response is not None:
        results = _set_journal_next_cursor_header(
            response=response,
            rows=results,
            requested_limit=safe_limit,
        )

    journals_list = []
    for journal, analysis in results:
        j_dict = journal.model_dump()
        if analysis:
            j_dict.update(analysis.model_dump(exclude={"id", "created_at", "journal_id"}))
        journals_list.append(j_dict)
        
    return journals_list

# 3. 讀取「伴侶」的日記 — 🚀 已優化：避免 full model_dump，直接存取 ORM 屬性
@router.get("/partner", response_model=List[Dict[str, Any]])
def read_partner_journals(
    session: ReadSessionDep,
    current_user: CurrentUser,
    limit: int = Query(_JOURNAL_LIST_LIMIT_DEFAULT, ge=1, le=_JOURNAL_LIST_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(default=None),
    response: Response = None,
):
    timeline_settings = get_timeline_cursor_settings()
    if cursor and offset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset cannot be combined with cursor.",
        )
    page_cursor = _decode_journal_cursor(cursor)
    safe_limit, fetch_limit, cursor_window_enabled = _resolve_journal_fetch_limit(
        limit=limit,
        offset=offset,
        cursor_raw=cursor,
        timeline_settings=timeline_settings,
    )

    # 雙向驗證：確認配對關係仍然有效 (BOLA 防禦)
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    if not verified_pid:
        # 未綁定或單向殘留，回傳空陣列，讓前端顯示「邀請伴侶」畫面
        return []

    # 查詢伴侶的日記 — 🚀 added deleted_at filter
    statement = (
        select(Journal, Analysis)
        .join(Analysis, Journal.id == Analysis.journal_id, isouter=True)
        .where(Journal.user_id == verified_pid)
        .where(Journal.deleted_at.is_(None))  # 🚀 Exclude soft-deleted
        .order_by(Journal.created_at.desc())
        .limit(fetch_limit)
    )
    statement = _apply_journal_cursor_or_offset(
        statement,
        page_cursor=page_cursor,
        offset=offset,
    )
    results = session.exec(statement).all()
    if response is not None:
        response.headers["X-Query-Budget-Units"] = str(
            estimate_timeline_query_budget(
                fetch_limit=fetch_limit,
                query_fanout=2,
                detail_query_count=1,
            )
        )
        if safe_limit != limit:
            response.headers["X-Query-Limit-Clamped"] = str(safe_limit)
    if cursor_window_enabled and response is not None:
        results = _set_journal_next_cursor_header(
            response=response,
            rows=results,
            requested_limit=safe_limit,
        )

    partner_journals = []

    for journal, analysis in results:
        # 🚀 直接存取 ORM 屬性，避免 full model_dump() 開銷
        item: Dict[str, Any] = {
            "id": str(journal.id),
            "user_id": str(journal.user_id),
            "created_at": journal.created_at,
            "content": "🔒 (內容已加密保護)",  # 隱私保護：不傳送原文
            "mood_label": (analysis.mood_label if analysis and analysis.mood_label else "等待分析..."),
            "emotional_needs": (analysis.emotional_needs if analysis and analysis.emotional_needs else ""),
            "advice_for_partner": (analysis.advice_for_partner if analysis and analysis.advice_for_partner else ""),
            "action_for_partner": (analysis.action_for_partner if analysis and analysis.action_for_partner else ""),
            "card_recommendation": (analysis.card_recommendation if analysis and analysis.card_recommendation else ""),
            "safety_tier": (analysis.safety_tier if analysis and analysis.safety_tier is not None else 0),
        }
        partner_journals.append(item)

    return partner_journals

# 4. 刪除日記 — 🚀 改用 soft-delete，與系統 DATA_SOFT_DELETE lifecycle 一致
@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(
    journal_id: str,
    session: SessionDep,
    current_user: CurrentUser
):
    try:
        j_uuid = uuid.UUID(journal_id)
        journal = session.get(Journal, j_uuid)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無效的 ID 格式")

    # 🚀 Check deleted_at — already soft-deleted items should return 404
    if not journal or journal.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到這篇日記")
    if journal.user_id != current_user.id:
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=journal.user_id,
            action="JOURNAL_DELETE_DENIED",
            resource_type="journal",
            resource_id=journal.id,
            outcome=AuditEventOutcome.DENIED,
            reason="not_owner",
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你沒有權限刪除這篇日記")

    # 🚀 Soft-delete: set deleted_at timestamp instead of hard-deleting.
    # This aligns with DATA_SOFT_DELETE_ENABLED and allows undo / GDPR purge lifecycle.
    journal.deleted_at = utcnow()
    session.add(journal)
    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        action="JOURNAL_DELETE",
        resource_type="journal",
        resource_id=journal.id,
        metadata={"soft_delete": True},
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="Soft-delete journal",
        conflict_detail="刪除日記時發生衝突，請重試。",
        failure_detail="刪除日記失敗，請稍後再試。",
    )
    return None
