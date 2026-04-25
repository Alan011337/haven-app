import type { AxiosRequestConfig } from 'axios';
import { apiGet, apiPost, apiPut, getWithFallback } from '@/services/api-transport';
export * from '@/services/notifications-api';
export * from '@/services/engagement-api';
export * from '@/services/billing-api';
export * from '@/services/relationship-api';
export * from '@/services/daily-sync-api';
export * from '@/services/appreciations-api';
export {
  createJournal,
  deleteJournalAttachment,
  deleteJournal,
  fetchJournalById,
  fetchJournals,
  fetchJournalsPage,
  fetchPartnerJournals,
  fetchPartnerJournalsPage,
  JOURNALS_INITIAL_LIMIT,
  MAX_JOURNAL_CONTENT_LENGTH,
  updateJournal,
  updateJournalAttachmentCaption,
  uploadJournalAttachment,
} from '@/services/journals-api';
export type {
  CreateJournalOptions,
  CreateJournalResponse,
  CursorListResult,
  JournalUpsertPayload,
  UpdateJournalPayload,
} from '@/services/journals-api';
// idempotency contract marker: `createJournal` keeps `idempotencyKey` -> `Idempotency-Key` mapping in journals-api.
export type {
  ActionCardData,
  FeatureFlagsResponse,
  FirstDelightAcknowledgePayload,
  FirstDelightAcknowledgeResponse,
  FirstDelightResponse,
  GamificationSummaryResponse,
  NotificationDailyStatsItem,
  NotificationErrorReasonStatsItem,
  NotificationEventItem,
  NotificationFilters,
  NotificationMarkReadResult,
  NotificationRetryResult,
  NotificationStats,
  OnboardingQuestResponse,
  OnboardingQuestStep,
  OnboardingQuestStepKey,
  PartnerStatus,
  PushDispatchDryRunResult,
  PushSubscriptionDeleteResult,
  PushSubscriptionItem,
  PushSubscriptionPayload,
  PushSubscriptionUpsertResult,
  ReferralCoupleInviteTrackPayload,
  ReferralLandingTrackPayload,
  ReferralSignupTrackPayload,
  ReferralTrackResult,
  SyncNudgeDeliverPayload,
  SyncNudgeDeliverResponse,
  SyncNudgeItem,
  SyncNudgeType,
  SyncNudgesResponse,
} from '@/services/api-client.types';
import type {
  ActionCardData,
  PartnerStatus,
} from '@/services/api-client.types';
import type {
  BaselineSummaryPublic,
  CoupleGoalPublic,
} from '@/services/relationship-api';

const LOCAL_CARDS: Record<string, ActionCardData> = {
  card_hug: {
    key: 'card_hug',
    title: '溫柔擁抱',
    description: '先放下對錯，給對方一個不帶評價的擁抱。',
    category: 'comfort',
    difficulty_level: 1,
  },
  card_walk: {
    key: 'card_walk',
    title: '散步五分鐘',
    description: '一起走一小段路，讓情緒慢慢落地。',
    category: 'action',
    difficulty_level: 1,
  },
  card_tea: {
    key: 'card_tea',
    title: '一杯熱飲',
    description: '幫彼此準備一杯熱飲，建立安定感。',
    category: 'comfort',
    difficulty_level: 1,
  },
  card_write: {
    key: 'card_write',
    title: '一句感謝',
    description: '寫下一句今天最想謝謝對方的話。',
    category: 'connection',
    difficulty_level: 1,
  },
};

export const fetchCard = async (key: string): Promise<ActionCardData> => {
  return LOCAL_CARDS[key] ?? {
    key,
    title: key.replace(/[_-]/g, ' '),
    description: '用一句真心話，回應你最在意的那個人。',
    category: 'connection',
    difficulty_level: 1,
  };
};


export const DEFAULT_PARTNER_STATUS: PartnerStatus = {
  has_partner: false,
  latest_journal_at: null,
  current_score: 0,
  unread_notification_count: 0,
};

export const fetchPartnerStatus = async (
  config?: AxiosRequestConfig,
): Promise<PartnerStatus> => {
  return getWithFallback({
    action: () => apiGet<PartnerStatus>('/users/partner-status', config),
    fallbackValue: DEFAULT_PARTNER_STATUS,
    errorTag: 'fetch-partner-status-failed',
  });
};

