# Module B1: Daily sync API (mood + daily question; unlock when both filled).

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.api.error_handling import commit_with_error_handling
from app.models.daily_sync import DailySync
from app.schemas.daily_sync import DailySyncCreate, DailySyncStatusPublic

logger = logging.getLogger(__name__)

router = APIRouter(tags=["daily-sync"])

# Rotate by day of week (0=Monday, 6=Sunday)
DAILY_QUESTIONS = [
    ("q0", "今天發生最好笑的事？"),
    ("q1", "今天最感謝對方的一件事？"),
    ("q2", "今天想跟對方說的一句話？"),
    ("q3", "今天關係裡的一個小亮點？"),
    ("q4", "明天想一起做的一件小事？"),
    ("q5", "這週最想被支持的方式？"),
    ("q6", "今天想被怎麼愛？"),
]


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _get_today_question() -> tuple[str, str]:
    idx = _today_utc().weekday() % len(DAILY_QUESTIONS)
    return DAILY_QUESTIONS[idx]


@router.get("/status", response_model=DailySyncStatusPublic)
def get_daily_sync_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> DailySyncStatusPublic:
    """Return today's sync status; if both filled, include partner's mood and answer."""
    today = _today_utc()
    q_id, q_label = _get_today_question()

    my_row = session.exec(
        select(DailySync).where(
            DailySync.user_id == current_user.id,
            DailySync.sync_date == today,
        )
    ).first()
    partner_row = None
    if current_user.partner_id:
        partner_row = session.exec(
            select(DailySync).where(
                DailySync.user_id == current_user.partner_id,
                DailySync.sync_date == today,
            )
        ).first()
    unlocked = my_row is not None and partner_row is not None
    return DailySyncStatusPublic(
        today=today,
        my_filled=my_row is not None,
        partner_filled=partner_row is not None,
        unlocked=unlocked,
        my_mood_score=my_row.mood_score if my_row else None,
        my_question_id=my_row.question_id if my_row else None,
        my_answer_text=my_row.answer_text if my_row else None,
        partner_mood_score=partner_row.mood_score if unlocked and partner_row else None,
        partner_question_id=partner_row.question_id if unlocked and partner_row else None,
        partner_answer_text=partner_row.answer_text if unlocked and partner_row else None,
        today_question_id=q_id,
        today_question_label=q_label,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_daily_sync(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: DailySyncCreate,
) -> dict:
    """Submit today's mood and daily question answer. One per user per day."""
    if not (1 <= body.mood_score <= 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mood_score must be between 1 and 5",
        )
    today = _today_utc()
    q_id, _ = _get_today_question()
    if body.question_id != q_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question_id does not match today's question",
        )
    answer_text = (body.answer_text or "").strip()[:1000]
    existing = session.exec(
        select(DailySync).where(
            DailySync.user_id == current_user.id,
            DailySync.sync_date == today,
        )
    ).first()
    if existing:
        existing.mood_score = body.mood_score
        existing.answer_text = answer_text
        session.add(existing)
    else:
        row = DailySync(
            user_id=current_user.id,
            sync_date=today,
            mood_score=body.mood_score,
            question_id=body.question_id,
            answer_text=answer_text,
        )
        session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Submit daily sync",
        conflict_detail="儲存時發生衝突，請稍後再試。",
        failure_detail="儲存失敗，請稍後再試。",
    )
    return {"status": "ok", "message": "已儲存今日同步"}
