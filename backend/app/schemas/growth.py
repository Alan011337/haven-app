import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlmodel import Field, SQLModel


class FeatureFlagsPublic(SQLModel):
    has_partner_context: bool
    flags: Dict[str, bool]
    kill_switches: Dict[str, bool]


class ReferralLandingViewTrackRequest(SQLModel):
    invite_code: str = Field(min_length=1, max_length=64)
    event_id: str = Field(min_length=8, max_length=128)
    source: str = Field(default="landing", min_length=1, max_length=64)
    landing_path: Optional[str] = Field(default=None, min_length=1, max_length=256)

    model_config = {"extra": "forbid"}


class ReferralSignupTrackRequest(SQLModel):
    invite_code: str = Field(min_length=1, max_length=64)
    event_id: Optional[str] = Field(default=None, min_length=8, max_length=128)
    source: str = Field(default="signup", min_length=1, max_length=64)

    model_config = {"extra": "forbid"}


class ReferralCoupleInviteTrackRequest(SQLModel):
    invite_code: str = Field(min_length=1, max_length=64)
    event_id: str = Field(min_length=8, max_length=128)
    source: str = Field(default="partner_settings", min_length=1, max_length=64)
    share_channel: Optional[str] = Field(default=None, min_length=1, max_length=32)
    landing_path: Optional[str] = Field(default="/register", min_length=1, max_length=256)

    model_config = {"extra": "forbid"}


class ReferralEventTrackResult(SQLModel):
    accepted: bool
    deduped: bool
    event_type: str


class CujEventName(str, Enum):
    RITUAL_LOAD = "RITUAL_LOAD"
    RITUAL_DRAW = "RITUAL_DRAW"
    RITUAL_RESPOND = "RITUAL_RESPOND"
    RITUAL_UNLOCK = "RITUAL_UNLOCK"
    JOURNAL_SUBMIT = "JOURNAL_SUBMIT"
    JOURNAL_PERSIST = "JOURNAL_PERSIST"
    JOURNAL_ANALYSIS_QUEUED = "JOURNAL_ANALYSIS_QUEUED"
    JOURNAL_ANALYSIS_DELIVERED = "JOURNAL_ANALYSIS_DELIVERED"
    BIND_START = "BIND_START"
    BIND_SUCCESS = "BIND_SUCCESS"
    AI_FEEDBACK_DOWNVOTE = "AI_FEEDBACK_DOWNVOTE"


class CoreLoopEventName(str, Enum):
    DAILY_SYNC_SUBMITTED = "daily_sync_submitted"
    DAILY_CARD_REVEALED = "daily_card_revealed"
    CARD_ANSWER_SUBMITTED = "card_answer_submitted"
    APPRECIATION_SENT = "appreciation_sent"
    DAILY_LOOP_COMPLETED = "daily_loop_completed"


class CujEventMode(str, Enum):
    DAILY_RITUAL = "DAILY_RITUAL"
    DECK = "DECK"
    JOURNAL = "JOURNAL"
    BIND = "BIND"


class CujEventTrackRequest(SQLModel):
    event_name: CujEventName
    event_id: str = Field(min_length=8, max_length=128)
    source: str = Field(default="web", min_length=1, max_length=64)
    mode: Optional[CujEventMode] = None
    session_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = Field(default=None, min_length=8, max_length=128)
    occurred_at: Optional[datetime] = None
    metadata_payload: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = {"extra": "forbid", "populate_by_name": True}


class CujEventTrackResult(SQLModel):
    accepted: bool
    deduped: bool
    event_name: str


class CoreLoopEventTrackRequest(SQLModel):
    event_name: CoreLoopEventName
    event_id: str = Field(min_length=8, max_length=128)
    source: str = Field(default="web", min_length=1, max_length=64)
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    device_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    occurred_at: Optional[datetime] = None
    props: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    privacy: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class CoreLoopEventTrackResult(SQLModel):
    accepted: bool
    deduped: bool
    event_name: str
    loop_completed_today: bool = False


