# Module D1: Love Map — layered cards and notes.

import logging
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.core.datetime_utils import utcnow
from app.models.appreciation import Appreciation
from app.models.card import Card
from app.models.card_response import CardResponse, ResponseStatus
from app.models.card_session import CardSession, CardSessionStatus
from app.models.couple_goal import CoupleGoal
from app.models.journal import Journal
from app.models.love_language import LoveLanguagePreference
from app.models.love_map_note import LoveMapNote
from app.models.relationship_care_profile import RelationshipCareProfile
from app.models.relationship_compass import RelationshipCompass
from app.models.relationship_compass_change import RelationshipCompassChange
from app.models.relationship_knowledge_suggestion import RelationshipKnowledgeSuggestion
from app.models.relationship_repair_agreement import RelationshipRepairAgreement
from app.models.relationship_repair_agreement_change import RelationshipRepairAgreementChange
from app.models.relationship_repair_outcome_capture import RelationshipRepairOutcomeCapture
from app.models.relationship_baseline import RelationshipBaseline
from app.models.user import User
from app.models.wishlist_item import WishlistItem
from app.schemas.baseline import BaselineSummaryPublic, CoupleGoalPublic, RelationshipBaselinePublic
from app.schemas.blueprint import WishlistItemPublic
from app.schemas.love_map import (
    LoveMapCardSummary,
    LoveMapCareProfilePublic,
    LoveMapCarePreferencesPublic,
    LoveMapCardsResponse,
    LoveMapHeartProfileSavePublic,
    LoveMapHeartProfileUpsert,
    LoveMapRepairAgreementChangePublic,
    LoveMapRepairAgreementFieldChangePublic,
    LoveMapRepairAgreementsPublic,
    LoveMapRepairAgreementsUpsert,
    LoveMapRepairOutcomeCapturePublic,
    LoveMapRelationshipCompassChangePublic,
    LoveMapRelationshipCompassFieldChangePublic,
    LoveMapRelationshipCompassPublic,
    LoveMapRelationshipCompassUpsert,
    LoveMapNoteCreate,
    LoveMapNotePublic,
    LoveMapStoryCapsulePublic,
    LoveMapStoryMomentPublic,
    LoveMapStoryPublic,
    LoveMapSystemEssentialsPublic,
    LoveMapSystemMePublic,
    LoveMapSystemPartnerPublic,
    LoveMapSystemResponse,
    LoveMapSystemStatsPublic,
    LoveMapWeeklyTaskPublic,
    LoveMapNoteUpdate,
    RelationshipCompassSuggestionCandidatePublic,
    RelationshipKnowledgeSuggestionEvidencePublic,
    RelationshipKnowledgeSuggestionPublic,
)
from app.services.ai import (
    generate_relationship_compass_suggestion,
    generate_shared_future_story_adjacent_ritual,
    generate_shared_future_refinement_cadence,
    generate_shared_future_refinement_next_step,
    generate_shared_future_suggestions,
    is_shared_future_refinement_near_duplicate,
    is_shared_future_title_near_duplicate,
    normalize_shared_future_suggestion_key,
    shared_future_similarity_ratio,
    supports_shared_future_cadence_refinement,
)
from app.services.ai_errors import HavenAIProviderError, HavenAISchemaError, HavenAITimeoutError
from app.services.love_language_runtime import (
    LoveLanguagePreferenceSummary,
    WeeklyTaskResolution,
    load_love_language_preference_summary,
    normalize_love_language_preference,
    resolve_pair_weekly_task,
)
from app.services.memory_archive import get_relationship_story_slice, get_relationship_story_time_capsule
from app.services.repair_flow_runtime import (
    OUTCOME_CAPTURE_STATUS_APPLIED,
    OUTCOME_CAPTURE_STATUS_DISMISSED,
    OUTCOME_CAPTURE_STATUS_PENDING,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["love-map"])

SUGGESTION_SECTION_SHARED_FUTURE = "shared_future"
SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT = "shared_future_refinement"
SUGGESTION_SECTION_RELATIONSHIP_COMPASS = "relationship_compass"
SUGGESTION_STATUS_PENDING = "pending"
SUGGESTION_STATUS_ACCEPTED = "accepted"
SUGGESTION_STATUS_DISMISSED = "dismissed"
SUGGESTION_GENERATOR_SHARED_FUTURE_V1 = "shared_future_v1"
SUGGESTION_GENERATOR_SHARED_FUTURE_STORY_RITUAL_V1 = "shared_future_story_ritual_v1"
SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_NEXT_STEP_V1 = "shared_future_refinement_next_step_v1"
SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_CADENCE_V1 = "shared_future_refinement_cadence_v1"
SUGGESTION_GENERATOR_RELATIONSHIP_COMPASS_V1 = "relationship_compass_v1"
REFINEMENT_DISMISS_COOLDOWN = timedelta(hours=24)
REPAIR_AGREEMENT_ORIGIN_MANUAL_EDIT = "manual_edit"
REPAIR_AGREEMENT_ORIGIN_POST_MEDIATION = "post_mediation_carry_forward"
REPAIR_AGREEMENT_FIELD_LABELS = {
    "protect_what_matters": "當張力升高時，我們想保護什麼",
    "avoid_in_conflict": "卡住或升高時，我們先避免什麼",
    "repair_reentry": "要重新開啟修復時，我們怎麼回來",
}
COMPASS_FIELD_LABELS: dict[str, str] = {
    "identity_statement": "身份",
    "story_anchor": "故事",
    "future_direction": "未來",
}
COMPASS_HISTORY_LIMIT = 3


def _depth_to_layer(d: int) -> str:
    if d <= 1:
        return "safe"
    if d == 2:
        return "medium"
    return "deep"


def _to_note_public(row: LoveMapNote) -> LoveMapNotePublic:
    return LoveMapNotePublic(
        id=str(row.id),
        layer=row.layer,
        content=row.content,
        created_at=row.created_at.isoformat() + "Z",
        updated_at=row.updated_at.isoformat() + "Z",
    )


def _to_baseline_public(row: RelationshipBaseline) -> RelationshipBaselinePublic:
    return RelationshipBaselinePublic(
        user_id=str(row.user_id),
        partner_id=str(row.partner_id) if row.partner_id else None,
        filled_at=row.filled_at,
        scores=row.scores,
    )


def _to_wishlist_public(*, row: WishlistItem, current_user: CurrentUser) -> WishlistItemPublic:
    return WishlistItemPublic(
        id=str(row.id),
        title=row.title,
        notes=row.notes,
        created_at=row.created_at.isoformat() + "Z",
        added_by_me=row.user_id == current_user.id,
    )


def _resolve_partner_name(partner: User) -> str | None:
    return partner.full_name or partner.email.split("@")[0]


