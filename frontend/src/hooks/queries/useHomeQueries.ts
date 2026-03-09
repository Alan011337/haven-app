'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { queryKeys } from '@/lib/query-keys';
import {
  fetchFeatureFlags,
  fetchGamificationSummary,
  fetchOnboardingQuest,
  fetchSyncNudges,
  fetchFirstDelight,
  fetchPartnerJournals,
  JOURNALS_INITIAL_LIMIT,
} from '@/services/api-client';

export function useFeatureFlags() {
  const { user } = useAuth();
  // ✅ 使用 AuthContext 檢查用戶是否登入，而不是 localStorage
  
  return useQuery({
    queryKey: queryKeys.featureFlags(),
    queryFn: fetchFeatureFlags,
    enabled: !!user,
    staleTime: 60_000,
  });
}

export function useGamificationSummary() {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.gamificationSummary(),
    queryFn: fetchGamificationSummary,
    enabled: !!user,
  });
}

export function useOnboardingQuest() {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.onboardingQuest(),
    queryFn: fetchOnboardingQuest,
    enabled: !!user,
  });
}

export function useSyncNudges() {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.syncNudges(),
    queryFn: fetchSyncNudges,
    enabled: !!user,
  });
}

export function useFirstDelight() {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.firstDelight(),
    queryFn: fetchFirstDelight,
    enabled: !!user,
  });
}

/** 1 minute: avoid refetch on every focus when user navigates back to home. */
const PARTNER_JOURNALS_STALE_TIME_MS = 60_000;

export function usePartnerJournals() {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.partnerJournals(),
    queryFn: () => fetchPartnerJournals({ limit: JOURNALS_INITIAL_LIMIT, offset: 0 }),
    enabled: !!user,
    staleTime: PARTNER_JOURNALS_STALE_TIME_MS,
  });
}