class GamificationSummaryPublic(SQLModel):
    has_partner_context: bool
    streak_days: int
    best_streak_days: int
    streak_eligible_today: bool
    level: int
    level_points_total: int
    level_points_current: int
    level_points_target: int
    love_bar_percent: float
    level_title: str
    anti_cheat_enabled: bool


class ReengagementHookType(str, Enum):
    SOCIAL_SHARE_CARD = "SOCIAL_SHARE_CARD"
    TIME_CAPSULE = "TIME_CAPSULE"


class ReengagementHookPublic(SQLModel):
    hook_type: ReengagementHookType
    eligible: bool
    reason: str
    dedupe_key: str = Field(min_length=64, max_length=64)
    hook_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class ReengagementHooksPublic(SQLModel):
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    hooks: list[ReengagementHookPublic] = Field(default_factory=list)


class OnboardingQuestStepKey(str, Enum):
    ACCEPT_TERMS = "ACCEPT_TERMS"
    BIND_PARTNER = "BIND_PARTNER"
    CREATE_FIRST_JOURNAL = "CREATE_FIRST_JOURNAL"
    RESPOND_FIRST_CARD = "RESPOND_FIRST_CARD"
    PARTNER_FIRST_JOURNAL = "PARTNER_FIRST_JOURNAL"
    PAIR_CARD_EXCHANGE = "PAIR_CARD_EXCHANGE"
    PAIR_STREAK_2_DAYS = "PAIR_STREAK_2_DAYS"


class OnboardingQuestStepPublic(SQLModel):
    key: OnboardingQuestStepKey
    title: str
    description: str
    quest_day: int = Field(ge=1, le=7)
    completed: bool
    reason: str
    dedupe_key: str = Field(min_length=64, max_length=64)
    step_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class OnboardingQuestPublic(SQLModel):
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    completed_steps: int = Field(ge=0)
    total_steps: int = Field(ge=0)
    progress_percent: float = Field(ge=0, le=100)
    steps: list[OnboardingQuestStepPublic] = Field(default_factory=list)


class SyncNudgeType(str, Enum):
    PARTNER_JOURNAL_REPLY = "PARTNER_JOURNAL_REPLY"
    RITUAL_RESYNC = "RITUAL_RESYNC"
    STREAK_RECOVERY = "STREAK_RECOVERY"


class SyncNudgePublic(SQLModel):
    nudge_type: SyncNudgeType
    title: str
    description: str
    eligible: bool
    reason: str
    dedupe_key: str = Field(min_length=64, max_length=64)
    nudge_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class SyncNudgesPublic(SQLModel):
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    nudge_cooldown_hours: int = Field(ge=0)
    nudges: list[SyncNudgePublic] = Field(default_factory=list)


class SyncNudgeDeliverRequest(SQLModel):
    dedupe_key: str = Field(min_length=64, max_length=64)
    source: Optional[str] = Field(default="home", min_length=1, max_length=64)

    model_config = {"extra": "forbid"}


class SyncNudgeDeliverResult(SQLModel):
    accepted: bool
    deduped: bool
    nudge_type: SyncNudgeType
    dedupe_key: str
    reason: str


class FirstDelightPublic(SQLModel):
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    delivered: bool
    eligible: bool
    reason: str
    dedupe_key: Optional[str] = Field(default=None, min_length=64, max_length=64)
    title: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=240)
    first_delight_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class FirstDelightAcknowledgeRequest(SQLModel):
    dedupe_key: str = Field(min_length=64, max_length=64)
    source: Optional[str] = Field(default="home", min_length=1, max_length=64)

    model_config = {"extra": "forbid"}


class FirstDelightAcknowledgeResult(SQLModel):
    accepted: bool
    deduped: bool
    reason: str
    dedupe_key: str
