# backend/app/models/__init__.py

# 1. 基礎 User (最先載入)
from .user import User, UserRead, UserCreate, UserUpdate

# 2. Card 相關 (因為 Journal 會用到 Card 和 CardDeck，所以要先載入)
from .card import Card, CardRead, CardCategory, CardDeck
from .card_session import CardSession, CardSessionRead, DeckHistoryEntry
from .card_response import CardResponse

# 3. Journal (參照了 User 和 CardDeck)
from .journal import Journal, JournalRead

# 4. Analysis (參照了 Journal)
from .analysis import Analysis, AnalysisRead
from .notification_event import NotificationEvent, NotificationEventRead
from .notification_outbox import NotificationOutbox, NotificationOutboxStatus
from .push_subscription import PushSubscription, PushSubscriptionState
from .growth_referral_event import GrowthReferralEvent, GrowthReferralEventType
from .cuj_event import CujEvent
from .api_idempotency_record import ApiIdempotencyRecord
from .events_log import EventsLog
from .events_log_daily_rollup import EventsLogDailyRollup
from .gamification_score_event import GamificationEventType, GamificationScoreEvent
from .billing import (
    BillingCommandLog,
    BillingCustomerBinding,
    BillingEntitlementState,
    BillingLedgerEntry,
    BillingWebhookReceipt,
)
from .audit_event import AuditEvent, AuditEventOutcome
from .consent_receipt import ConsentReceipt
from .auth_refresh_session import AuthRefreshSession
from .entitlement_usage_daily import EntitlementUsageDaily
from .user_streak_summary import UserStreakSummary
from .mediation_session import MediationSession
from .mediation_answer import MediationAnswer
from .offline_operation_log import OfflineOperationLog
from .content_report import ContentReport, ContentReportStatus, ContentReportResourceType
from .user_onboarding_consent import UserOnboardingConsent
from .relationship_baseline import RelationshipBaseline
from .couple_goal import CoupleGoal
from .daily_sync import DailySync
from .appreciation import Appreciation
from .love_language import LoveLanguagePreference, LoveLanguageTaskAssignment
from .cool_down_session import CoolDownSession
from .love_map_note import LoveMapNote, LoveMapLayer
from .wishlist_item import WishlistItem

__all__ = [
    "Analysis",
    "AnalysisRead",
    "ApiIdempotencyRecord",
    "Appreciation",
    "AuditEvent",
    "AuditEventOutcome",
    "AuthRefreshSession",
    "BillingCommandLog",
    "BillingCustomerBinding",
    "BillingEntitlementState",
    "BillingLedgerEntry",
    "BillingWebhookReceipt",
    "Card",
    "CardCategory",
    "CardDeck",
    "CardRead",
    "CardResponse",
    "CardSession",
    "CardSessionRead",
    "ConsentReceipt",
    "ContentReport",
    "ContentReportResourceType",
    "ContentReportStatus",
    "CoolDownSession",
    "CoupleGoal",
    "CujEvent",
    "DailySync",
    "DeckHistoryEntry",
    "EntitlementUsageDaily",
    "EventsLog",
    "EventsLogDailyRollup",
    "GamificationEventType",
    "GamificationScoreEvent",
    "GrowthReferralEvent",
    "GrowthReferralEventType",
    "Journal",
    "JournalRead",
    "LoveLanguagePreference",
    "LoveLanguageTaskAssignment",
    "LoveMapLayer",
    "LoveMapNote",
    "MediationAnswer",
    "MediationSession",
    "NotificationEvent",
    "NotificationEventRead",
    "NotificationOutbox",
    "NotificationOutboxStatus",
    "OfflineOperationLog",
    "PushSubscription",
    "PushSubscriptionState",
    "RelationshipBaseline",
    "User",
    "UserCreate",
    "UserOnboardingConsent",
    "UserRead",
    "UserStreakSummary",
    "UserUpdate",
    "WishlistItem",
]
