import { apiGet, apiPost } from '@/services/api-transport';
import type {
  FeatureFlagsResponse,
  FirstDelightAcknowledgePayload,
  FirstDelightAcknowledgeResponse,
  FirstDelightResponse,
  GamificationSummaryResponse,
  OnboardingQuestResponse,
  ReferralCoupleInviteTrackPayload,
  ReferralLandingTrackPayload,
  ReferralSignupTrackPayload,
  ReferralTrackResult,
  SyncNudgeDeliverPayload,
  SyncNudgeDeliverResponse,
  SyncNudgeType,
  SyncNudgesResponse,
} from '@/services/api-client.types';

export const fetchFeatureFlags = async (): Promise<FeatureFlagsResponse> => {
  return apiGet<FeatureFlagsResponse>('/users/feature-flags');
};

export const fetchGamificationSummary = async (): Promise<GamificationSummaryResponse> => {
  return apiGet<GamificationSummaryResponse>('/users/gamification-summary');
};

export const fetchOnboardingQuest = async () => {
  return apiGet<OnboardingQuestResponse>('/users/onboarding-quest');
};

export const fetchSyncNudges = async (): Promise<SyncNudgesResponse> => {
  return apiGet<SyncNudgesResponse>('/users/sync-nudges');
};

export const deliverSyncNudge = async (
  nudgeType: SyncNudgeType,
  payload: SyncNudgeDeliverPayload
): Promise<SyncNudgeDeliverResponse> => {
  return apiPost<SyncNudgeDeliverResponse>(`/users/sync-nudges/${nudgeType}/deliver`, payload);
};

export const fetchFirstDelight = async (): Promise<FirstDelightResponse> => {
  return apiGet<FirstDelightResponse>('/users/first-delight');
};

export const acknowledgeFirstDelight = async (
  payload: FirstDelightAcknowledgePayload
): Promise<FirstDelightAcknowledgeResponse> => {
  return apiPost<FirstDelightAcknowledgeResponse>('/users/first-delight/ack', payload);
};

export const trackReferralLandingView = async (
  payload: ReferralLandingTrackPayload
): Promise<ReferralTrackResult> => {
  return apiPost<ReferralTrackResult>('/users/referrals/landing-view', payload);
};

export const trackReferralSignup = async (
  payload: ReferralSignupTrackPayload
): Promise<ReferralTrackResult> => {
  return apiPost<ReferralTrackResult>('/users/referrals/signup', payload);
};

export const trackReferralCoupleInvite = async (
  payload: ReferralCoupleInviteTrackPayload
): Promise<ReferralTrackResult> => {
  return apiPost<ReferralTrackResult>('/users/referrals/couple-invite', payload);
};