def _resolve_user_name(user: User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.email.split("@")[0]


def _to_iso_z(value: object) -> str:
    if hasattr(value, "isoformat"):
        return f"{value.isoformat()}Z"
    return str(value)


def _to_story_public(story_slice: dict[str, object] | None) -> LoveMapStoryPublic:
    if not story_slice:
        return LoveMapStoryPublic()

    moment_rows = story_slice.get("moments")
    capsule_row = story_slice.get("time_capsule")

    return LoveMapStoryPublic(
        available=bool(story_slice.get("available")),
        moments=[
            LoveMapStoryMomentPublic(
                kind=str(row["kind"]),
                title=str(row["title"]),
                description=str(row["description"]),
                occurred_at=_to_iso_z(row["occurred_at"]),
                badges=[str(badge) for badge in row.get("badges", [])],
                why_text=str(row["why_text"]),
                source_id=str(row["source_id"]) if row.get("source_id") else None,
            )
            for row in moment_rows
            if isinstance(row, dict)
        ]
        if isinstance(moment_rows, list)
        else [],
        time_capsule=(
            LoveMapStoryCapsulePublic(
                summary_text=str(capsule_row["summary_text"]),
                from_date=str(capsule_row["from_date"]),
                to_date=str(capsule_row["to_date"]),
                journals_count=int(capsule_row["journals_count"]),
                cards_count=int(capsule_row["cards_count"]),
                appreciations_count=int(capsule_row["appreciations_count"]),
            )
            if isinstance(capsule_row, dict)
            else None
        ),
    )


def _truncate_preview(value: str, limit: int) -> str:
    normalized = " ".join((value or "").strip().split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def _to_care_preferences_public(
    summary: LoveLanguagePreferenceSummary | None,
) -> LoveMapCarePreferencesPublic | None:
    if summary is None:
        return None
    return LoveMapCarePreferencesPublic(
        primary=summary.primary,
        secondary=summary.secondary,
        updated_at=summary.updated_at.isoformat() + "Z" if summary.updated_at else None,
    )


def _to_weekly_task_public(
    resolution: WeeklyTaskResolution | None,
) -> LoveMapWeeklyTaskPublic | None:
    if resolution is None:
        return None
    return LoveMapWeeklyTaskPublic(
        task_slug=resolution.task_slug,
        task_label=resolution.task_label,
        assigned_at=resolution.assigned_at.isoformat() + "Z" if resolution.assigned_at else None,
        completed=resolution.completed,
        completed_at=resolution.completed_at.isoformat() + "Z" if resolution.completed_at else None,
    )


def _to_care_profile_public(
    row: RelationshipCareProfile | None,
) -> LoveMapCareProfilePublic | None:
    if row is None:
        return None
    return LoveMapCareProfilePublic(
        support_me=row.support_me,
        avoid_when_stressed=row.avoid_when_stressed,
        small_delights=row.small_delights,
        updated_at=row.updated_at.isoformat() + "Z" if row.updated_at else None,
    )


def _to_repair_agreements_public(
    row: RelationshipRepairAgreement | None,
    *,
    updated_by_name: str | None = None,
) -> LoveMapRepairAgreementsPublic | None:
    if row is None:
        return None
    return LoveMapRepairAgreementsPublic(
        protect_what_matters=row.protect_what_matters,
        avoid_in_conflict=row.avoid_in_conflict,
        repair_reentry=row.repair_reentry,
        updated_by_name=updated_by_name,
        updated_at=row.updated_at.isoformat() + "Z" if row.updated_at else None,
    )


def _to_relationship_compass_public(
    row: RelationshipCompass | None,
    *,
    updated_by_name: str | None = None,
) -> LoveMapRelationshipCompassPublic | None:
    if row is None:
        return None
    return LoveMapRelationshipCompassPublic(
        identity_statement=row.identity_statement,
        story_anchor=row.story_anchor,
        future_direction=row.future_direction,
        updated_by_name=updated_by_name,
        updated_at=row.updated_at.isoformat() + "Z" if row.updated_at else None,
    )


def _to_repair_outcome_capture_public(
    row: RelationshipRepairOutcomeCapture | None,
    *,
    captured_by_name: str | None = None,
) -> LoveMapRepairOutcomeCapturePublic | None:
    if row is None:
        return None
    return LoveMapRepairOutcomeCapturePublic(
        id=str(row.id),
        repair_session_id=row.repair_session_id,
        shared_commitment=row.shared_commitment,
        improvement_note=row.improvement_note,
        status=row.status,
        captured_by_name=captured_by_name,
        created_at=row.created_at.isoformat() + "Z" if row.created_at else None,
        updated_at=row.updated_at.isoformat() + "Z" if row.updated_at else None,
    )


def _build_repair_agreement_field_changes(
    row: RelationshipRepairAgreementChange,
) -> list[LoveMapRepairAgreementFieldChangePublic]:
    changes: list[LoveMapRepairAgreementFieldChangePublic] = []
    for field_key, label in REPAIR_AGREEMENT_FIELD_LABELS.items():
        before_value = getattr(row, f"{field_key}_before")
        after_value = getattr(row, f"{field_key}_after")
        if before_value == after_value:
            continue
        if before_value is None and after_value is not None:
            change_kind = "added"
        elif before_value is not None and after_value is None:
            change_kind = "cleared"
        else:
            change_kind = "updated"
        changes.append(
            LoveMapRepairAgreementFieldChangePublic(
                key=field_key,
                label=label,
                change_kind=change_kind,
                before_text=before_value,
                after_text=after_value,
            )
        )
    return changes


def _to_repair_agreement_change_public(
    row: RelationshipRepairAgreementChange,
    *,
    changed_by_name: str | None = None,
    source_captured_by_name: str | None = None,
) -> LoveMapRepairAgreementChangePublic:
    return LoveMapRepairAgreementChangePublic(
        id=str(row.id),
        changed_at=row.changed_at.isoformat() + "Z" if row.changed_at else None,
        changed_by_name=changed_by_name,
        origin_kind=row.origin_kind,
        source_outcome_capture_id=str(row.source_outcome_capture_id) if row.source_outcome_capture_id else None,
        source_captured_by_name=source_captured_by_name,
        source_captured_at=row.source_captured_at.isoformat() + "Z" if row.source_captured_at else None,
        fields=_build_repair_agreement_field_changes(row),
        revision_note=row.revision_note,
    )


def _normalize_short_text(value: str | None) -> str | None:
    trimmed = (value or "").strip()
    if not trimmed:
        return None
    return trimmed[:500]


def _load_care_profile(
    *,
    session,
    user_id: UUID,
    partner_id: UUID,
) -> RelationshipCareProfile | None:
    return session.exec(
        select(RelationshipCareProfile).where(
            RelationshipCareProfile.user_id == user_id,
            RelationshipCareProfile.partner_id == partner_id,
        )
    ).first()


def _load_relationship_compass(
    *,
    session,
    user_id: UUID,
    partner_id: UUID,
) -> RelationshipCompass | None:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    return session.exec(
        select(RelationshipCompass).where(
            RelationshipCompass.user_id == uid1,
            RelationshipCompass.partner_id == uid2,
        )
    ).first()


def _load_repair_agreements(
    *,
    session,
    user_id: UUID,
    partner_id: UUID,
) -> RelationshipRepairAgreement | None:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    return session.exec(
        select(RelationshipRepairAgreement).where(
            RelationshipRepairAgreement.user_id == uid1,
            RelationshipRepairAgreement.partner_id == uid2,
        )
    ).first()


def _load_repair_outcome_capture(
    *,
    session,
    capture_id: UUID,
    user_id: UUID,
    partner_id: UUID,
    status: str | None = None,
) -> RelationshipRepairOutcomeCapture | None:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    statement = select(RelationshipRepairOutcomeCapture).where(
        RelationshipRepairOutcomeCapture.id == capture_id,
        RelationshipRepairOutcomeCapture.user_id == uid1,
        RelationshipRepairOutcomeCapture.partner_id == uid2,
    )
    if status:
        statement = statement.where(RelationshipRepairOutcomeCapture.status == status)
    return session.exec(statement).first()


def _load_pending_repair_outcome_capture(
    *,
    session,
    user_id: UUID,
    partner_id: UUID,
) -> RelationshipRepairOutcomeCapture | None:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    return session.exec(
        select(RelationshipRepairOutcomeCapture).where(
            RelationshipRepairOutcomeCapture.user_id == uid1,
            RelationshipRepairOutcomeCapture.partner_id == uid2,
            RelationshipRepairOutcomeCapture.status == OUTCOME_CAPTURE_STATUS_PENDING,
        ).order_by(RelationshipRepairOutcomeCapture.updated_at.desc())
    ).first()


def _load_repair_agreement_history(
    *,
    session,
    user_id: UUID,
    partner_id: UUID,
    limit: int = 5,
) -> list[RelationshipRepairAgreementChange]:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    return session.exec(
        select(RelationshipRepairAgreementChange).where(
            RelationshipRepairAgreementChange.user_id == uid1,
            RelationshipRepairAgreementChange.partner_id == uid2,
        ).order_by(RelationshipRepairAgreementChange.changed_at.desc()).limit(limit)
    ).all()


def _build_relationship_compass_field_changes(
    row: RelationshipCompassChange,
) -> list[LoveMapRelationshipCompassFieldChangePublic]:
    out: list[LoveMapRelationshipCompassFieldChangePublic] = []
    for key, label in COMPASS_FIELD_LABELS.items():
        before = getattr(row, f"{key}_before")
        after = getattr(row, f"{key}_after")
        if before == after:
            continue
        if before is None:
            change_kind = "added"
        elif after is None:
            change_kind = "cleared"
        else:
            change_kind = "updated"
        out.append(
            LoveMapRelationshipCompassFieldChangePublic(
                key=key,
                label=label,
                change_kind=change_kind,
                before_text=before,
                after_text=after,
            )
        )
    return out


def _to_relationship_compass_change_public(
    row: RelationshipCompassChange,
    *,
    changed_by_name: str | None,
) -> LoveMapRelationshipCompassChangePublic:
    return LoveMapRelationshipCompassChangePublic(
        id=str(row.id),
        changed_at=row.changed_at.isoformat() + "Z" if row.changed_at else None,
        changed_by_name=changed_by_name,
        origin_kind=getattr(row, "origin_kind", "manual_edit") or "manual_edit",
        fields=_build_relationship_compass_field_changes(row),
        revision_note=row.revision_note,
    )


def _load_relationship_compass_history(
    *,
    session,
    user_id: UUID,
    partner_id: UUID,
    limit: int = COMPASS_HISTORY_LIMIT,
) -> list[RelationshipCompassChange]:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    return session.exec(
        select(RelationshipCompassChange)
        .where(
            RelationshipCompassChange.user_id == uid1,
            RelationshipCompassChange.partner_id == uid2,
        )
        .order_by(RelationshipCompassChange.changed_at.desc())
        .limit(limit)
    ).all()


def _pair_scope_ids(user_id: UUID, partner_id: UUID) -> tuple[UUID, UUID]:
    return min(user_id, partner_id), max(user_id, partner_id)


def _pair_wishlist_rows(*, session, user_id: UUID, partner_id: UUID) -> list[WishlistItem]:
    uid1, uid2 = _pair_scope_ids(user_id, partner_id)
    return session.exec(
        select(WishlistItem).where(
            ((WishlistItem.user_id == uid1) & (WishlistItem.partner_id == uid2))
            | ((WishlistItem.user_id == uid2) & (WishlistItem.partner_id == uid1)),
        ).order_by(WishlistItem.created_at.desc())
    ).all()


def _pair_appreciation_rows(*, session, user_id: UUID, partner_id: UUID) -> list[Appreciation]:
    return session.exec(
        select(Appreciation).where(
            ((Appreciation.user_id == user_id) & (Appreciation.partner_id == partner_id))
            | ((Appreciation.user_id == partner_id) & (Appreciation.partner_id == user_id)),
        ).order_by(Appreciation.created_at.desc())
    ).all()


def _to_suggestion_public(row: RelationshipKnowledgeSuggestion) -> RelationshipKnowledgeSuggestionPublic:
    evidence_rows = row.evidence_json if isinstance(row.evidence_json, list) else []
    candidate = (
        _relationship_compass_candidate_public(row.candidate_json)
        if row.section == SUGGESTION_SECTION_RELATIONSHIP_COMPASS
        else None
    )
    return RelationshipKnowledgeSuggestionPublic(
        id=str(row.id),
        section=row.section,
        status=row.status,
        generator_version=row.generator_version,
        proposed_title=row.proposed_title,
        proposed_notes=row.proposed_notes,
        relationship_compass_candidate=candidate,
        evidence=[
            RelationshipKnowledgeSuggestionEvidencePublic(
                source_kind=str(item.get("source_kind", "")),
                source_id=str(item.get("source_id", "")),
                label=str(item.get("label", "")),
                excerpt=str(item.get("excerpt", "")),
            )
            for item in evidence_rows
            if isinstance(item, dict)
        ],
        created_at=row.created_at.isoformat() + "Z",
        reviewed_at=row.reviewed_at.isoformat() + "Z" if row.reviewed_at else None,
        target_wishlist_item_id=str(row.target_wishlist_item_id) if row.target_wishlist_item_id else None,
        accepted_wishlist_item_id=str(row.accepted_wishlist_item_id) if row.accepted_wishlist_item_id else None,
    )


def _relationship_compass_candidate_public(
    raw: object,
) -> RelationshipCompassSuggestionCandidatePublic | None:
    if not isinstance(raw, dict):
        return None
    candidate = {
        key: _normalize_short_text(str(raw.get(key) or ""))
        for key in COMPASS_FIELD_LABELS
    }
    if not any(candidate.values()):
        return None
    return RelationshipCompassSuggestionCandidatePublic(**candidate)


def _get_owned_suggestion_or_404(
    *,
    session,
    current_user: CurrentUser,
    suggestion_id: UUID,
) -> RelationshipKnowledgeSuggestion:
    row = session.get(RelationshipKnowledgeSuggestion, suggestion_id)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")
    return row


def _load_shared_future_pending_suggestions(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
) -> list[RelationshipKnowledgeSuggestion]:
    return session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_PENDING,
        ).order_by(RelationshipKnowledgeSuggestion.created_at.desc())
    ).all()


