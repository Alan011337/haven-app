from __future__ import annotations

import logging

from app.api.deps import verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.schemas.growth import (
    FeatureFlagsPublic,
    FirstDelightAcknowledgeRequest,
    FirstDelightAcknowledgeResult,
    FirstDelightPublic,
    GamificationSummaryPublic,
    OnboardingQuestPublic,
    OnboardingQuestStepPublic,
    ReengagementHookPublic,
    ReengagementHooksPublic,
    SyncNudgeDeliverRequest,
    SyncNudgeDeliverResult,
    SyncNudgesPublic,
    SyncNudgePublic,
    SyncNudgeType,
)
from app.services.feature_flags import list_feature_flags_for_client
from app.services.gamification import get_or_compute_streak_summary
from app.services.growth_first_delight_runtime import (
    acknowledge_first_delight,
    evaluate_first_delight,
)
from app.services.growth_onboarding_quest_runtime import evaluate_onboarding_quest
from app.services.growth_reengagement_runtime import evaluate_reengagement_hooks
from app.services.growth_sync_nudge_runtime import deliver_sync_nudge, evaluate_sync_nudges

logger = logging.getLogger(__name__)


def handle_read_my_feature_flags(*, session, current_user) -> FeatureFlagsPublic:
    has_partner = verify_active_partner_id(session=session, current_user=current_user) is not None
    payload = list_feature_flags_for_client(has_partner=has_partner)
    return FeatureFlagsPublic(
        has_partner_context=bool(payload["has_partner_context"]),
        flags=dict(payload["flags"]),
        kill_switches=dict(payload["kill_switches"]),
    )


def handle_read_my_gamification_summary(*, session, current_user) -> GamificationSummaryPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    summary = get_or_compute_streak_summary(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    return GamificationSummaryPublic(
        has_partner_context=summary.has_partner_context,
        streak_days=summary.streak_days,
        best_streak_days=summary.best_streak_days,
        streak_eligible_today=summary.streak_eligible_today,
        level=summary.level,
        level_points_total=summary.level_points_total,
        level_points_current=summary.level_points_current,
        level_points_target=summary.level_points_target,
        love_bar_percent=summary.love_bar_percent,
        level_title=summary.level_title,
        anti_cheat_enabled=summary.anti_cheat_enabled,
    )


def handle_read_my_reengagement_hooks(*, session, current_user) -> ReengagementHooksPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    evaluation = evaluate_reengagement_hooks(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=partner_id,
    )
    return ReengagementHooksPublic(
        enabled=evaluation.enabled,
        has_partner_context=evaluation.has_partner_context,
        kill_switch_active=evaluation.kill_switch_active,
        hooks=[
            ReengagementHookPublic(
                hook_type=item.hook_type,
                eligible=item.eligible,
                reason=item.reason,
                dedupe_key=item.dedupe_key,
                hook_metadata=dict(item.metadata),
            )
            for item in evaluation.hooks
        ],
    )


def handle_read_my_onboarding_quest(*, session, current_user) -> OnboardingQuestPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    evaluation = evaluate_onboarding_quest(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=partner_id,
    )
    return OnboardingQuestPublic(
        enabled=evaluation.enabled,
        has_partner_context=evaluation.has_partner_context,
        kill_switch_active=evaluation.kill_switch_active,
        completed_steps=evaluation.completed_steps,
        total_steps=evaluation.total_steps,
        progress_percent=evaluation.progress_percent,
        steps=[
            OnboardingQuestStepPublic(
                key=item.key,
                title=item.title,
                description=item.description,
                quest_day=item.quest_day,
                completed=item.completed,
                reason=item.reason,
                dedupe_key=item.dedupe_key,
                step_metadata=dict(item.metadata),
            )
            for item in evaluation.steps
        ],
    )


def handle_read_my_sync_nudges(*, session, current_user) -> SyncNudgesPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    evaluation = evaluate_sync_nudges(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=partner_id,
    )
    return SyncNudgesPublic(
        enabled=evaluation.enabled,
        has_partner_context=evaluation.has_partner_context,
        kill_switch_active=evaluation.kill_switch_active,
        nudge_cooldown_hours=evaluation.nudge_cooldown_hours,
        nudges=[
            SyncNudgePublic(
                nudge_type=item.nudge_type,
                title=item.title,
                description=item.description,
                eligible=item.eligible,
                reason=item.reason,
                dedupe_key=item.dedupe_key,
                nudge_metadata=dict(item.metadata),
            )
            for item in evaluation.nudges
        ],
    )


def handle_read_my_first_delight(*, session, current_user) -> FirstDelightPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    evaluation = evaluate_first_delight(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=partner_id,
    )
    return FirstDelightPublic(
        enabled=evaluation.enabled,
        has_partner_context=evaluation.has_partner_context,
        kill_switch_active=evaluation.kill_switch_active,
        delivered=evaluation.delivered,
        eligible=evaluation.eligible,
        reason=evaluation.reason,
        dedupe_key=evaluation.dedupe_key,
        title=evaluation.title,
        description=evaluation.description,
        first_delight_metadata=dict(evaluation.metadata),
    )


def handle_acknowledge_my_first_delight(
    *,
    session,
    current_user,
    payload: FirstDelightAcknowledgeRequest,
) -> FirstDelightAcknowledgeResult:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    result = acknowledge_first_delight(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=partner_id,
        dedupe_key=payload.dedupe_key,
        source=payload.source,
    )
    if result.accepted and not result.deduped:
        commit_with_error_handling(
            session=session,
            logger=logger,
            action="first delight acknowledgment",
            conflict_detail="Could not record first delight event",
            failure_detail="Could not record first delight event",
        )
    return FirstDelightAcknowledgeResult(
        accepted=result.accepted,
        deduped=result.deduped,
        reason=result.reason,
        dedupe_key=result.dedupe_key,
    )


def handle_deliver_my_sync_nudge(
    *,
    session,
    current_user,
    nudge_type: SyncNudgeType,
    payload: SyncNudgeDeliverRequest,
) -> SyncNudgeDeliverResult:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    result = deliver_sync_nudge(
        session=session,
        current_user_id=current_user.id,
        partner_user_id=partner_id,
        nudge_type=nudge_type.value,
        dedupe_key=payload.dedupe_key,
        source=payload.source,
    )
    if result.accepted and not result.deduped:
        commit_with_error_handling(
            session=session,
            logger=logger,
            action="sync nudge delivery",
            conflict_detail="Could not record sync nudge delivery event",
            failure_detail="Could not record sync nudge delivery event",
        )

    return SyncNudgeDeliverResult(
        accepted=result.accepted,
        deduped=result.deduped,
        nudge_type=nudge_type.value,
        dedupe_key=result.dedupe_key,
        reason=result.reason,
    )