// --- Module B3: Love Languages ---
export const LOVE_LANGUAGE_OPTIONS = ['words', 'acts', 'gifts', 'time', 'touch'] as const;
export type LoveLanguagePreferenceKey = (typeof LOVE_LANGUAGE_OPTIONS)[number];

export interface LoveLanguagePreferenceRecord {
  primary: LoveLanguagePreferenceKey | null;
  secondary: LoveLanguagePreferenceKey | null;
}

export interface LoveLanguagePreferencePublic {
  preference: LoveLanguagePreferenceRecord;
  updated_at: string;
}

export interface WeeklyTaskPublic {
  task_slug: string;
  task_label: string;
  assigned_at: string | null;
  completed: boolean;
  completed_at: string | null;
}

function isLoveLanguagePreferenceKey(value: unknown): value is LoveLanguagePreferenceKey {
  return typeof value === 'string' && LOVE_LANGUAGE_OPTIONS.includes(value as LoveLanguagePreferenceKey);
}

export function normalizeLoveLanguagePreference(
  value?: LoveLanguagePreferenceRecord | Record<string, unknown> | null,
): LoveLanguagePreferenceRecord {
  const primary = isLoveLanguagePreferenceKey(value?.primary) ? value.primary : null;
  const secondaryCandidate = isLoveLanguagePreferenceKey(value?.secondary) ? value.secondary : null;
  return {
    primary,
    secondary: secondaryCandidate && secondaryCandidate !== primary ? secondaryCandidate : null,
  };
}

export const fetchLoveLanguagePreference = async (): Promise<LoveLanguagePreferencePublic | null> => {
  const response = await apiGet<LoveLanguagePreferencePublic | null>('/love-languages/preference');
  if (!response) {
    return null;
  }
  return {
    ...response,
    preference: normalizeLoveLanguagePreference(response.preference),
  };
};

export const putLoveLanguagePreference = async (
  preference: LoveLanguagePreferenceRecord,
): Promise<LoveLanguagePreferencePublic> => {
  const normalizedPreference = normalizeLoveLanguagePreference(preference);
  const payload = {
    primary: normalizedPreference.primary,
    secondary: normalizedPreference.secondary,
  };
  const response = await apiPut<LoveLanguagePreferencePublic>('/love-languages/preference', {
    preference: payload,
  });
  return {
    ...response,
    preference: normalizeLoveLanguagePreference(response.preference),
  };
};

export const fetchWeeklyTask = async (
  config?: AxiosRequestConfig,
): Promise<WeeklyTaskPublic | null> => {
  return apiGet<WeeklyTaskPublic | null>('/love-languages/weekly-task', config);
};

export const completeWeeklyTask = async (): Promise<WeeklyTaskPublic> => {
  return apiPost<WeeklyTaskPublic>('/love-languages/weekly-task/complete');
};

// --- Module C1: SOS Cooldown ---
export interface CooldownStatusPublic {
  in_cooldown: boolean;
  started_by_me: boolean;
  ends_at_iso: string | null;
  remaining_seconds: number | null;
}

export const fetchCooldownStatus = async (): Promise<CooldownStatusPublic> => {
  return apiGet<CooldownStatusPublic>('/cooldown/status');
};

export const startCooldown = async (duration_minutes: number): Promise<CooldownStatusPublic> => {
  return apiPost<CooldownStatusPublic>('/cooldown/start', { duration_minutes });
};

export const rewriteMessage = async (message: string): Promise<{ rewritten: string }> => {
  return apiPost<{ rewritten: string }>('/cooldown/rewrite-message', { message });
};

// --- Module C3: Mediation ---
export interface MediationStatusPublic {
  in_mediation: boolean;
  questions: string[];
  my_answered: boolean;
  partner_answered: boolean;
  session_id?: string;
  my_answers?: string[];
  partner_answers?: string[];
  next_sop?: string;
}

export const fetchMediationStatus = async (
  config?: AxiosRequestConfig,
): Promise<MediationStatusPublic> => {
  return apiGet<MediationStatusPublic>('/mediation/status', config);
};

export const submitMediationAnswers = async (
  sessionId: string,
  answers: [string, string, string]
): Promise<{ status: string; message: string }> => {
  return apiPost<{ status: string; message: string }>('/mediation/answers', {
    session_id: sessionId,
    answers,
  });
};

export interface RepairFlowStartResult {
  accepted: boolean;
  deduped: boolean;
  session_id: string;
}

