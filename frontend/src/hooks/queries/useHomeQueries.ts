'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { HOME_TIMELINE_TIMEOUT_MS } from '@/lib/home-performance';
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

export function useFeatureFlags(enabled = true) {
  const { user } = useAuth();
  // ✅ 使用 AuthContext 檢查用戶是否登入，而不是 localStorage
  
  return useQuery({
    queryKey: queryKeys.featureFlags(),
    queryFn: fetchFeatureFlags,
    enabled: !!user && enabled,
    staleTime: 60_000,
  });
}

export function useGamificationSummary(enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.gamificationSummary(),
    queryFn: fetchGamificationSummary,
    enabled: !!user && enabled,
  });
}

export function useOnboardingQuest(enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.onboardingQuest(),
    queryFn: fetchOnboardingQuest,
    enabled: !!user && enabled,
  });
}

export function useSyncNudges(enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.syncNudges(),
    queryFn: fetchSyncNudges,
    enabled: !!user && enabled,
  });
}

export function useFirstDelight(enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.firstDelight(),
    queryFn: fetchFirstDelight,
    enabled: !!user && enabled,
  });
}

/** 1 minute: avoid refetch on every focus when user navigates back to home. */
const PARTNER_JOURNALS_STALE_TIME_MS = 60_000;

export function usePartnerJournals(enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: queryKeys.partnerJournals(),
    queryFn: () =>
      fetchPartnerJournals(
        { limit: JOURNALS_INITIAL_LIMIT, offset: 0 },
        { timeout: HOME_TIMELINE_TIMEOUT_MS },
      ),
    enabled: !!user && enabled,
    staleTime: PARTNER_JOURNALS_STALE_TIME_MS,
    retry: false,
  });
}
