# P2-D: Mediation mode — guided questions and session state.

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Session, select, and_, or_

from app.core.datetime_utils import utcnow
from app.models.mediation_session import MediationSession
from app.models.mediation_answer import MediationAnswer

logger = logging.getLogger(__name__)

# 調解模式引導式問題（幫助換位思考）
MEDIATION_GUIDED_QUESTIONS = [
    "此刻你最希望對方理解的是什麼？",
    "如果換成對方的角度，你覺得他/她可能正在感受什麼？",
    "你願意為這段關係做的一件小事是什麼？",
]


def trigger_mediation(
    session: Session,
    user_id_1: UUID,
    user_id_2: UUID,
    triggered_by_journal_id: UUID,
) -> Optional[MediationSession]:
    """Create a new mediation session for the pair. Returns the session or None on conflict."""
    # Avoid duplicate active session (optional: allow one per pair at a time)
    existing = session.exec(
        select(MediationSession).where(
            or_(
                and_(
                    MediationSession.user_id_1 == user_id_1,
                    MediationSession.user_id_2 == user_id_2,
                ),
                and_(
                    MediationSession.user_id_1 == user_id_2,
                    MediationSession.user_id_2 == user_id_1,
                ),
            ),
            or_(
                MediationSession.user_1_answered_at.is_(None),
                MediationSession.user_2_answered_at.is_(None),
            ),
        )
    ).first()
    if existing:
        logger.info("Mediation session already active for pair, skipping duplicate")
        return existing
    med = MediationSession(
        user_id_1=user_id_1,
        user_id_2=user_id_2,
        triggered_by_journal_id=triggered_by_journal_id,
        created_at=utcnow(),
    )
    session.add(med)
    session.flush()
    return med


def get_mediation_status(
    session: Session,
    current_user_id: UUID,
    partner_id: Optional[UUID],
) -> dict[str, Any]:
    """Return in_mediation, questions, my_answered, partner_answered, session_id, my_answers, partner_answers, next_sop (when both answered)."""
    if not partner_id:
        return {"in_mediation": False, "questions": [], "my_answered": False, "partner_answered": False}
    uid1, uid2 = min(current_user_id, partner_id), max(current_user_id, partner_id)
    med = session.exec(
        select(MediationSession).where(
            MediationSession.user_id_1 == uid1,
            MediationSession.user_id_2 == uid2,
            or_(
                MediationSession.user_1_answered_at.is_(None),
                MediationSession.user_2_answered_at.is_(None),
            ),
        ).order_by(MediationSession.created_at.desc()).limit(1)
    ).first()
    if not med:
        return {"in_mediation": False, "questions": MEDIATION_GUIDED_QUESTIONS, "my_answered": False, "partner_answered": False}
    my_answered = (med.user_1_answered_at is not None) if current_user_id == uid1 else (med.user_2_answered_at is not None)
    partner_answered = (med.user_2_answered_at is not None) if current_user_id == uid1 else (med.user_1_answered_at is not None)
    out: dict[str, Any] = {
        "in_mediation": True,
        "questions": MEDIATION_GUIDED_QUESTIONS,
        "my_answered": my_answered,
        "partner_answered": partner_answered,
        "session_id": str(med.id),
    }
    if my_answered and partner_answered:
        my_uid = current_user_id
        partner_uid = uid2 if current_user_id == uid1 else uid1
        my_row = session.exec(
            select(MediationAnswer).where(
                MediationAnswer.mediation_session_id == med.id,
                MediationAnswer.user_id == my_uid,
            )
        ).first()
        partner_row = session.exec(
            select(MediationAnswer).where(
                MediationAnswer.mediation_session_id == med.id,
                MediationAnswer.user_id == partner_uid,
            )
        ).first()
        out["my_answers"] = [my_row.answer_1, my_row.answer_2, my_row.answer_3] if my_row else []
        out["partner_answers"] = [partner_row.answer_1, partner_row.answer_2, partner_row.answer_3] if partner_row else []
        out["next_sop"] = _build_next_sop()
    return out


def _build_next_sop() -> str:
    """Simple rule-based SOP (per docs/ai-safety/ai-guardrails.md: no judgment/diagnosis)."""
    return "下次衝突時：先暫停、各自冷靜 5 分鐘、再輪流用「我訊息」說一句。"


def record_mediation_answers(
    session: Session,
    mediation_session_id: UUID,
    user_id: UUID,
    answers: list[str] | None = None,
) -> bool:
    """Mark that user has submitted answers; store answer text if provided (len 3). Returns True if updated."""
    med = session.get(MediationSession, mediation_session_id)
    if not med:
        return False
    now = utcnow()
    if med.user_id_1 == user_id:
        med.user_1_answered_at = now
    elif med.user_id_2 == user_id:
        med.user_2_answered_at = now
    else:
        return False
    session.add(med)
    if answers is not None and len(answers) >= 3:
        a1, a2, a3 = (answers[0] or "")[:2000], (answers[1] or "")[:2000], (answers[2] or "")[:2000]
        existing = session.exec(
            select(MediationAnswer).where(
                MediationAnswer.mediation_session_id == mediation_session_id,
                MediationAnswer.user_id == user_id,
            )
        ).first()
        if existing:
            existing.answer_1, existing.answer_2, existing.answer_3 = a1, a2, a3
            session.add(existing)
        else:
            session.add(
                MediationAnswer(
                    mediation_session_id=mediation_session_id,
                    user_id=user_id,
                    answer_1=a1,
                    answer_2=a2,
                    answer_3=a3,
                )
            )
    return True
