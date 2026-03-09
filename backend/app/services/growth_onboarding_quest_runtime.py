from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.card_response import CardResponse
from app.models.journal import Journal
from app.models.user import User
from app.services.feature_flags import resolve_feature_flags

logger = logging.getLogger(__name__)

ONBOARDING_QUEST_STEP_COUNT = 7


@dataclass(frozen=True)
class OnboardingQuestStepProgress:
    key: str
    title: str
    description: str
    quest_day: int
    completed: bool
    reason: str
    dedupe_key: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class OnboardingQuestEvaluation:
    enabled: bool
    kill_switch_active: bool
    has_partner_context: bool
    completed_steps: int
    total_steps: int
    progress_percent: float
    steps: list[OnboardingQuestStepProgress]


def _safe_count(session: Session, statement) -> int:
    value = session.exec(statement).one()
    return int(value or 0)


def _build_dedupe_key(*, user_id: uuid.UUID, key: str) -> str:
    payload = f"{user_id}:{key}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _count_user_journals(*, session: Session, user_id: uuid.UUID) -> int:
    statement = select(func.count(Journal.id)).where(
        Journal.user_id == user_id,
        Journal.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _count_user_card_responses(*, session: Session, user_id: uuid.UUID) -> int:
    statement = select(func.count(CardResponse.id)).where(
        CardResponse.user_id == user_id,
        CardResponse.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _count_pair_card_responses(*, session: Session, user_id: uuid.UUID, partner_id: uuid.UUID) -> int:
    statement = select(func.count(CardResponse.id)).where(
        col(CardResponse.user_id).in_([user_id, partner_id]),
        CardResponse.deleted_at.is_(None),
    )
    return _safe_count(session, statement)


def _extract_journal_days(*, session: Session, user_id: uuid.UUID) -> set[date]:
    rows = session.exec(
        select(Journal.created_at).where(
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
        )
    ).all()
    result: set[date] = set()
    for created_at in rows:
        if created_at is not None:
            result.add(created_at.date())
    return result


def _build_step(
    *,
    user_id: uuid.UUID,
    key: str,
    title: str,
    description: str,
    quest_day: int,
    completed: bool,
    reason: str,
    metadata: dict[str, Any],
) -> OnboardingQuestStepProgress:
    return OnboardingQuestStepProgress(
        key=key,
        title=title,
        description=description,
        quest_day=quest_day,
        completed=completed,
        reason=reason,
        dedupe_key=_build_dedupe_key(user_id=user_id, key=key),
        metadata=metadata,
    )


def evaluate_onboarding_quest(
    *,
    session: Session,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
) -> OnboardingQuestEvaluation:
    has_partner_context = partner_user_id is not None
    resolved = resolve_feature_flags(has_partner=has_partner_context)
    kill_switch_active = bool(resolved.kill_switches.get("disable_growth_onboarding_quest", False))
    feature_enabled = bool(resolved.flags.get("growth_onboarding_quest_enabled", False))

    if not feature_enabled or kill_switch_active:
        growth_onboarding_quest_runtime_metrics.record_evaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            completed_steps=0,
            total_steps=ONBOARDING_QUEST_STEP_COUNT,
        )
        return OnboardingQuestEvaluation(
            enabled=False,
            kill_switch_active=kill_switch_active,
            has_partner_context=has_partner_context,
            completed_steps=0,
            total_steps=ONBOARDING_QUEST_STEP_COUNT,
            progress_percent=0.0,
            steps=[],
        )

    user_terms_accepted = (
        session.exec(
            select(User.terms_accepted_at).where(User.id == current_user_id)
        ).one()
        is not None
    )
    user_journal_count = _count_user_journals(session=session, user_id=current_user_id)
    user_card_response_count = _count_user_card_responses(session=session, user_id=current_user_id)

    if has_partner_context:
        assert partner_user_id is not None
        partner_journal_count = _count_user_journals(session=session, user_id=partner_user_id)
        pair_card_response_count = _count_pair_card_responses(
            session=session,
            user_id=current_user_id,
            partner_id=partner_user_id,
        )
        shared_journal_days = len(
            _extract_journal_days(session=session, user_id=current_user_id).intersection(
                _extract_journal_days(session=session, user_id=partner_user_id)
            )
        )
    else:
        partner_journal_count = 0
        pair_card_response_count = 0
        shared_journal_days = 0

    steps = [
        _build_step(
            user_id=current_user_id,
            key="ACCEPT_TERMS",
            title="完成服務條款同意",
            description="確認帳號已完成最小法遵同意流程。",
            quest_day=1,
            completed=user_terms_accepted,
            reason="eligible" if user_terms_accepted else "terms_not_accepted",
            metadata={
                "terms_accepted": user_terms_accepted,
            },
        ),
        _build_step(
            user_id=current_user_id,
            key="BIND_PARTNER",
            title="完成伴侶綁定",
            description="綁定另一半，開啟雙人任務與同步體驗。",
            quest_day=2,
            completed=has_partner_context,
            reason="eligible" if has_partner_context else "partner_not_bound",
            metadata={
                "has_partner_context": has_partner_context,
            },
        ),
        _build_step(
            user_id=current_user_id,
            key="CREATE_FIRST_JOURNAL",
            title="寫下第一篇日記",
            description="完成首篇 journal，建立關係記錄基線。",
            quest_day=3,
            completed=user_journal_count >= 1,
            reason="eligible" if user_journal_count >= 1 else "journal_missing",
            metadata={
                "user_journal_count": user_journal_count,
                "target": 1,
            },
        ),
        _build_step(
            user_id=current_user_id,
            key="RESPOND_FIRST_CARD",
            title="回覆第一張卡片",
            description="完成第一筆卡片回覆，確保儀式流程可用。",
            quest_day=4,
            completed=user_card_response_count >= 1,
            reason="eligible" if user_card_response_count >= 1 else "card_response_missing",
            metadata={
                "user_card_response_count": user_card_response_count,
                "target": 1,
            },
        ),
        _build_step(
            user_id=current_user_id,
            key="PARTNER_FIRST_JOURNAL",
            title="伴侶完成第一篇日記",
            description="雙方都至少完成 1 篇日記，建立互動閉環。",
            quest_day=5,
            completed=has_partner_context and partner_journal_count >= 1,
            reason=(
                "eligible"
                if has_partner_context and partner_journal_count >= 1
                else ("partner_required" if not has_partner_context else "partner_journal_missing")
            ),
            metadata={
                "partner_journal_count": partner_journal_count,
                "target": 1,
            },
        ),
        _build_step(
            user_id=current_user_id,
            key="PAIR_CARD_EXCHANGE",
            title="完成雙方卡片互動",
            description="雙方合計至少 2 次卡片回覆，驗證雙向互動。",
            quest_day=6,
            completed=has_partner_context and pair_card_response_count >= 2,
            reason=(
                "eligible"
                if has_partner_context and pair_card_response_count >= 2
                else ("partner_required" if not has_partner_context else "pair_card_responses_insufficient")
            ),
            metadata={
                "pair_card_response_count": pair_card_response_count,
                "target": 2,
            },
        ),
        _build_step(
            user_id=current_user_id,
            key="PAIR_STREAK_2_DAYS",
            title="達成 2 天共同連勝",
            description="雙方連續互動至少 2 天，完成 onboarding 轉化。",
            quest_day=7,
            completed=has_partner_context and shared_journal_days >= 2,
            reason=(
                "eligible"
                if has_partner_context and shared_journal_days >= 2
                else ("partner_required" if not has_partner_context else "shared_streak_days_insufficient")
            ),
            metadata={
                "shared_journal_days": shared_journal_days,
                "target": 2,
            },
        ),
    ]

    completed_steps = sum(1 for step in steps if step.completed)
    progress_percent = round((completed_steps / ONBOARDING_QUEST_STEP_COUNT) * 100, 1)

    logger.info(
        "onboarding_quest_evaluated enabled=true has_partner=%s completed_steps=%s total_steps=%s",
        has_partner_context,
        completed_steps,
        ONBOARDING_QUEST_STEP_COUNT,
    )
    growth_onboarding_quest_runtime_metrics.record_evaluation(
        enabled=True,
        has_partner_context=has_partner_context,
        completed_steps=completed_steps,
        total_steps=ONBOARDING_QUEST_STEP_COUNT,
    )
    return OnboardingQuestEvaluation(
        enabled=True,
        kill_switch_active=False,
        has_partner_context=has_partner_context,
        completed_steps=completed_steps,
        total_steps=ONBOARDING_QUEST_STEP_COUNT,
        progress_percent=progress_percent,
        steps=steps,
    )


class GrowthOnboardingQuestRuntimeMetrics:
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
        completed_steps: int,
        total_steps: int,
    ) -> None:
        with self._lock:
            self._increment("growth_onboarding_quest_evaluations_total")
            if enabled:
                self._increment("growth_onboarding_quest_enabled_total")
            else:
                self._increment("growth_onboarding_quest_disabled_total")
            if has_partner_context:
                self._increment("growth_onboarding_quest_partner_context_total")
            if completed_steps >= total_steps and total_steps > 0:
                self._increment("growth_onboarding_quest_completed_total")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


growth_onboarding_quest_runtime_metrics = GrowthOnboardingQuestRuntimeMetrics()