def _load_shared_future_pending_refinements(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
) -> list[RelationshipKnowledgeSuggestion]:
    return session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_PENDING,
        ).order_by(RelationshipKnowledgeSuggestion.created_at.desc())
    ).all()


def _load_relationship_compass_pending_suggestions(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
) -> list[RelationshipKnowledgeSuggestion]:
    return session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_RELATIONSHIP_COMPASS,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_PENDING,
        ).order_by(RelationshipKnowledgeSuggestion.created_at.desc())
    ).all()


def _load_couple_wishlist_item_or_404(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
    wishlist_item_id: UUID,
) -> WishlistItem:
    row = session.get(WishlistItem, wishlist_item_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到這個 Shared Future 片段")

    uid1, uid2 = _pair_scope_ids(current_user.id, partner_id)
    row_uid1, row_uid2 = _pair_scope_ids(row.user_id, row.partner_id)
    if (row_uid1, row_uid2) != (uid1, uid2):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到這個 Shared Future 片段")
    return row


def _normalize_shared_future_refinement_key(
    *,
    wishlist_item_id: UUID,
    proposed_notes: str,
    refinement_kind: str,
) -> str:
    normalized_notes = " ".join((proposed_notes or "").strip().lower().split())
    return f"wishlist:{wishlist_item_id}:{refinement_kind}:{normalized_notes}"


def _extract_shared_future_prefixed_lines(notes: str, *, prefix: str) -> list[str]:
    lines: list[str] = []
    for raw_line in (notes or "").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith(prefix):
            continue
        content = stripped.removeprefix(prefix).strip()
        if content:
            lines.append(content)
    return lines


def _extract_shared_future_next_step_lines(notes: str) -> list[str]:
    return _extract_shared_future_prefixed_lines(notes, prefix="下一步：")


def _extract_shared_future_cadence_lines(notes: str) -> list[str]:
    return _extract_shared_future_prefixed_lines(notes, prefix="節奏：")


def _shared_future_refinement_line_prefix(generator_version: str) -> str:
    if generator_version == SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_CADENCE_V1:
        return "節奏："
    return "下一步："


def _log_shared_future_near_duplicate_filtered(
    *,
    flow: str,
    candidate_text: str,
    matched_text: str,
    matched_source: str,
) -> None:
    logger.info(
        "shared_future_near_duplicate_filtered: flow=%s matched_source=%s similarity_ratio=%.3f candidate_text=%s matched_text=%s",
        flow,
        matched_source,
        shared_future_similarity_ratio(candidate_text, matched_text),
        candidate_text,
        matched_text,
    )


def _find_shared_future_title_near_duplicate_match(
    *,
    candidate_text: str,
    comparison_rows: list[tuple[str, str]],
) -> tuple[str, str] | None:
    for existing_text, matched_source in comparison_rows:
        if not existing_text.strip():
            continue
        if is_shared_future_title_near_duplicate(candidate_text, existing_text):
            return existing_text, matched_source
    return None


def _find_shared_future_refinement_near_duplicate_match(
    *,
    candidate_text: str,
    comparison_rows: list[tuple[str, str]],
) -> tuple[str, str] | None:
    for existing_text, matched_source in comparison_rows:
        if not existing_text.strip():
            continue
        if is_shared_future_refinement_near_duplicate(candidate_text, existing_text):
            return existing_text, matched_source
    return None


def _build_shared_future_generation_sources(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
    include_personal_journals: bool = False,
) -> tuple[list[dict[str, str]], list[str], set[str], list[str]]:
    evidence_catalog: list[dict[str, str]] = []

    if include_personal_journals:
        journal_rows = session.exec(
            select(Journal).where(
                Journal.user_id == current_user.id,
                Journal.deleted_at.is_(None),
                Journal.is_draft.is_(False),
            ).order_by(Journal.created_at.desc())
        ).all()
        for row in journal_rows[:6]:
            evidence_catalog.append(
                {
                    "evidence_id": f"journal:{row.id}",
                    "source_kind": "journal",
                    "source_id": str(row.id),
                    "label": f"你的日記 · {row.created_at.date().isoformat()}",
                    "excerpt": _truncate_preview(row.content, 280),
                }
            )

    session_rows = session.exec(
        select(CardSession).where(
            CardSession.deleted_at.is_(None),
            CardSession.status == CardSessionStatus.COMPLETED,
            (((CardSession.creator_id == current_user.id) & (CardSession.partner_id == partner_id))
             | ((CardSession.creator_id == partner_id) & (CardSession.partner_id == current_user.id))),
        ).order_by(CardSession.created_at.desc())
    ).all()
    for session_row in session_rows[:6]:
        response_rows = session.exec(
            select(CardResponse).where(
                CardResponse.session_id == session_row.id,
                CardResponse.deleted_at.is_(None),
                CardResponse.status == ResponseStatus.REVEALED,
            )
        ).all()
        if len(response_rows) < 2:
            continue
        my_response = next((row for row in response_rows if row.user_id == current_user.id), None)
        partner_response = next((row for row in response_rows if row.user_id == partner_id), None)
        if not my_response or not partner_response:
            continue
        card = session.get(Card, session_row.card_id)
        card_title = card.title if card else "共同卡片對話"
        card_question = card.question if card else ""
        evidence_catalog.append(
            {
                "evidence_id": f"card:{session_row.id}",
                "source_kind": "card",
                "source_id": str(session_row.id),
                "label": f"共同卡片 · {card_title}",
                "excerpt": _truncate_preview(
                    f"問題：{card_question} 我：{my_response.content} 對方：{partner_response.content}",
                    280,
                ),
            }
        )

    appreciation_rows = _pair_appreciation_rows(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
    )
    for row in appreciation_rows[:6]:
        evidence_catalog.append(
            {
                "evidence_id": f"appreciation:{row.id}",
                "source_kind": "appreciation",
                "source_id": str(row.id),
                "label": f"感恩 · {row.created_at.date().isoformat()}",
                "excerpt": _truncate_preview(row.body_text, 280),
            }
        )

    existing_wishlist_titles = [
        row.title
        for row in _pair_wishlist_rows(session=session, user_id=current_user.id, partner_id=partner_id)
        if row.title.strip()
    ]
    suggestion_rows = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE,
        )
    ).all()
    blocked_dedupe_keys = {
        row.dedupe_key
        for row in suggestion_rows
        if row.dedupe_key.strip()
    }
    handled_titles = [
        row.proposed_title
        for row in suggestion_rows
        if row.proposed_title.strip()
    ]
    return evidence_catalog, existing_wishlist_titles, blocked_dedupe_keys, handled_titles


def _relationship_compass_candidate_dict(raw: object) -> dict[str, str | None]:
    if not isinstance(raw, dict):
        return {key: None for key in COMPASS_FIELD_LABELS}
    return {
        key: _normalize_short_text(str(raw.get(key) or ""))
        for key in COMPASS_FIELD_LABELS
    }


def _relationship_compass_candidate_text(candidate: dict[str, str | None]) -> str:
    return " ".join(
        value.strip()
        for key in COMPASS_FIELD_LABELS
        if (value := candidate.get(key)) and value.strip()
    )


def _build_relationship_compass_suggestion_sources(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
) -> tuple[list[dict[str, str]], dict[str, str | None], set[str]]:
    evidence_catalog, _, _, _ = _build_shared_future_generation_sources(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        include_personal_journals=True,
    )
    compass = _load_relationship_compass(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
    )
    current_compass = {
        key: getattr(compass, key) if compass else None
        for key in COMPASS_FIELD_LABELS
    }
    handled_rows = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_RELATIONSHIP_COMPASS,
        )
    ).all()
    blocked_dedupe_keys = {
        row.dedupe_key
        for row in handled_rows
        if row.dedupe_key.strip()
    }
    current_dedupe = normalize_shared_future_suggestion_key(
        _relationship_compass_candidate_text(current_compass)
    )
    if current_dedupe:
        blocked_dedupe_keys.add(current_dedupe)
    return evidence_catalog[:12], current_compass, blocked_dedupe_keys


def _story_time_capsule_item_label(source_kind: str) -> str:
    if source_kind == "journal":
        return "Time Capsule · 日記"
    if source_kind == "card":
        return "Time Capsule · 共同卡片"
    if source_kind == "appreciation":
        return "Time Capsule · 感恩"
    return "Time Capsule · 記憶片段"


def _build_story_ritual_evidence_catalog(
    *,
    time_capsule: dict[str, object],
) -> list[dict[str, str]]:
    from_date = str(time_capsule.get("from_date") or "").strip()
    to_date = str(time_capsule.get("to_date") or "").strip()
    summary_text = _truncate_preview(str(time_capsule.get("summary_text") or ""), 280)
    evidence_catalog: list[dict[str, str]] = []

    if from_date and to_date and summary_text:
        evidence_catalog.append(
            {
                "evidence_id": f"time-capsule:{from_date}:{to_date}",
                "source_kind": "story_time_capsule",
                "source_id": f"{from_date}:{to_date}",
                "label": "Story Time Capsule",
                "excerpt": summary_text,
            }
        )

    items = time_capsule.get("items")
    if not isinstance(items, list):
        return evidence_catalog

    for item in items[:2]:
        if not isinstance(item, dict):
            continue
        source_kind = str(item.get("type") or "").strip().lower()
        source_id = str(item.get("source_id") or "").strip()
        preview_text = _truncate_preview(str(item.get("preview_text") or ""), 280)
        if not source_kind or not source_id or not preview_text:
            continue
        evidence_catalog.append(
            {
                "evidence_id": f"time-capsule-item:{source_kind}:{source_id}",
                "source_kind": "time_capsule_item",
                "source_id": source_id,
                "label": _story_time_capsule_item_label(source_kind),
                "excerpt": preview_text,
            }
        )

    return evidence_catalog


