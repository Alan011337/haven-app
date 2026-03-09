import type { Journal } from '@/types';

export interface PartnerStatus {
  has_partner: boolean;
  latest_journal_at: string | null;
  current_score: number;
  unread_notification_count: number;
}

export interface ActionCardData {
  key: string;
  title: string;
  description: string;
  category: 'comfort' | 'action' | 'connection';
  difficulty_level: number;
}

export interface CreateJournalResponse extends Journal {
  new_savings_score: number;
  score_gained: number;
}

export interface NotificationMarkReadResult {
  updated: number;
}

export interface NotificationRetryResult {
  queued: boolean;
}

export interface PushSubscriptionPayload {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  expiration_time?: string | null;
  user_agent?: string | null;
}

export interface PushSubscriptionItem {
  id: string;
  state: 'ACTIVE' | 'INVALID' | 'TOMBSTONED' | 'PURGED';
  endpoint_hash: string;
  failure_count: number;
  fail_reason?: string | null;
  created_at: string;
  updated_at: string;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  dry_run_sampled_at?: string | null;
}

export interface PushSubscriptionUpsertResult {
  created: boolean;
  subscription: PushSubscriptionItem;
}

export interface PushSubscriptionDeleteResult {
  deleted: boolean;
  subscription_id: string;
}

export interface PushDispatchDryRunResult {
  channel: 'WEB_PUSH';
  enabled: boolean;
  dry_run: boolean;
  ttl_seconds: number;
  sampled_count: number;
  active_count: number;
  sampled_subscription_ids: string[];
}

export interface FeatureFlagsResponse {
  has_partner_context: boolean;
  flags: Record<string, boolean>;
  kill_switches: Record<string, boolean>;
}

export interface GamificationSummaryResponse {
  has_partner_context: boolean;
  streak_days: number;
  best_streak_days: number;
  streak_eligible_today: boolean;
  level: number;
  level_points_total: number;
  level_points_current: number;
  level_points_target: number;
  love_bar_percent: number;
  level_title: string;
  anti_cheat_enabled: boolean;
}

export type OnboardingQuestStepKey =
  | 'ACCEPT_TERMS'
  | 'BIND_PARTNER'
  | 'CREATE_FIRST_JOURNAL'
  | 'RESPOND_FIRST_CARD'
  | 'PARTNER_FIRST_JOURNAL'
  | 'PAIR_CARD_EXCHANGE'
  | 'PAIR_STREAK_2_DAYS';

export interface OnboardingQuestStep {
  key: OnboardingQuestStepKey;
  title: string;
  description: string;
  quest_day: number;
  completed: boolean;
  reason: string;
  dedupe_key: string;
  metadata: Record<string, unknown>;
}

export interface OnboardingQuestResponse {
  enabled: boolean;
  has_partner_context: boolean;
  kill_switch_active: boolean;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  steps: OnboardingQuestStep[];
}

export type SyncNudgeType =
  | 'PARTNER_JOURNAL_REPLY'
  | 'RITUAL_RESYNC'
  | 'STREAK_RECOVERY';

export interface SyncNudgeItem {
  nudge_type: SyncNudgeType;
  title: string;
  description: string;
  eligible: boolean;
  reason: string;
  dedupe_key: string;
  metadata: Record<string, unknown>;
}

export interface SyncNudgesResponse {
  enabled: boolean;
  has_partner_context: boolean;
  kill_switch_active: boolean;
  nudge_cooldown_hours: number;
  nudges: SyncNudgeItem[];
}

export interface SyncNudgeDeliverPayload {
  dedupe_key: string;
  source?: string;
}

export interface SyncNudgeDeliverResponse {
  accepted: boolean;
  deduped: boolean;
  nudge_type: SyncNudgeType;
  dedupe_key: string;
  reason: string;
}

export interface FirstDelightResponse {
  enabled: boolean;
  has_partner_context: boolean;
  kill_switch_active: boolean;
  delivered: boolean;
  eligible: boolean;
  reason: string;
  dedupe_key: string | null;
  title: string | null;
  description: string | null;
  metadata: Record<string, unknown>;
}

export interface FirstDelightAcknowledgePayload {
  dedupe_key: string;
  source?: string;
}

export interface FirstDelightAcknowledgeResponse {
  accepted: boolean;
  deduped: boolean;
  reason: string;
  dedupe_key: string;
}

export interface ReferralTrackResult {
  accepted: boolean;
  deduped: boolean;
  event_type: 'LANDING_VIEW' | 'SIGNUP' | 'COUPLE_INVITE';
}

export interface ReferralLandingTrackPayload {
  invite_code: string;
  event_id: string;
  source?: string;
  landing_path?: string;
}

export interface ReferralSignupTrackPayload {
  invite_code: string;
  event_id?: string;
  source?: string;
}

export interface ReferralCoupleInviteTrackPayload {
  invite_code: string;
  event_id: string;
  source?: string;
  share_channel?: string;
  landing_path?: string;
}

export interface NotificationEventItem {
  id: string;
  channel: string;
  action_type: 'JOURNAL' | 'CARD' | 'COOLDOWN_STARTED' | 'MEDIATION_INVITE';
  status: 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED';
  receiver_user_id?: string | null;
  sender_user_id?: string | null;
  source_session_id?: string | null;
  receiver_email: string;
  dedupe_key?: string | null;
  is_read: boolean;
  read_at?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface NotificationStats {
  total_count: number;
  unread_count: number;
  queued_count: number;
  sent_count: number;
  failed_count: number;
  throttled_count: number;
  journal_count: number;
  card_count: number;
  recent_24h_count: number;
  recent_24h_failed_count: number;
  window_days: number;
  window_total_count: number;
  window_sent_count: number;
  window_failed_count: number;
  window_throttled_count: number;
  window_queued_count: number;
  window_daily: NotificationDailyStatsItem[];
  window_top_failure_reasons: NotificationErrorReasonStatsItem[];
  last_event_at?: string | null;
}

export interface NotificationFilters {
  unread_only?: boolean;
  action_type?: 'JOURNAL' | 'CARD' | 'COOLDOWN_STARTED' | 'MEDIATION_INVITE';
  status?: 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED';
  error_reason?: string;
}

export interface NotificationDailyStatsItem {
  date: string;
  total_count: number;
  sent_count: number;
  failed_count: number;
  throttled_count: number;
  queued_count: number;
}

export interface NotificationErrorReasonStatsItem {
  reason: string;
  count: number;
}