export interface RepairFlowStatusPublic {
  enabled: boolean;
  session_id: string | null;
  in_repair_flow: boolean;
  safety_mode_active: boolean;
  completed: boolean;
  outcome_capture_pending: boolean;
  current_step: number;
  my_completed_steps: number[];
  partner_completed_steps: number[];
}

export interface RepairFlowStepCompletePayload {
  session_id: string;
  step: number;
  source?: string;
  i_feel?: string;
  i_need?: string;
  mirror_text?: string;
  shared_commitment?: string;
  improvement_note?: string;
}

export interface RepairFlowStepCompleteResult {
  accepted: boolean;
  deduped: boolean;
  step: number;
  completed: boolean;
  safety_mode_active: boolean;
}

export const startRepairFlow = async (payload?: {
  source_session_id?: string;
  source?: string;
}): Promise<RepairFlowStartResult> => {
  return apiPost<RepairFlowStartResult>('/mediation/repair/start', payload ?? {});
};

export const fetchRepairFlowStatus = async (sessionId: string): Promise<RepairFlowStatusPublic> => {
  return apiGet<RepairFlowStatusPublic>('/mediation/repair/status', {
    params: { session_id: sessionId },
  });
};

export const completeRepairFlowStep = async (
  payload: RepairFlowStepCompletePayload,
): Promise<RepairFlowStepCompleteResult> => {
  return apiPost<RepairFlowStepCompleteResult>(
    '/mediation/repair/step-complete',
    payload,
  );
};

// --- Module D1: Love Map ---
export interface LoveMapCardSummary {
  id: string;
  title: string;
  description: string;
  question: string;
  depth_level: number;
  layer: string;
}

export interface LoveMapCardsResponse {
  safe: LoveMapCardSummary[];
  medium: LoveMapCardSummary[];
  deep: LoveMapCardSummary[];
}

