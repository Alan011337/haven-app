import { apiGet, apiPost } from '@/services/api-transport';

export interface RelationshipBaselinePublic {
  user_id: string;
  partner_id: string | null;
  filled_at: string;
  scores: Record<string, number>;
}

export interface BaselineSummaryPublic {
  mine: RelationshipBaselinePublic | null;
  partner: RelationshipBaselinePublic | null;
}

export const BASELINE_DIMENSIONS = ['intimacy', 'conflict', 'trust', 'communication', 'commitment'] as const;

export const fetchBaseline = async (): Promise<BaselineSummaryPublic> => {
  return apiGet<BaselineSummaryPublic>('/baseline');
};

export const upsertBaseline = async (scores: Record<string, number>): Promise<RelationshipBaselinePublic> => {
  return apiPost<RelationshipBaselinePublic>('/baseline', { scores });
};

export interface CoupleGoalPublic {
  goal_slug: string;
  chosen_at: string;
}

export const COUPLE_GOAL_SLUGS = ['reduce_argument', 'increase_intimacy', 'better_communication', 'more_trust', 'other'] as const;

export const fetchCoupleGoal = async (): Promise<CoupleGoalPublic | null> => {
  return apiGet<CoupleGoalPublic | null>('/couple-goal');
};

export const setCoupleGoal = async (goalSlug: string): Promise<CoupleGoalPublic> => {
  return apiPost<CoupleGoalPublic>('/couple-goal', { goal_slug: goalSlug });
};