@router.get("/cards", response_model=LoveMapCardsResponse)
def get_love_map_cards(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> LoveMapCardsResponse:
    """Return cards grouped by layer (safe=depth 1, medium=2, deep=3). No partner required."""
    rows = session.exec(select(Card).where(Card.depth_level.is_(None) | (Card.depth_level >= 1))).all()
    safe, medium, deep = [], [], []
    for c in rows:
        layer = _depth_to_layer(c.depth_level if c.depth_level is not None else 1)
        summary = LoveMapCardSummary(
            id=str(c.id),
            title=c.title,
            description=c.description,
            question=c.question,
            depth_level=c.depth_level or 1,
            layer=layer,
        )
        if layer == "safe":
            safe.append(summary)
        elif layer == "medium":
            medium.append(summary)
        else:
            deep.append(summary)
    return LoveMapCardsResponse(safe=safe, medium=medium, deep=deep)


@router.get("/notes", response_model=list[LoveMapNotePublic])
def list_love_map_notes(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[LoveMapNotePublic]:
    """List current user's love map notes (for their partner pair)."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return []
    uid1, uid2 = min(current_user.id, partner_id), max(current_user.id, partner_id)
    rows = session.exec(
        select(LoveMapNote).where(
            ((LoveMapNote.user_id == uid1) & (LoveMapNote.partner_id == uid2))
            | ((LoveMapNote.user_id == uid2) & (LoveMapNote.partner_id == uid1)),
            LoveMapNote.user_id == current_user.id,
        )
    ).all()
    return [_to_note_public(r) for r in rows]


@router.get("/system", response_model=LoveMapSystemResponse)
def get_love_map_system(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> LoveMapSystemResponse:
    """Return the current relationship-system snapshot for the Love Map surface."""
    verified_partner_id = verify_active_partner_id(session=session, current_user=current_user)

    mine_baseline = session.exec(
        select(RelationshipBaseline).where(RelationshipBaseline.user_id == current_user.id)
    ).first()
    partner_baseline = None
    partner = None

    if verified_partner_id:
        partner = session.get(User, verified_partner_id)
        partner_baseline = session.exec(
            select(RelationshipBaseline).where(RelationshipBaseline.user_id == verified_partner_id)
        ).first()

    couple_goal = None
    notes: list[LoveMapNotePublic] = []
    wishlist_items: list[WishlistItemPublic] = []
    note_rows: list[LoveMapNote] = []
    wishlist_rows: list[WishlistItem] = []
    relationship_compass_row = None
    relationship_compass = None
    relationship_compass_history_rows: list[RelationshipCompassChange] = []
    relationship_compass_history: list[LoveMapRelationshipCompassChangePublic] = []
    story = LoveMapStoryPublic()
    my_care_preferences = load_love_language_preference_summary(
        session=session,
        user_id=current_user.id,
    )
    partner_care_preferences = None
    my_care_profile = None
    partner_care_profile = None
    repair_agreements_row = None
    repair_agreements = None
    repair_agreement_history_rows: list[RelationshipRepairAgreementChange] = []
    repair_agreement_history: list[LoveMapRepairAgreementChangePublic] = []
    pending_repair_outcome_capture_row = None
    pending_repair_outcome_capture = None
    weekly_task = None

    if verified_partner_id:
        uid1, uid2 = _pair_scope_ids(current_user.id, verified_partner_id)
        goal_row = session.exec(
            select(CoupleGoal).where(
                CoupleGoal.user_id == uid1,
                CoupleGoal.partner_id == uid2,
            )
        ).first()
        if goal_row:
            couple_goal = CoupleGoalPublic(goal_slug=goal_row.goal_slug, chosen_at=goal_row.chosen_at)

        relationship_compass_row = _load_relationship_compass(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        compass_updated_by_user = (
            session.get(User, relationship_compass_row.updated_by_user_id)
            if relationship_compass_row and relationship_compass_row.updated_by_user_id
            else None
        )
        relationship_compass = _to_relationship_compass_public(
            relationship_compass_row,
            updated_by_name=_resolve_user_name(compass_updated_by_user),
        )

        relationship_compass_history_rows = _load_relationship_compass_history(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        compass_history_user_ids = {
            row.changed_by_user_id
            for row in relationship_compass_history_rows
            if row.changed_by_user_id is not None
        }
        compass_history_users = {
            user_id: session.get(User, user_id)
            for user_id in compass_history_user_ids
        }
        relationship_compass_history = [
            _to_relationship_compass_change_public(
                row,
                changed_by_name=_resolve_user_name(
                    compass_history_users.get(row.changed_by_user_id)
                ),
            )
            for row in relationship_compass_history_rows
        ]

        note_rows = session.exec(
            select(LoveMapNote).where(
                LoveMapNote.user_id == current_user.id,
                LoveMapNote.partner_id == verified_partner_id,
            )
        ).all()
        notes = [_to_note_public(row) for row in note_rows]

        wishlist_rows = _pair_wishlist_rows(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        wishlist_items = [_to_wishlist_public(row=row, current_user=current_user) for row in wishlist_rows]
        story = _to_story_public(
            get_relationship_story_slice(
                session=session,
                user_id=current_user.id,
                partner_id=verified_partner_id,
            )
        )
        partner_care_preferences = load_love_language_preference_summary(
            session=session,
            user_id=verified_partner_id,
        )
        my_care_profile = _load_care_profile(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        partner_care_profile = _load_care_profile(
            session=session,
            user_id=verified_partner_id,
            partner_id=current_user.id,
        )
        repair_agreements_row = _load_repair_agreements(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        updated_by_user = (
            session.get(User, repair_agreements_row.updated_by_user_id)
            if repair_agreements_row and repair_agreements_row.updated_by_user_id
            else None
        )
        repair_agreements = _to_repair_agreements_public(
            repair_agreements_row,
            updated_by_name=_resolve_user_name(updated_by_user),
        )
        repair_agreement_history_rows = _load_repair_agreement_history(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        history_user_ids = {
            row.changed_by_user_id
            for row in repair_agreement_history_rows
            if row.changed_by_user_id is not None
        }
        history_user_ids.update(
            row.source_captured_by_user_id
            for row in repair_agreement_history_rows
            if row.source_captured_by_user_id is not None
        )
        history_users = {
            user_id: session.get(User, user_id)
            for user_id in history_user_ids
        }
        repair_agreement_history = [
            _to_repair_agreement_change_public(
                row,
                changed_by_name=_resolve_user_name(history_users.get(row.changed_by_user_id)),
                source_captured_by_name=_resolve_user_name(history_users.get(row.source_captured_by_user_id)),
            )
            for row in repair_agreement_history_rows
        ]
        pending_repair_outcome_capture_row = _load_pending_repair_outcome_capture(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
        )
        capture_author = (
            session.get(User, pending_repair_outcome_capture_row.created_by_user_id)
            if pending_repair_outcome_capture_row
            else None
        )
        pending_repair_outcome_capture = _to_repair_outcome_capture_public(
            pending_repair_outcome_capture_row,
            captured_by_name=_resolve_user_name(capture_author),
        )
        weekly_task = resolve_pair_weekly_task(
            session=session,
            user_id=current_user.id,
            partner_id=verified_partner_id,
            ensure_assignment=False,
        )

    timestamps = []
    if mine_baseline:
        timestamps.append(mine_baseline.filled_at)
    if partner_baseline:
        timestamps.append(partner_baseline.filled_at)
    if couple_goal:
        timestamps.append(couple_goal.chosen_at)
    if relationship_compass_row and relationship_compass_row.updated_at:
        timestamps.append(relationship_compass_row.updated_at)
    timestamps.extend(row.updated_at for row in note_rows)
    timestamps.extend(row.created_at for row in wishlist_rows)
    if my_care_preferences and my_care_preferences.updated_at:
        timestamps.append(my_care_preferences.updated_at)
    if partner_care_preferences and partner_care_preferences.updated_at:
        timestamps.append(partner_care_preferences.updated_at)
    if my_care_profile and my_care_profile.updated_at:
        timestamps.append(my_care_profile.updated_at)
    if partner_care_profile and partner_care_profile.updated_at:
        timestamps.append(partner_care_profile.updated_at)
    if repair_agreements_row and repair_agreements_row.updated_at:
        timestamps.append(repair_agreements_row.updated_at)
    timestamps.extend(row.changed_at for row in repair_agreement_history_rows if row.changed_at)
    if pending_repair_outcome_capture_row and pending_repair_outcome_capture_row.updated_at:
        timestamps.append(pending_repair_outcome_capture_row.updated_at)
    if weekly_task and weekly_task.completed_at:
        timestamps.append(weekly_task.completed_at)

    last_activity_at = max(timestamps).isoformat() + "Z" if timestamps else None

    return LoveMapSystemResponse(
        has_partner=verified_partner_id is not None,
        me=LoveMapSystemMePublic(
            id=str(current_user.id),
            full_name=current_user.full_name,
            email=current_user.email,
        ),
        partner=(
            LoveMapSystemPartnerPublic(
                id=str(partner.id),
                partner_name=_resolve_partner_name(partner),
            )
            if partner
            else None
        ),
        baseline=BaselineSummaryPublic(
            mine=_to_baseline_public(mine_baseline) if mine_baseline else None,
            partner=_to_baseline_public(partner_baseline) if partner_baseline else None,
        ),
        couple_goal=couple_goal,
        relationship_compass=relationship_compass,
        relationship_compass_history=relationship_compass_history,
        story=story,
        notes=notes,
        wishlist_items=wishlist_items,
        stats=LoveMapSystemStatsPublic(
            filled_note_layers=sum(1 for note in notes if note.content.strip()),
            baseline_ready_mine=mine_baseline is not None,
            baseline_ready_partner=partner_baseline is not None,
            wishlist_count=len(wishlist_items),
            last_activity_at=last_activity_at,
        ),
        essentials=LoveMapSystemEssentialsPublic(
            my_care_preferences=_to_care_preferences_public(my_care_preferences),
            partner_care_preferences=_to_care_preferences_public(partner_care_preferences),
            my_care_profile=_to_care_profile_public(my_care_profile),
            partner_care_profile=_to_care_profile_public(partner_care_profile),
            repair_agreements=repair_agreements,
            repair_agreement_history=repair_agreement_history,
            pending_repair_outcome_capture=pending_repair_outcome_capture,
            weekly_task=_to_weekly_task_public(weekly_task),
        ),
    )


@router.put("/identity/compass", response_model=LoveMapRelationshipCompassPublic)
def upsert_relationship_compass(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: LoveMapRelationshipCompassUpsert,
) -> LoveMapRelationshipCompassPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    compass = _save_relationship_compass_values(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        values={
            key: getattr(body, key)
            for key in COMPASS_FIELD_LABELS
        },
        revision_note=body.revision_note,
        origin_kind="manual_edit",
        source_suggestion_id=None,
        action="Upsert love map relationship compass",
        conflict_detail="儲存 Relationship Compass 時發生衝突。",
        failure_detail="儲存 Relationship Compass 失敗。",
    )

    return _to_relationship_compass_public(
        compass,
        updated_by_name=_resolve_user_name(current_user),
    ) or LoveMapRelationshipCompassPublic()


def _save_relationship_compass_values(
    *,
    session,
    current_user: CurrentUser,
    partner_id: UUID,
    values: dict[str, str | None],
    revision_note: str | None,
    origin_kind: str = "manual_edit",
    source_suggestion_id: UUID | None = None,
    action: str,
    conflict_detail: str,
    failure_detail: str,
) -> RelationshipCompass | None:
    uid1, uid2 = _pair_scope_ids(current_user.id, partner_id)
    compass = _load_relationship_compass(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
    )
    current_values = {
        key: getattr(compass, key) if compass else None
        for key in COMPASS_FIELD_LABELS
    }
    next_values = {
        key: _normalize_short_text(values.get(key))
        for key in COMPASS_FIELD_LABELS
    }
    has_changes = any(
        current_values[key] != next_values[key] for key in COMPASS_FIELD_LABELS
    )
    # Whitespace-only note → None so empty chips never leak into the timeline.
    # Over-length rejected earlier by Pydantic `max_length=300`.
    normalized_revision_note = (revision_note or "").strip() or None
    saved_at = utcnow()

    if has_changes:
        if compass is None:
            compass = RelationshipCompass(user_id=uid1, partner_id=uid2)
        for key in COMPASS_FIELD_LABELS:
            setattr(compass, key, next_values[key])
        compass.updated_by_user_id = current_user.id
        compass.updated_at = saved_at
        session.add(compass)
        session.flush()

        session.add(
            RelationshipCompassChange(
                user_id=uid1,
                partner_id=uid2,
                changed_by_user_id=current_user.id,
                changed_at=saved_at,
                identity_statement_before=current_values["identity_statement"],
                identity_statement_after=next_values["identity_statement"],
                story_anchor_before=current_values["story_anchor"],
                story_anchor_after=next_values["story_anchor"],
                future_direction_before=current_values["future_direction"],
                future_direction_after=next_values["future_direction"],
                origin_kind=origin_kind,
                source_suggestion_id=source_suggestion_id,
                revision_note=normalized_revision_note,
            )
        )

        commit_with_error_handling(
            session,
            logger=logger,
            action=action,
            conflict_detail=conflict_detail,
            failure_detail=failure_detail,
        )
        session.refresh(compass)

    return compass


@router.put("/essentials/heart-profile", response_model=LoveMapHeartProfileSavePublic)
def upsert_heart_care_profile(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: LoveMapHeartProfileUpsert,
) -> LoveMapHeartProfileSavePublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    normalized_preference = normalize_love_language_preference(
        {
            "primary": body.primary,
            "secondary": body.secondary,
        }
    )
    care_profile = _load_care_profile(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
    )
    if care_profile is None:
        care_profile = RelationshipCareProfile(
            user_id=current_user.id,
            partner_id=partner_id,
        )

    care_profile.support_me = _normalize_short_text(body.support_me)
    care_profile.avoid_when_stressed = _normalize_short_text(body.avoid_when_stressed)
    care_profile.small_delights = _normalize_short_text(body.small_delights)
    care_profile.updated_at = utcnow()
    session.add(care_profile)

    preference_row = session.get(LoveLanguagePreference, current_user.id)
    if preference_row is None:
        preference_row = LoveLanguagePreference(
            user_id=current_user.id,
            preference=normalized_preference,
        )
    else:
        preference_row.preference = normalized_preference
        preference_row.updated_at = utcnow()
    session.add(preference_row)

    commit_with_error_handling(
        session,
        logger=logger,
        action="Upsert love map heart care profile",
        conflict_detail="儲存 Heart care playbook 時發生衝突。",
        failure_detail="儲存 Heart care playbook 失敗。",
    )
    session.refresh(care_profile)
    session.refresh(preference_row)
    return LoveMapHeartProfileSavePublic(
        care_preferences=LoveMapCarePreferencesPublic(
            primary=normalized_preference["primary"],
            secondary=normalized_preference["secondary"],
            updated_at=preference_row.updated_at.isoformat() + "Z",
        ),
        care_profile=LoveMapCareProfilePublic(
            support_me=care_profile.support_me,
            avoid_when_stressed=care_profile.avoid_when_stressed,
            small_delights=care_profile.small_delights,
            updated_at=care_profile.updated_at.isoformat() + "Z",
        ),
    )


@router.put("/essentials/repair-agreements", response_model=LoveMapRepairAgreementsPublic)
def upsert_repair_agreements(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: LoveMapRepairAgreementsUpsert,
) -> LoveMapRepairAgreementsPublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    uid1, uid2 = _pair_scope_ids(current_user.id, partner_id)
    source_capture = None
    if body.source_outcome_capture_id:
        try:
            source_capture_id = UUID(body.source_outcome_capture_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source_outcome_capture_id") from exc
        source_capture = _load_repair_outcome_capture(
            session=session,
            capture_id=source_capture_id,
            user_id=current_user.id,
            partner_id=partner_id,
            status=OUTCOME_CAPTURE_STATUS_PENDING,
        )
        if source_capture is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到待審核的修復結果")
    repair_agreements = _load_repair_agreements(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
    )
    current_values = {
        "protect_what_matters": repair_agreements.protect_what_matters if repair_agreements else None,
        "avoid_in_conflict": repair_agreements.avoid_in_conflict if repair_agreements else None,
        "repair_reentry": repair_agreements.repair_reentry if repair_agreements else None,
    }
    next_values = {
        "protect_what_matters": _normalize_short_text(body.protect_what_matters),
        "avoid_in_conflict": _normalize_short_text(body.avoid_in_conflict),
        "repair_reentry": _normalize_short_text(body.repair_reentry),
    }
    has_changes = any(current_values[key] != next_values[key] for key in REPAIR_AGREEMENT_FIELD_LABELS)
    # Optional short human-authored revision note. Whitespace-only input is
    # normalized to None so an empty chip never renders in the timeline.
    # Over-length input is rejected earlier by Pydantic's `max_length=300`.
    normalized_revision_note = (body.revision_note or "").strip() or None
    saved_at = utcnow()
    if repair_agreements is None and has_changes:
        repair_agreements = RelationshipRepairAgreement(
            user_id=uid1,
            partner_id=uid2,
        )

    if repair_agreements is not None and has_changes:
        repair_agreements.protect_what_matters = next_values["protect_what_matters"]
        repair_agreements.avoid_in_conflict = next_values["avoid_in_conflict"]
        repair_agreements.repair_reentry = next_values["repair_reentry"]
        repair_agreements.updated_by_user_id = current_user.id
        repair_agreements.updated_at = saved_at
        session.add(repair_agreements)
        session.flush()

        source_captured_at = None
        if source_capture is not None:
            source_captured_at = source_capture.updated_at or source_capture.created_at

        session.add(
            RelationshipRepairAgreementChange(
                user_id=uid1,
                partner_id=uid2,
                repair_agreement_id=repair_agreements.id,
                changed_by_user_id=current_user.id,
                origin_kind=(
                    REPAIR_AGREEMENT_ORIGIN_POST_MEDIATION
                    if source_capture is not None
                    else REPAIR_AGREEMENT_ORIGIN_MANUAL_EDIT
                ),
                source_outcome_capture_id=source_capture.id if source_capture is not None else None,
                source_captured_by_user_id=(
                    source_capture.created_by_user_id if source_capture is not None else None
                ),
                source_captured_at=source_captured_at,
                changed_at=saved_at,
                protect_what_matters_before=current_values["protect_what_matters"],
                protect_what_matters_after=next_values["protect_what_matters"],
                avoid_in_conflict_before=current_values["avoid_in_conflict"],
                avoid_in_conflict_after=next_values["avoid_in_conflict"],
                repair_reentry_before=current_values["repair_reentry"],
                repair_reentry_after=next_values["repair_reentry"],
                revision_note=normalized_revision_note,
            )
        )

    if source_capture is not None:
        source_capture.status = OUTCOME_CAPTURE_STATUS_APPLIED
        source_capture.reviewed_by_user_id = current_user.id
        source_capture.reviewed_at = saved_at
        source_capture.updated_at = saved_at
        session.add(source_capture)

    commit_with_error_handling(
        session,
        logger=logger,
        action="Upsert love map repair agreements",
        conflict_detail="儲存 Repair Agreements 時發生衝突。",
        failure_detail="儲存 Repair Agreements 失敗。",
    )
    if repair_agreements is not None:
        session.refresh(repair_agreements)
        updated_by_user = (
            session.get(User, repair_agreements.updated_by_user_id)
            if repair_agreements.updated_by_user_id
            else None
        )
        return _to_repair_agreements_public(
            repair_agreements,
            updated_by_name=_resolve_user_name(updated_by_user),
        )
    return LoveMapRepairAgreementsPublic()


@router.post(
    "/essentials/repair-outcome-captures/{capture_id}/dismiss",
    response_model=LoveMapRepairOutcomeCapturePublic,
)
def dismiss_repair_outcome_capture(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    capture_id: UUID,
) -> LoveMapRepairOutcomeCapturePublic:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    capture = _load_repair_outcome_capture(
        session=session,
        capture_id=capture_id,
        user_id=current_user.id,
        partner_id=partner_id,
        status=OUTCOME_CAPTURE_STATUS_PENDING,
    )
    if capture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到待審核的修復結果")

    dismissed_at = utcnow()
    capture.status = OUTCOME_CAPTURE_STATUS_DISMISSED
    capture.reviewed_by_user_id = current_user.id
    capture.reviewed_at = dismissed_at
    capture.updated_at = dismissed_at
    session.add(capture)

    commit_with_error_handling(
        session,
        logger=logger,
        action="Dismiss love map repair outcome capture",
        conflict_detail="略過修復結果時發生衝突。",
        failure_detail="略過修復結果失敗。",
    )
    session.refresh(capture)
    return _to_repair_outcome_capture_public(
        capture,
        captured_by_name=_resolve_user_name(session.get(User, capture.created_by_user_id)),
    ) or LoveMapRepairOutcomeCapturePublic(
        id=str(capture.id),
        repair_session_id=capture.repair_session_id,
        status=capture.status,
    )


@router.get(
    "/suggestions/relationship-compass",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
def list_relationship_compass_suggestions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return []
    rows = _load_relationship_compass_pending_suggestions(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    return [_to_suggestion_public(row) for row in rows]


@router.post(
    "/suggestions/relationship-compass/generate",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
async def generate_relationship_compass_review_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    pending_rows = _load_relationship_compass_pending_suggestions(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    if pending_rows:
        return [_to_suggestion_public(row) for row in pending_rows]

    evidence_catalog, current_compass, blocked_dedupe_keys = _build_relationship_compass_suggestion_sources(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    try:
        generated = await generate_relationship_compass_suggestion(
            evidence_catalog=evidence_catalog,
            current_compass=current_compass,
        )
    except (HavenAIProviderError, HavenAISchemaError, HavenAITimeoutError) as exc:
        logger.warning(
            "relationship_compass_suggestion_generate_failed: reason=%s",
            getattr(exc, "reason", type(exc).__name__),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 建議暫時無法使用，請稍後再試。",
        ) from exc

    if not generated:
        logger.info("relationship_compass_suggestion_skipped: reason=%s", "ai_returned_empty")
        return []

    candidate = _relationship_compass_candidate_dict(generated.get("candidate"))
    candidate_text = _relationship_compass_candidate_text(candidate)
    dedupe_key = normalize_shared_future_suggestion_key(
        str(generated.get("dedupe_key") or candidate_text)
    )
    if not candidate_text or not dedupe_key or dedupe_key in blocked_dedupe_keys:
        logger.info("relationship_compass_suggestion_skipped: reason=%s", "dedupe_key_blocked")
        return []

    evidence_rows = [
        item
        for item in generated.get("evidence", [])
        if isinstance(item, dict)
    ]
    if not evidence_rows:
        logger.info("relationship_compass_suggestion_skipped: reason=%s", "missing_evidence")
        return []

    row = RelationshipKnowledgeSuggestion(
        user_id=current_user.id,
        partner_id=partner_id,
        section=SUGGESTION_SECTION_RELATIONSHIP_COMPASS,
        status=SUGGESTION_STATUS_PENDING,
        generator_version=SUGGESTION_GENERATOR_RELATIONSHIP_COMPASS_V1,
        proposed_title="Relationship Compass 建議更新",
        proposed_notes="Haven 根據最近留下的片段整理出一版可審核的 Compass 更新。",
        candidate_json=candidate,
        evidence_json=evidence_rows[:3],
        dedupe_key=dedupe_key,
    )
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Generate relationship compass suggestion",
        conflict_detail="儲存 Compass 建議時發生衝突，請稍後再試。",
        failure_detail="儲存 Compass 建議失敗，請稍後再試。",
    )
    session.refresh(row)
    return [_to_suggestion_public(row)]


@router.post(
    "/suggestions/relationship-compass/{suggestion_id}/accept",
    response_model=LoveMapRelationshipCompassPublic,
)
def accept_relationship_compass_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    suggestion_id: UUID,
) -> LoveMapRelationshipCompassPublic:
    row = session.exec(
        select(RelationshipKnowledgeSuggestion)
        .where(
            RelationshipKnowledgeSuggestion.id == suggestion_id,
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
        )
        .with_for_update()
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")
    if row.section != SUGGESTION_SECTION_RELATIONSHIP_COMPASS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    active_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not active_partner_id or active_partner_id != row.partner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")

    if row.status == SUGGESTION_STATUS_ACCEPTED:
        compass = _load_relationship_compass(
            session=session,
            user_id=current_user.id,
            partner_id=active_partner_id,
        )
        updated_by_user = (
            session.get(User, compass.updated_by_user_id) if compass and compass.updated_by_user_id else None
        )
        return _to_relationship_compass_public(
            compass,
            updated_by_name=_resolve_user_name(updated_by_user),
        ) or LoveMapRelationshipCompassPublic()

    if row.status != SUGGESTION_STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    candidate = _relationship_compass_candidate_dict(row.candidate_json)
    if not any(candidate.values()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議沒有可寫入的 Compass 欄位")

    compass = _save_relationship_compass_values(
        session=session,
        current_user=current_user,
        partner_id=active_partner_id,
        values=candidate,
        revision_note=None,
        origin_kind="accepted_suggestion",
        source_suggestion_id=suggestion_id,
        action="Accept relationship compass suggestion",
        conflict_detail="接受 Compass 建議時發生衝突，請稍後再試。",
        failure_detail="接受 Compass 建議失敗，請稍後再試。",
    )
    row.status = SUGGESTION_STATUS_ACCEPTED
    row.reviewed_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Mark relationship compass suggestion accepted",
        conflict_detail="更新 Compass 建議狀態時發生衝突，請稍後再試。",
        failure_detail="更新 Compass 建議狀態失敗，請稍後再試。",
    )
    session.refresh(row)

    return _to_relationship_compass_public(
        compass,
        updated_by_name=_resolve_user_name(current_user),
    ) or LoveMapRelationshipCompassPublic()


@router.post(
    "/suggestions/relationship-compass/{suggestion_id}/dismiss",
    response_model=RelationshipKnowledgeSuggestionPublic,
)
def dismiss_relationship_compass_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    suggestion_id: UUID,
) -> RelationshipKnowledgeSuggestionPublic:
    row = session.exec(
        select(RelationshipKnowledgeSuggestion)
        .where(
            RelationshipKnowledgeSuggestion.id == suggestion_id,
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
        )
        .with_for_update()
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")
    if row.section != SUGGESTION_SECTION_RELATIONSHIP_COMPASS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    active_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not active_partner_id or active_partner_id != row.partner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")

    if row.status == SUGGESTION_STATUS_DISMISSED:
        return _to_suggestion_public(row)
    if row.status == SUGGESTION_STATUS_ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")
    if row.status != SUGGESTION_STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    row.status = SUGGESTION_STATUS_DISMISSED
    row.reviewed_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Dismiss relationship compass suggestion",
        conflict_detail="略過 Compass 建議時發生衝突，請稍後再試。",
        failure_detail="略過 Compass 建議失敗，請稍後再試。",
    )
    session.refresh(row)
    return _to_suggestion_public(row)


@router.get(
    "/suggestions/shared-future",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
def list_shared_future_suggestions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return []
    rows = _load_shared_future_pending_suggestions(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    return [_to_suggestion_public(row) for row in rows]


@router.post(
    "/suggestions/shared-future/generate",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
async def generate_shared_future_review_suggestions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    pending_rows = _load_shared_future_pending_suggestions(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    if pending_rows:
        return [_to_suggestion_public(row) for row in pending_rows]

    evidence_catalog, existing_titles, blocked_dedupe_keys, handled_titles = _build_shared_future_generation_sources(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        include_personal_journals=False,
    )
    try:
        generated_rows = await generate_shared_future_suggestions(
            evidence_catalog=evidence_catalog,
            existing_titles=existing_titles,
        )
    except (HavenAIProviderError, HavenAISchemaError, HavenAITimeoutError) as exc:
        logger.warning(
            "shared_future_suggestions_generate_failed: reason=%s",
            getattr(exc, "reason", type(exc).__name__),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 建議暫時無法使用，請稍後再試。",
        ) from exc

    created_rows: list[RelationshipKnowledgeSuggestion] = []
    comparison_rows: list[tuple[str, str]] = [
        *((title, "wishlist_title") for title in existing_titles if title.strip()),
        *((title, "handled_suggestion") for title in handled_titles if title.strip()),
    ]
    allowed_evidence_kinds = {"card", "appreciation"}
    for generated in generated_rows:
        title = _truncate_preview(str(generated.get("proposed_title") or ""), 500)
        dedupe_key = normalize_shared_future_suggestion_key(
            str(generated.get("dedupe_key") or title or "")
        )
        if not title or not dedupe_key or dedupe_key in blocked_dedupe_keys:
            continue
        near_duplicate_match = _find_shared_future_title_near_duplicate_match(
            candidate_text=title,
            comparison_rows=comparison_rows,
        )
        if near_duplicate_match:
            matched_text, matched_source = near_duplicate_match
            _log_shared_future_near_duplicate_filtered(
                flow=SUGGESTION_SECTION_SHARED_FUTURE,
                candidate_text=title,
                matched_text=matched_text,
                matched_source=matched_source,
            )
            continue
        row = RelationshipKnowledgeSuggestion(
            user_id=current_user.id,
            partner_id=partner_id,
            section=SUGGESTION_SECTION_SHARED_FUTURE,
            status=SUGGESTION_STATUS_PENDING,
            generator_version=SUGGESTION_GENERATOR_SHARED_FUTURE_V1,
            proposed_title=title,
            proposed_notes=_truncate_preview(str(generated.get("proposed_notes") or ""), 2000),
            evidence_json=[
                item
                for item in generated.get("evidence", [])
                if (
                    isinstance(item, dict)
                    and str(item.get("source_kind") or "").strip().lower() in allowed_evidence_kinds
                )
            ][:3],
            dedupe_key=dedupe_key,
        )
        session.add(row)
        created_rows.append(row)
        blocked_dedupe_keys.add(dedupe_key)
        comparison_rows.append((title, "generated_sibling"))
        if len(created_rows) >= 2:
            break

    commit_with_error_handling(
        session,
        logger=logger,
        action="Generate shared future suggestions",
        conflict_detail="儲存建議時發生衝突，請稍後再試。",
        failure_detail="儲存建議失敗，請稍後再試。",
    )
    for row in created_rows:
        session.refresh(row)
    return [_to_suggestion_public(row) for row in created_rows]


@router.post(
    "/suggestions/shared-future/generate-story-ritual",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
async def generate_story_adjacent_ritual_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    pending_rows = _load_shared_future_pending_suggestions(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    pending_story_rows = [
        row
        for row in pending_rows
        if row.generator_version == SUGGESTION_GENERATOR_SHARED_FUTURE_STORY_RITUAL_V1
    ]
    if pending_story_rows:
        return [_to_suggestion_public(row) for row in pending_story_rows]
    if pending_rows:
        logger.info("shared_future_story_ritual_skipped: reason=%s", "shared_future_pending_queue_not_empty")
        return []

    time_capsule = get_relationship_story_time_capsule(
        session=session,
        user_id=current_user.id,
        partner_id=partner_id,
    )
    if not time_capsule:
        logger.info("shared_future_story_ritual_skipped: reason=%s", "story_time_capsule_unavailable")
        return []

    total_content_count = sum(
        int(time_capsule.get(key) or 0)
        for key in ("journals_count", "cards_count", "appreciations_count")
    )
    if total_content_count < 2:
        logger.info("shared_future_story_ritual_skipped: reason=%s", "insufficient_story_signal")
        return []

    evidence_catalog = _build_story_ritual_evidence_catalog(time_capsule=time_capsule)
    if len(evidence_catalog) < 2:
        logger.info("shared_future_story_ritual_skipped: reason=%s", "insufficient_time_capsule_evidence")
        return []

    _, existing_titles, blocked_dedupe_keys, handled_titles = _build_shared_future_generation_sources(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        include_personal_journals=False,
    )

    try:
        generated = await generate_shared_future_story_adjacent_ritual(
            evidence_catalog=evidence_catalog,
            existing_titles=existing_titles,
            handled_titles=handled_titles,
        )
    except (HavenAIProviderError, HavenAISchemaError, HavenAITimeoutError) as exc:
        logger.warning(
            "shared_future_story_ritual_generate_failed: reason=%s",
            getattr(exc, "reason", type(exc).__name__),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 建議暫時無法使用，請稍後再試。",
        ) from exc

    if not generated:
        logger.info("shared_future_story_ritual_skipped: reason=%s", "ai_returned_empty")
        return []

    title = _truncate_preview(str(generated.get("proposed_title") or ""), 500)
    dedupe_key = normalize_shared_future_suggestion_key(
        str(generated.get("dedupe_key") or title or "")
    )
    if not title or not dedupe_key or dedupe_key in blocked_dedupe_keys:
        logger.info("shared_future_story_ritual_skipped: reason=%s", "dedupe_key_blocked")
        return []

    comparison_rows: list[tuple[str, str]] = [
        *((existing_title, "wishlist_title") for existing_title in existing_titles if existing_title.strip()),
        *((handled_title, "handled_suggestion") for handled_title in handled_titles if handled_title.strip()),
    ]
    near_duplicate_match = _find_shared_future_title_near_duplicate_match(
        candidate_text=title,
        comparison_rows=comparison_rows,
    )
    if near_duplicate_match:
        matched_text, matched_source = near_duplicate_match
        _log_shared_future_near_duplicate_filtered(
            flow=SUGGESTION_SECTION_SHARED_FUTURE,
            candidate_text=title,
            matched_text=matched_text,
            matched_source=matched_source,
        )
        return []

    row = RelationshipKnowledgeSuggestion(
        user_id=current_user.id,
        partner_id=partner_id,
        section=SUGGESTION_SECTION_SHARED_FUTURE,
        status=SUGGESTION_STATUS_PENDING,
        generator_version=SUGGESTION_GENERATOR_SHARED_FUTURE_STORY_RITUAL_V1,
        proposed_title=title,
        proposed_notes=_truncate_preview(str(generated.get("proposed_notes") or ""), 2000),
        evidence_json=evidence_catalog,
        dedupe_key=dedupe_key,
    )
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Generate story-adjacent ritual suggestion",
        conflict_detail="儲存 Story ritual 建議時發生衝突，請稍後再試。",
        failure_detail="儲存 Story ritual 建議失敗，請稍後再試。",
    )
    session.refresh(row)
    return [_to_suggestion_public(row)]


@router.get(
    "/suggestions/shared-future/refinements",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
def list_shared_future_refinement_suggestions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        return []
    rows = _load_shared_future_pending_refinements(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    return [_to_suggestion_public(row) for row in rows]


@router.post(
    "/suggestions/shared-future/refinements/{wishlist_item_id}/generate",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
async def generate_shared_future_refinement_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    wishlist_item_id: UUID,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    wishlist_row = _load_couple_wishlist_item_or_404(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        wishlist_item_id=wishlist_item_id,
    )

    pending_rows = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_PENDING,
            RelationshipKnowledgeSuggestion.target_wishlist_item_id == wishlist_item_id,
        ).order_by(RelationshipKnowledgeSuggestion.created_at.desc())
    ).all()
    if pending_rows:
        return [_to_suggestion_public(row) for row in pending_rows]

    latest_dismissed_row = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_DISMISSED,
            RelationshipKnowledgeSuggestion.target_wishlist_item_id == wishlist_item_id,
            RelationshipKnowledgeSuggestion.generator_version
            == SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_NEXT_STEP_V1,
        ).order_by(RelationshipKnowledgeSuggestion.reviewed_at.desc())
    ).first()
    if (
        latest_dismissed_row
        and latest_dismissed_row.reviewed_at
        and latest_dismissed_row.reviewed_at >= utcnow() - REFINEMENT_DISMISS_COOLDOWN
    ):
        return []

    refinement_rows = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.target_wishlist_item_id == wishlist_item_id,
        )
    ).all()
    blocked_dedupe_keys = {
        row.dedupe_key
        for row in refinement_rows
        if row.dedupe_key.strip()
    }
    comparison_rows: list[tuple[str, str]] = [
        *((line, "wishlist_next_step") for line in _extract_shared_future_next_step_lines(wishlist_row.notes)),
        *(
            (row.proposed_notes, "handled_refinement")
            for row in refinement_rows
            if row.proposed_notes.strip()
            and row.generator_version == SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_NEXT_STEP_V1
        ),
    ]

    try:
        generated = await generate_shared_future_refinement_next_step(
            title=wishlist_row.title,
            notes=wishlist_row.notes,
            created_at=wishlist_row.created_at.isoformat() + "Z",
        )
    except (HavenAIProviderError, HavenAISchemaError, HavenAITimeoutError) as exc:
        logger.warning(
            "shared_future_refinement_generate_failed: reason=%s",
            getattr(exc, "reason", type(exc).__name__),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 建議暫時無法使用，請稍後再試。",
        ) from exc

    if not generated:
        return []

    proposed_notes = _truncate_preview(str(generated.get("proposed_notes") or ""), 240)
    dedupe_key = _normalize_shared_future_refinement_key(
        wishlist_item_id=wishlist_row.id,
        proposed_notes=proposed_notes,
        refinement_kind="next-step",
    )
    if not proposed_notes or dedupe_key in blocked_dedupe_keys:
        return []
    near_duplicate_match = _find_shared_future_refinement_near_duplicate_match(
        candidate_text=proposed_notes,
        comparison_rows=comparison_rows,
    )
    if near_duplicate_match:
        matched_text, matched_source = near_duplicate_match
        _log_shared_future_near_duplicate_filtered(
            flow=SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            candidate_text=proposed_notes,
            matched_text=matched_text,
            matched_source=matched_source,
        )
        return []

    excerpt_parts = [wishlist_row.title.strip()]
    if wishlist_row.notes.strip():
        excerpt_parts.append(wishlist_row.notes.strip())
    row = RelationshipKnowledgeSuggestion(
        user_id=current_user.id,
        partner_id=partner_id,
        section=SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
        status=SUGGESTION_STATUS_PENDING,
        generator_version=SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_NEXT_STEP_V1,
        proposed_title="",
        proposed_notes=proposed_notes,
        evidence_json=[
            {
                "source_kind": "shared_future_item",
                "source_id": str(wishlist_row.id),
                "label": "目前的 Shared Future",
                "excerpt": _truncate_preview("｜".join(excerpt_parts), 280),
            }
        ],
        dedupe_key=dedupe_key,
        target_wishlist_item_id=wishlist_row.id,
    )
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Generate shared future refinement suggestion",
        conflict_detail="儲存 refinement 建議時發生衝突，請稍後再試。",
        failure_detail="儲存 refinement 建議失敗，請稍後再試。",
    )
    session.refresh(row)
    return [_to_suggestion_public(row)]


@router.post(
    "/suggestions/shared-future/refinements/{wishlist_item_id}/generate-cadence",
    response_model=list[RelationshipKnowledgeSuggestionPublic],
)
async def generate_shared_future_cadence_refinement_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    wishlist_item_id: UUID,
) -> list[RelationshipKnowledgeSuggestionPublic]:
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")

    wishlist_row = _load_couple_wishlist_item_or_404(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
        wishlist_item_id=wishlist_item_id,
    )
    if not supports_shared_future_cadence_refinement(wishlist_row.title, wishlist_row.notes):
        return []

    pending_rows = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_PENDING,
            RelationshipKnowledgeSuggestion.target_wishlist_item_id == wishlist_item_id,
        ).order_by(RelationshipKnowledgeSuggestion.created_at.desc())
    ).all()
    if pending_rows:
        return [_to_suggestion_public(row) for row in pending_rows]

    latest_dismissed_row = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.status == SUGGESTION_STATUS_DISMISSED,
            RelationshipKnowledgeSuggestion.target_wishlist_item_id == wishlist_item_id,
            RelationshipKnowledgeSuggestion.generator_version
            == SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_CADENCE_V1,
        ).order_by(RelationshipKnowledgeSuggestion.reviewed_at.desc())
    ).first()
    if (
        latest_dismissed_row
        and latest_dismissed_row.reviewed_at
        and latest_dismissed_row.reviewed_at >= utcnow() - REFINEMENT_DISMISS_COOLDOWN
    ):
        return []

    refinement_rows = session.exec(
        select(RelationshipKnowledgeSuggestion).where(
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
            RelationshipKnowledgeSuggestion.partner_id == partner_id,
            RelationshipKnowledgeSuggestion.section == SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            RelationshipKnowledgeSuggestion.target_wishlist_item_id == wishlist_item_id,
        )
    ).all()
    blocked_dedupe_keys = {
        row.dedupe_key
        for row in refinement_rows
        if row.dedupe_key.strip()
    }
    comparison_rows: list[tuple[str, str]] = [
        *((line, "wishlist_cadence") for line in _extract_shared_future_cadence_lines(wishlist_row.notes)),
        *((line, "wishlist_next_step") for line in _extract_shared_future_next_step_lines(wishlist_row.notes)),
        *(
            (row.proposed_notes, "handled_cadence")
            for row in refinement_rows
            if row.proposed_notes.strip()
            and row.generator_version == SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_CADENCE_V1
        ),
    ]

    try:
        generated = await generate_shared_future_refinement_cadence(
            title=wishlist_row.title,
            notes=wishlist_row.notes,
            created_at=wishlist_row.created_at.isoformat() + "Z",
        )
    except (HavenAIProviderError, HavenAISchemaError, HavenAITimeoutError) as exc:
        logger.warning(
            "shared_future_refinement_cadence_generate_failed: reason=%s",
            getattr(exc, "reason", type(exc).__name__),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 建議暫時無法使用，請稍後再試。",
        ) from exc

    if not generated:
        return []

    proposed_notes = _truncate_preview(str(generated.get("proposed_notes") or ""), 240)
    dedupe_key = _normalize_shared_future_refinement_key(
        wishlist_item_id=wishlist_row.id,
        proposed_notes=proposed_notes,
        refinement_kind="cadence",
    )
    if not proposed_notes or dedupe_key in blocked_dedupe_keys:
        return []
    near_duplicate_match = _find_shared_future_refinement_near_duplicate_match(
        candidate_text=proposed_notes,
        comparison_rows=comparison_rows,
    )
    if near_duplicate_match:
        matched_text, matched_source = near_duplicate_match
        _log_shared_future_near_duplicate_filtered(
            flow=SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
            candidate_text=proposed_notes,
            matched_text=matched_text,
            matched_source=matched_source,
        )
        return []

    excerpt_parts = [wishlist_row.title.strip()]
    if wishlist_row.notes.strip():
        excerpt_parts.append(wishlist_row.notes.strip())
    row = RelationshipKnowledgeSuggestion(
        user_id=current_user.id,
        partner_id=partner_id,
        section=SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
        status=SUGGESTION_STATUS_PENDING,
        generator_version=SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_CADENCE_V1,
        proposed_title="",
        proposed_notes=proposed_notes,
        evidence_json=[
            {
                "source_kind": "shared_future_item",
                "source_id": str(wishlist_row.id),
                "label": "目前的 Shared Future",
                "excerpt": _truncate_preview("｜".join(excerpt_parts), 280),
            }
        ],
        dedupe_key=dedupe_key,
        target_wishlist_item_id=wishlist_row.id,
    )
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Generate shared future cadence refinement suggestion",
        conflict_detail="儲存 cadence 建議時發生衝突，請稍後再試。",
        failure_detail="儲存 cadence 建議失敗，請稍後再試。",
    )
    session.refresh(row)
    return [_to_suggestion_public(row)]


@router.post(
    "/suggestions/{suggestion_id}/accept",
    response_model=WishlistItemPublic,
)
def accept_relationship_knowledge_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    suggestion_id: UUID,
) -> WishlistItemPublic:
    row = session.exec(
        select(RelationshipKnowledgeSuggestion)
        .where(
            RelationshipKnowledgeSuggestion.id == suggestion_id,
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
        )
        .with_for_update()
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")
    if row.section not in {SUGGESTION_SECTION_SHARED_FUTURE, SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    active_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not active_partner_id or active_partner_id != row.partner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")

    if row.status == SUGGESTION_STATUS_ACCEPTED and row.accepted_wishlist_item_id:
        wishlist_row = _load_couple_wishlist_item_or_404(
            session=session,
            current_user=current_user,
            partner_id=active_partner_id,
            wishlist_item_id=row.accepted_wishlist_item_id,
        )
        return _to_wishlist_public(row=wishlist_row, current_user=current_user)

    if row.status != SUGGESTION_STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    if row.section == SUGGESTION_SECTION_SHARED_FUTURE:
        wishlist_row = WishlistItem(
            user_id=current_user.id,
            partner_id=row.partner_id,
            title=row.proposed_title,
            notes=row.proposed_notes,
        )
        session.add(wishlist_row)
        commit_with_error_handling(
            session,
            logger=logger,
            action="Accept shared future suggestion",
            conflict_detail="接受建議時發生衝突，請稍後再試。",
            failure_detail="接受建議失敗，請稍後再試。",
        )
        session.refresh(wishlist_row)
    else:
        if not row.target_wishlist_item_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")
        wishlist_row = _load_couple_wishlist_item_or_404(
            session=session,
            current_user=current_user,
            partner_id=active_partner_id,
            wishlist_item_id=row.target_wishlist_item_id,
        )
        note_line = f"{_shared_future_refinement_line_prefix(row.generator_version)}{row.proposed_notes.strip()}"
        existing_notes = wishlist_row.notes.strip()
        if note_line not in existing_notes:
            wishlist_row.notes = note_line if not existing_notes else f"{existing_notes}\n\n{note_line}"
            session.add(wishlist_row)
            commit_with_error_handling(
                session,
                logger=logger,
                action="Accept shared future refinement suggestion",
                conflict_detail="接受 refinement 建議時發生衝突，請稍後再試。",
                failure_detail="接受 refinement 建議失敗，請稍後再試。",
            )
            session.refresh(wishlist_row)

    row.status = SUGGESTION_STATUS_ACCEPTED
    row.accepted_wishlist_item_id = wishlist_row.id
    row.reviewed_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Mark shared future suggestion accepted",
        conflict_detail="更新建議狀態時發生衝突，請稍後再試。",
        failure_detail="更新建議狀態失敗，請稍後再試。",
    )
    session.refresh(row)
    return _to_wishlist_public(row=wishlist_row, current_user=current_user)


@router.post(
    "/suggestions/{suggestion_id}/dismiss",
    response_model=RelationshipKnowledgeSuggestionPublic,
)
def dismiss_relationship_knowledge_suggestion(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    suggestion_id: UUID,
) -> RelationshipKnowledgeSuggestionPublic:
    row = session.exec(
        select(RelationshipKnowledgeSuggestion)
        .where(
            RelationshipKnowledgeSuggestion.id == suggestion_id,
            RelationshipKnowledgeSuggestion.user_id == current_user.id,
        )
        .with_for_update()
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")
    if row.section not in {SUGGESTION_SECTION_SHARED_FUTURE, SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    if row.status == SUGGESTION_STATUS_DISMISSED:
        return _to_suggestion_public(row)
    if row.status == SUGGESTION_STATUS_ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")
    if row.status != SUGGESTION_STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    row.status = SUGGESTION_STATUS_DISMISSED
    row.reviewed_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Dismiss shared future suggestion",
        conflict_detail="略過建議時發生衝突，請稍後再試。",
        failure_detail="略過建議失敗，請稍後再試。",
    )
    session.refresh(row)
    return _to_suggestion_public(row)


@router.post("/notes", response_model=LoveMapNotePublic)
def create_or_update_love_map_note(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: LoveMapNoteCreate,
) -> LoveMapNotePublic:
    """Upsert a note for the given layer (one note per user per layer per pair)."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not partner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要先綁定伴侶")
    existing = session.exec(
        select(LoveMapNote).where(
            LoveMapNote.user_id == current_user.id,
            LoveMapNote.partner_id == partner_id,
            LoveMapNote.layer == body.layer,
        )
    ).first()
    now = utcnow()
    if existing:
        existing.content = (body.content or "")[:5000]
        existing.updated_at = now
        session.add(existing)
        commit_with_error_handling(
            session, logger=logger, action="Update love map note",
            conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
        )
        session.refresh(existing)
        r = existing
    else:
        row = LoveMapNote(
            user_id=current_user.id,
            partner_id=partner_id,
            layer=body.layer,
            content=(body.content or "")[:5000],
        )
        session.add(row)
        commit_with_error_handling(
            session, logger=logger, action="Create love map note",
            conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
        )
        session.refresh(row)
        r = row
    return _to_note_public(r)


@router.put("/notes/{note_id}", response_model=LoveMapNotePublic)
def update_love_map_note(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    note_id: UUID,
    body: LoveMapNoteUpdate,
) -> LoveMapNotePublic:
    """Update a note by id. BOLA: only owner can update."""
    row = session.get(LoveMapNote, note_id)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該筆記")
    row.content = (body.content or "")[:5000]
    row.updated_at = utcnow()
    session.add(row)
    commit_with_error_handling(
        session, logger=logger, action="Update love map note by id",
        conflict_detail="儲存時發生衝突。", failure_detail="儲存失敗。",
    )
    session.refresh(row)
    return _to_note_public(row)