export interface LoveMapNotePublic {
  id: string;
  layer: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface LoveMapSystemMePublic {
  id: string;
  full_name: string | null;
  email: string;
}

export interface LoveMapSystemPartnerPublic {
  id: string;
  partner_name: string | null;
}

export interface LoveMapCarePreferencesPublic extends LoveLanguagePreferenceRecord {
  updated_at: string | null;
}

export interface LoveMapCareProfilePublic {
  support_me: string | null;
  avoid_when_stressed: string | null;
  small_delights: string | null;
  updated_at: string | null;
}

export interface LoveMapRepairAgreementsPublic {
  protect_what_matters: string | null;
  avoid_in_conflict: string | null;
  repair_reentry: string | null;
  updated_by_name: string | null;
  updated_at: string | null;
}

export interface LoveMapRepairAgreementFieldChangePublic {
  key: string;
  label: string;
  change_kind: 'added' | 'updated' | 'cleared';
  before_text: string | null;
  after_text: string | null;
}

export interface LoveMapRepairAgreementChangePublic {
  id: string;
  changed_at: string | null;
  changed_by_name: string | null;
  origin_kind: 'manual_edit' | 'post_mediation_carry_forward';
  source_outcome_capture_id: string | null;
  source_captured_by_name: string | null;
  source_captured_at: string | null;
  fields: LoveMapRepairAgreementFieldChangePublic[];
  revision_note: string | null;
}

export interface LoveMapRepairOutcomeCapturePublic {
  id: string;
  repair_session_id: string;
  shared_commitment: string | null;
  improvement_note: string | null;
  status: string;
  captured_by_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LoveMapStoryMomentPublic {
  kind: 'card' | 'appreciation' | 'journal';
  title: string;
  description: string;
  occurred_at: string;
  badges: string[];
  why_text: string;
  source_id?: string | null;
}

export interface LoveMapStoryCapsulePublic {
  summary_text: string;
  from_date: string;
  to_date: string;
  journals_count: number;
  cards_count: number;
  appreciations_count: number;
}

export interface LoveMapStoryPublic {
  available: boolean;
  moments: LoveMapStoryMomentPublic[];
  time_capsule: LoveMapStoryCapsulePublic | null;
}

export type LoveMapRelationshipCompassPublic = {
  identity_statement: string | null; story_anchor: string | null; future_direction: string | null; updated_by_name: string | null; updated_at: string | null;
};

export interface LoveMapRelationshipCompassFieldChangePublic {
  key: 'identity_statement' | 'story_anchor' | 'future_direction';
  label: string;
  change_kind: 'added' | 'updated' | 'cleared';
  before_text: string | null;
  after_text: string | null;
}

export interface LoveMapRelationshipCompassChangePublic {
  id: string;
  changed_at: string | null;
  changed_by_name: string | null;
  origin_kind: 'manual_edit' | 'accepted_suggestion';
  fields: LoveMapRelationshipCompassFieldChangePublic[];
  revision_note: string | null;
}

export interface LoveMapSystemStatsPublic {
  filled_note_layers: number;
  baseline_ready_mine: boolean;
  baseline_ready_partner: boolean;
  wishlist_count: number;
  last_activity_at: string | null;
}

export interface LoveMapSystemEssentialsPublic {
  my_care_preferences: LoveMapCarePreferencesPublic | null;
  partner_care_preferences: LoveMapCarePreferencesPublic | null;
  my_care_profile: LoveMapCareProfilePublic | null;
  partner_care_profile: LoveMapCareProfilePublic | null;
  repair_agreements: LoveMapRepairAgreementsPublic | null;
  repair_agreement_history: LoveMapRepairAgreementChangePublic[];
  pending_repair_outcome_capture: LoveMapRepairOutcomeCapturePublic | null;
  weekly_task: WeeklyTaskPublic | null;
}

export interface LoveMapSystemResponse {
  has_partner: boolean;
  me: LoveMapSystemMePublic;
  partner: LoveMapSystemPartnerPublic | null;
  baseline: BaselineSummaryPublic;
  couple_goal: CoupleGoalPublic | null;
  relationship_compass: LoveMapRelationshipCompassPublic | null;
  relationship_compass_history: LoveMapRelationshipCompassChangePublic[];
  story: LoveMapStoryPublic;
  notes: LoveMapNotePublic[];
  wishlist_items: WishlistItemPublic[];
  stats: LoveMapSystemStatsPublic;
  essentials: LoveMapSystemEssentialsPublic;
}

export interface LoveMapWeeklyReviewAnswersPublic {
  understood_this_week: string | null;
  worth_carrying_forward: string | null;
  needs_care: string | null;
  next_week_intention: string | null;
}

export interface LoveMapWeeklyReviewPublic {
  week_start: string;
  my_answers: LoveMapWeeklyReviewAnswersPublic;
  partner_answers: LoveMapWeeklyReviewAnswersPublic;
  my_updated_at: string | null;
  partner_updated_at: string | null;
}

export interface LoveMapWeeklyReviewUpsertPayload {
  understood_this_week: string;
  worth_carrying_forward: string;
  needs_care: string;
  next_week_intention: string;
}

export interface RelationshipKnowledgeSuggestionEvidencePublic {
  source_kind: string;
  source_id: string;
  label: string;
  excerpt: string;
}

export interface RelationshipCompassSuggestionCandidatePublic {
  identity_statement: string | null;
  story_anchor: string | null;
  future_direction: string | null;
}

export interface RelationshipKnowledgeSuggestionPublic {
  id: string;
  section: string;
  status: string;
  generator_version: string;
  proposed_title: string;
  proposed_notes: string;
  relationship_compass_candidate: RelationshipCompassSuggestionCandidatePublic | null;
  evidence: RelationshipKnowledgeSuggestionEvidencePublic[];
  created_at: string;
  reviewed_at: string | null;
  target_wishlist_item_id: string | null;
  accepted_wishlist_item_id: string | null;
}

export const fetchLoveMapCards = async (): Promise<LoveMapCardsResponse> => {
  return apiGet<LoveMapCardsResponse>('/love-map/cards');
};

export const fetchLoveMapNotes = async (): Promise<LoveMapNotePublic[]> => {
  return apiGet<LoveMapNotePublic[]>('/love-map/notes');
};

export const fetchLoveMapSystem = async (): Promise<LoveMapSystemResponse> => {
  const response = await apiGet<LoveMapSystemResponse>('/love-map/system');
  return {
    ...response,
    relationship_compass: response.relationship_compass ?? null,
    relationship_compass_history: response.relationship_compass_history ?? [],
    essentials: {
      my_care_preferences: response.essentials?.my_care_preferences
        ? {
            ...response.essentials.my_care_preferences,
            ...normalizeLoveLanguagePreference(response.essentials.my_care_preferences),
          }
        : null,
      partner_care_preferences: response.essentials?.partner_care_preferences
        ? {
            ...response.essentials.partner_care_preferences,
            ...normalizeLoveLanguagePreference(response.essentials.partner_care_preferences),
          }
        : null,
      my_care_profile: response.essentials?.my_care_profile ?? null,
      partner_care_profile: response.essentials?.partner_care_profile ?? null,
      repair_agreements: response.essentials?.repair_agreements ?? null,
      repair_agreement_history: response.essentials?.repair_agreement_history ?? [],
      pending_repair_outcome_capture: response.essentials?.pending_repair_outcome_capture ?? null,
      weekly_task: response.essentials?.weekly_task ?? null,
    },
  };
};

export const fetchLoveMapWeeklyReviewCurrent = async (): Promise<LoveMapWeeklyReviewPublic> => {
  return apiGet<LoveMapWeeklyReviewPublic>('/love-map/weekly-review/current');
};

export const upsertLoveMapWeeklyReviewCurrent = async (
  payload: LoveMapWeeklyReviewUpsertPayload,
): Promise<LoveMapWeeklyReviewPublic> => {
  return apiPut<LoveMapWeeklyReviewPublic>('/love-map/weekly-review/current', payload);
};

export interface LoveMapHeartProfileUpsertPayload extends LoveLanguagePreferenceRecord {
  support_me: string;
  avoid_when_stressed: string;
  small_delights: string;
}

export type LoveMapRelationshipCompassUpsertPayload = {
  identity_statement: string;
  story_anchor: string;
  future_direction: string;
  revision_note?: string | null;
};

export interface LoveMapHeartProfileSavePublic {
  care_preferences: LoveMapCarePreferencesPublic;
  care_profile: LoveMapCareProfilePublic;
}

export interface LoveMapRepairAgreementsUpsertPayload {
  protect_what_matters: string;
  avoid_in_conflict: string;
  repair_reentry: string;
  source_outcome_capture_id?: string | null;
  revision_note?: string | null;
}

export const upsertLoveMapHeartProfile = async (
  payload: LoveMapHeartProfileUpsertPayload,
): Promise<LoveMapHeartProfileSavePublic> => {
  const normalizedPreference = normalizeLoveLanguagePreference(payload);
  const response = await apiPut<LoveMapHeartProfileSavePublic>('/love-map/essentials/heart-profile', {
    primary: normalizedPreference.primary,
    secondary: normalizedPreference.secondary,
    support_me: payload.support_me,
    avoid_when_stressed: payload.avoid_when_stressed,
    small_delights: payload.small_delights,
  });
  return {
    care_preferences: {
      ...response.care_preferences,
      ...normalizeLoveLanguagePreference(response.care_preferences),
    },
    care_profile: response.care_profile,
  };
};

export const upsertLoveMapRelationshipCompass = async (
  payload: LoveMapRelationshipCompassUpsertPayload,
): Promise<LoveMapRelationshipCompassPublic> => {
  return apiPut<LoveMapRelationshipCompassPublic>('/love-map/identity/compass', {
    identity_statement: payload.identity_statement,
    story_anchor: payload.story_anchor,
    future_direction: payload.future_direction,
    revision_note: payload.revision_note ?? null,
  });
};

export const upsertLoveMapRepairAgreements = async (
  payload: LoveMapRepairAgreementsUpsertPayload,
): Promise<LoveMapRepairAgreementsPublic> => {
  return apiPut<LoveMapRepairAgreementsPublic>('/love-map/essentials/repair-agreements', {
    protect_what_matters: payload.protect_what_matters,
    avoid_in_conflict: payload.avoid_in_conflict,
    repair_reentry: payload.repair_reentry,
    source_outcome_capture_id: payload.source_outcome_capture_id,
    revision_note: payload.revision_note ?? null,
  });
};

export const dismissLoveMapRepairOutcomeCapture = async (
  captureId: string,
): Promise<LoveMapRepairOutcomeCapturePublic> => {
  return apiPost<LoveMapRepairOutcomeCapturePublic>(
    `/love-map/essentials/repair-outcome-captures/${captureId}/dismiss`,
  );
};

export const fetchLoveMapSharedFutureSuggestions = async (): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiGet<RelationshipKnowledgeSuggestionPublic[]>('/love-map/suggestions/shared-future');
};

export const fetchLoveMapRelationshipCompassSuggestions = async (): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiGet<RelationshipKnowledgeSuggestionPublic[]>('/love-map/suggestions/relationship-compass');
};

