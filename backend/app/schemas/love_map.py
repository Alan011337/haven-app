# Module D1: Love Map API schemas.

from pydantic import BaseModel, Field
from typing import Literal

from app.schemas.baseline import BaselineSummaryPublic, CoupleGoalPublic
from app.schemas.blueprint import WishlistItemPublic


LAYER_VALUES = ("safe", "medium", "deep")


class LoveMapCardSummary(BaseModel):
    id: str
    title: str
    description: str
    question: str
    depth_level: int
    layer: str  # safe | medium | deep


class LoveMapCardsResponse(BaseModel):
    safe: list[LoveMapCardSummary]
    medium: list[LoveMapCardSummary]
    deep: list[LoveMapCardSummary]


class LoveMapNotePublic(BaseModel):
    id: str
    layer: str
    content: str
    created_at: str
    updated_at: str


class LoveMapNoteCreate(BaseModel):
    layer: str = Field(..., pattern="^(safe|medium|deep)$")
    content: str = Field(max_length=5000, default="")


class LoveMapNoteUpdate(BaseModel):
    content: str = Field(max_length=5000)


class LoveMapSystemMePublic(BaseModel):
    id: str
    full_name: str | None = None
    email: str


class LoveMapSystemPartnerPublic(BaseModel):
    id: str
    partner_name: str | None = None


class LoveMapStoryMomentPublic(BaseModel):
    kind: str
    title: str
    description: str
    occurred_at: str
    badges: list[str] = Field(default_factory=list)
    why_text: str
    source_id: str | None = None


class LoveMapStoryCapsulePublic(BaseModel):
    summary_text: str
    from_date: str
    to_date: str
    journals_count: int
    cards_count: int
    appreciations_count: int


class LoveMapStoryPublic(BaseModel):
    available: bool = False
    moments: list[LoveMapStoryMomentPublic] = Field(default_factory=list)
    time_capsule: LoveMapStoryCapsulePublic | None = None


class LoveMapRelationshipCompassPublic(BaseModel):
    identity_statement: str | None = None
    story_anchor: str | None = None
    future_direction: str | None = None
    updated_by_name: str | None = None
    updated_at: str | None = None


class LoveMapRelationshipCompassUpsert(BaseModel):
    identity_statement: str = Field(default="", max_length=500)
    story_anchor: str = Field(default="", max_length=500)
    future_direction: str = Field(default="", max_length=500)
    # Optional human-authored revision note persisted on the change-history row.
    # Max 300 mirrors the Heart revision-note cap (and outcome-capture
    # `improvement_note` cap) for consistency across the Relationship System.
    revision_note: str | None = Field(default=None, max_length=300)


class LoveMapRelationshipCompassFieldChangePublic(BaseModel):
    key: str
    label: str
    change_kind: Literal["added", "updated", "cleared"]
    before_text: str | None = None
    after_text: str | None = None


class LoveMapRelationshipCompassChangePublic(BaseModel):
    id: str
    changed_at: str | None = None
    changed_by_name: str | None = None
    fields: list[LoveMapRelationshipCompassFieldChangePublic] = Field(default_factory=list)
    # Optional short human-authored note left at save-time; null when absent.
    revision_note: str | None = None


class RelationshipKnowledgeSuggestionEvidencePublic(BaseModel):
    source_kind: str
    source_id: str
    label: str
    excerpt: str


class RelationshipKnowledgeSuggestionPublic(BaseModel):
    id: str
    section: str
    status: str
    generator_version: str
    proposed_title: str
    proposed_notes: str
    evidence: list[RelationshipKnowledgeSuggestionEvidencePublic] = Field(default_factory=list)
    created_at: str
    reviewed_at: str | None = None
    target_wishlist_item_id: str | None = None
    accepted_wishlist_item_id: str | None = None


class LoveMapSystemStatsPublic(BaseModel):
    filled_note_layers: int
    baseline_ready_mine: bool
    baseline_ready_partner: bool
    wishlist_count: int
    last_activity_at: str | None = None


class LoveMapCarePreferencesPublic(BaseModel):
    primary: str | None = None
    secondary: str | None = None
    updated_at: str | None = None


