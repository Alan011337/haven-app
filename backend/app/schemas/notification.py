import uuid
from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class NotificationEventPublic(SQLModel):
    id: uuid.UUID
    channel: str
    action_type: str
    status: str
    receiver_user_id: Optional[uuid.UUID] = None
    sender_user_id: Optional[uuid.UUID] = None
    source_session_id: Optional[uuid.UUID] = None
    receiver_email: str
    dedupe_key: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class NotificationMarkReadResult(SQLModel):
    updated: int


class NotificationRetryResult(SQLModel):
    queued: bool


class NotificationDailyStatsPublic(SQLModel):
    date: date
    total_count: int
    sent_count: int
    failed_count: int
    throttled_count: int
    queued_count: int


class NotificationErrorReasonStatsPublic(SQLModel):
    reason: str
    count: int


class NotificationStatsPublic(SQLModel):
    total_count: int
    unread_count: int
    queued_count: int
    sent_count: int
    failed_count: int
    throttled_count: int
    journal_count: int
    card_count: int
    recent_24h_count: int
    recent_24h_failed_count: int
    window_days: int
    window_total_count: int
    window_sent_count: int
    window_failed_count: int
    window_throttled_count: int
    window_queued_count: int
    window_daily: list[NotificationDailyStatsPublic]
    window_top_failure_reasons: list[NotificationErrorReasonStatsPublic]
    last_event_at: Optional[datetime] = None


class PushSubscriptionKeysIn(SQLModel):
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)
    model_config = {"extra": "forbid"}


class PushSubscriptionCreate(SQLModel):
    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushSubscriptionKeysIn
    expiration_time: Optional[datetime] = None
    user_agent: Optional[str] = Field(default=None, max_length=512)
    model_config = {"extra": "forbid"}


class PushSubscriptionPublic(SQLModel):
    id: uuid.UUID
    state: str
    endpoint_hash: str
    failure_count: int
    fail_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    dry_run_sampled_at: Optional[datetime] = None


class PushSubscriptionUpsertResult(SQLModel):
    created: bool
    subscription: PushSubscriptionPublic


class PushSubscriptionDeleteResult(SQLModel):
    deleted: bool
    subscription_id: uuid.UUID


class PushDispatchDryRunRequest(SQLModel):
    sample_size: Optional[int] = Field(default=None, ge=1, le=20)
    ttl_seconds: Optional[int] = Field(default=None, ge=60, le=86400)
    model_config = {"extra": "forbid"}


class PushDispatchDryRunResult(SQLModel):
    channel: str = "WEB_PUSH"
    enabled: bool
    dry_run: bool = True
    ttl_seconds: int
    sampled_count: int
    active_count: int
    sampled_subscription_ids: list[uuid.UUID] = Field(default_factory=list)