export const fetchLoveMapSharedFutureRefinements = async (): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiGet<RelationshipKnowledgeSuggestionPublic[]>('/love-map/suggestions/shared-future/refinements');
};

export const generateLoveMapSharedFutureSuggestions = async (): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic[]>('/love-map/suggestions/shared-future/generate');
};

export const generateLoveMapRelationshipCompassSuggestion = async (): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic[]>('/love-map/suggestions/relationship-compass/generate');
};

export const generateLoveMapStoryAdjacentRitualSuggestion = async (): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic[]>('/love-map/suggestions/shared-future/generate-story-ritual');
};

export const generateLoveMapSharedFutureRefinement = async (
  wishlistItemId: string,
): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic[]>(
    `/love-map/suggestions/shared-future/refinements/${wishlistItemId}/generate`,
  );
};

export const generateLoveMapSharedFutureCadenceRefinement = async (
  wishlistItemId: string,
): Promise<RelationshipKnowledgeSuggestionPublic[]> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic[]>(
    `/love-map/suggestions/shared-future/refinements/${wishlistItemId}/generate-cadence`,
  );
};

export const acceptLoveMapSharedFutureSuggestion = async (
  suggestionId: string,
): Promise<WishlistItemPublic> => {
  return apiPost<WishlistItemPublic>(`/love-map/suggestions/${suggestionId}/accept`);
};