class LoveMapCareProfilePublic(BaseModel):
    support_me: str | None = None
    avoid_when_stressed: str | None = None
    small_delights: str | None = None
    updated_at: str | None = None


class LoveMapRepairAgreementsPublic(BaseModel):
    protect_what_matters: str | None = None
    avoid_in_conflict: str | None = None
    repair_reentry: str | None = None
    updated_by_name: str | None = None
    updated_at: str | None = None


class LoveMapRepairAgreementFieldChangePublic(BaseModel):
    key: str
    label: str
    change_kind: Literal["added", "updated", "cleared"]
    before_text: str | None = None
    after_text: str | None = None


class LoveMapRepairAgreementChangePublic(BaseModel):
    id: str
    changed_at: str | None = None
    changed_by_name: str | None = None
    origin_kind: Literal["manual_edit", "post_mediation_carry_forward"]
    source_outcome_capture_id: str | None = None
    source_captured_by_name: str | None = None
    source_captured_at: str | None = None
    fields: list[LoveMapRepairAgreementFieldChangePublic] = Field(default_factory=list)
    # Optional short human-authored note left at save-time; null when absent.
    revision_note: str | None = None


class LoveMapRepairOutcomeCapturePublic(BaseModel):
    id: str
    repair_session_id: str
    shared_commitment: str | None = None
    improvement_note: str | None = None
    status: str
    captured_by_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


LoveLanguageChoice = Literal["words", "acts", "gifts", "time", "touch"]


class LoveMapHeartProfileUpsert(BaseModel):
    primary: LoveLanguageChoice
    secondary: LoveLanguageChoice | None = None
    support_me: str = Field(default="", max_length=500)
    avoid_when_stressed: str = Field(default="", max_length=500)
    small_delights: str = Field(default="", max_length=500)


class LoveMapHeartProfileSavePublic(BaseModel):
    care_preferences: LoveMapCarePreferencesPublic
    care_profile: LoveMapCareProfilePublic


class LoveMapRepairAgreementsUpsert(BaseModel):
    protect_what_matters: str = Field(default="", max_length=500)
    avoid_in_conflict: str = Field(default="", max_length=500)
    repair_reentry: str = Field(default="", max_length=500)
    source_outcome_capture_id: str | None = Field(default=None, max_length=64)
    # Optional human-authored revision note persisted on the change-history row.
    # Max 300 matches existing `improvement_note` cap on outcome captures.
    revision_note: str | None = Field(default=None, max_length=300)


class LoveMapWeeklyTaskPublic(BaseModel):
    task_slug: str
    task_label: str
    assigned_at: str | None = None
    completed: bool
    completed_at: str | None = None


class LoveMapSystemEssentialsPublic(BaseModel):
    my_care_preferences: LoveMapCarePreferencesPublic | None = None
    partner_care_preferences: LoveMapCarePreferencesPublic | None = None
    my_care_profile: LoveMapCareProfilePublic | None = None
    partner_care_profile: LoveMapCareProfilePublic | None = None
    repair_agreements: LoveMapRepairAgreementsPublic | None = None
    repair_agreement_history: list[LoveMapRepairAgreementChangePublic] = Field(default_factory=list)
    pending_repair_outcome_capture: LoveMapRepairOutcomeCapturePublic | None = None
    weekly_task: LoveMapWeeklyTaskPublic | None = None


class LoveMapSystemResponse(BaseModel):
    has_partner: bool
    me: LoveMapSystemMePublic
    partner: LoveMapSystemPartnerPublic | None = None
    baseline: BaselineSummaryPublic
    couple_goal: CoupleGoalPublic | None = None
    relationship_compass: LoveMapRelationshipCompassPublic | None = None
    relationship_compass_history: list[LoveMapRelationshipCompassChangePublic] = Field(
        default_factory=list
    )
    story: LoveMapStoryPublic = Field(default_factory=LoveMapStoryPublic)
    notes: list[LoveMapNotePublic] = Field(default_factory=list)
    wishlist_items: list[WishlistItemPublic] = Field(default_factory=list)
    stats: LoveMapSystemStatsPublic
    essentials: LoveMapSystemEssentialsPublic = Field(default_factory=LoveMapSystemEssentialsPublic)
