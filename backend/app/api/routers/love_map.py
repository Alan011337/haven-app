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
from app.models.love_map_note import LoveMapNote
from app.models.relationship_knowledge_suggestion import RelationshipKnowledgeSuggestion
from app.models.relationship_baseline import RelationshipBaseline
from app.models.user import User
from app.models.wishlist_item import WishlistItem
from app.schemas.baseline import BaselineSummaryPublic, CoupleGoalPublic, RelationshipBaselinePublic
from app.schemas.blueprint import WishlistItemPublic
from app.schemas.love_map import (
    LoveMapCardSummary,
    LoveMapCarePreferencesPublic,
    LoveMapCardsResponse,
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
    RelationshipKnowledgeSuggestionEvidencePublic,
    RelationshipKnowledgeSuggestionPublic,
)
from app.services.ai import (
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
    resolve_pair_weekly_task,
)
from app.services.memory_archive import get_relationship_story_slice, get_relationship_story_time_capsule

logger = logging.getLogger(__name__)
router = APIRouter(tags=["love-map"])

SUGGESTION_SECTION_SHARED_FUTURE = "shared_future"
SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT = "shared_future_refinement"
SUGGESTION_STATUS_PENDING = "pending"
SUGGESTION_STATUS_ACCEPTED = "accepted"
SUGGESTION_STATUS_DISMISSED = "dismissed"
SUGGESTION_GENERATOR_SHARED_FUTURE_V1 = "shared_future_v1"
SUGGESTION_GENERATOR_SHARED_FUTURE_STORY_RITUAL_V1 = "shared_future_story_ritual_v1"
SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_NEXT_STEP_V1 = "shared_future_refinement_next_step_v1"
SUGGESTION_GENERATOR_SHARED_FUTURE_REFINEMENT_CADENCE_V1 = "shared_future_refinement_cadence_v1"
REFINEMENT_DISMISS_COOLDOWN = timedelta(hours=24)


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
    return RelationshipKnowledgeSuggestionPublic(
        id=str(row.id),
        section=row.section,
        status=row.status,
        generator_version=row.generator_version,
        proposed_title=row.proposed_title,
        proposed_notes=row.proposed_notes,
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
) -> tuple[list[dict[str, str]], list[str], set[str], list[str]]:
    evidence_catalog: list[dict[str, str]] = []

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
    story = LoveMapStoryPublic()
    my_care_preferences = load_love_language_preference_summary(
        session=session,
        user_id=current_user.id,
    )
    partner_care_preferences = None
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
    timestamps.extend(row.updated_at for row in note_rows)
    timestamps.extend(row.created_at for row in wishlist_rows)
    if my_care_preferences and my_care_preferences.updated_at:
        timestamps.append(my_care_preferences.updated_at)
    if partner_care_preferences and partner_care_preferences.updated_at:
        timestamps.append(partner_care_preferences.updated_at)
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
            weekly_task=_to_weekly_task_public(weekly_task),
        ),
    )


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
                if isinstance(item, dict)
            ],
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
    row = _get_owned_suggestion_or_404(
        session=session,
        current_user=current_user,
        suggestion_id=suggestion_id,
    )
    if row.status != SUGGESTION_STATUS_PENDING or row.section not in {
        SUGGESTION_SECTION_SHARED_FUTURE,
        SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="這個建議已經被處理")

    active_partner_id = verify_active_partner_id(session=session, current_user=current_user)
    if not active_partner_id or active_partner_id != row.partner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該建議")

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
    row = _get_owned_suggestion_or_404(
        session=session,
        current_user=current_user,
        suggestion_id=suggestion_id,
    )
    if row.status != SUGGESTION_STATUS_PENDING or row.section not in {
        SUGGESTION_SECTION_SHARED_FUTURE,
        SUGGESTION_SECTION_SHARED_FUTURE_REFINEMENT,
    }:
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