export const acceptLoveMapRelationshipCompassSuggestion = async (
  suggestionId: string,
): Promise<LoveMapRelationshipCompassPublic> => {
  return apiPost<LoveMapRelationshipCompassPublic>(
    `/love-map/suggestions/relationship-compass/${suggestionId}/accept`,
  );
};

export const dismissLoveMapSharedFutureSuggestion = async (
  suggestionId: string,
): Promise<RelationshipKnowledgeSuggestionPublic> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic>(`/love-map/suggestions/${suggestionId}/dismiss`);
};

export const dismissLoveMapRelationshipCompassSuggestion = async (
  suggestionId: string,
): Promise<RelationshipKnowledgeSuggestionPublic> => {
  return apiPost<RelationshipKnowledgeSuggestionPublic>(
    `/love-map/suggestions/relationship-compass/${suggestionId}/dismiss`,
  );
};

export const createOrUpdateLoveMapNote = async (
  layer: 'safe' | 'medium' | 'deep',
  content: string
): Promise<LoveMapNotePublic> => {
  return apiPost<LoveMapNotePublic>('/love-map/notes', { layer, content });
};

export const updateLoveMapNote = async (
  noteId: string,
  content: string
): Promise<LoveMapNotePublic> => {
  return apiPut<LoveMapNotePublic>(`/love-map/notes/${noteId}`, { content });
};

// --- Module D2: Blueprint & date suggestions ---
export interface WishlistItemPublic {
  id: string;
  title: string;
  notes: string;
  created_at: string;
  added_by_me: boolean;
}

export interface DateSuggestionPublic {
  suggested: boolean;
  message: string;
  last_activity_at: string | null;
  suggestions: string[];
}

export const fetchBlueprint = async (): Promise<WishlistItemPublic[]> => {
  return apiGet<WishlistItemPublic[]>('/blueprint/');
};

export const addBlueprintItem = async (
  title: string,
  notes?: string
): Promise<WishlistItemPublic> => {
  return apiPost<WishlistItemPublic>('/blueprint/', { title, notes: notes ?? '' });
};

export const fetchDateSuggestions = async (
  config?: AxiosRequestConfig,
): Promise<DateSuggestionPublic> => {
  return apiGet<DateSuggestionPublic>('/blueprint/date-suggestions', config);
};

// --- Module D3: Weekly Report ---
export interface WeeklyReportPublic {
  period_start: string;
  period_end: string;
  daily_sync_completion_rate: number;
  daily_sync_days_filled: number;
  partner_daily_sync_days_filled: number;
  pair_sync_overlap_days: number;
  pair_sync_alignment_rate: number | null;
  appreciation_count: number;
  insight: string | null;
}

export const fetchWeeklyReport = async (
  config?: AxiosRequestConfig,
): Promise<WeeklyReportPublic> => {
  return apiGet<WeeklyReportPublic>('/reports/weekly', config);
};
