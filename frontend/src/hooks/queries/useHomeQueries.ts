'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import {
  HOME_OPTIONAL_AUTO_RETRY_DELAY_MS,
  HOME_OPTIONAL_DATA_TIMEOUT_MS,
  HOME_TIMELINE_TIMEOUT_MS,
} from '@/lib/home-performance';
import {
  buildHomeAppreciationHistoryQueryKey,
  getHomeAppreciationWeekRange,
} from '@/lib/home-appreciation-history';
import { queryKeys } from '@/lib/query-keys';
import {
  fetchAppreciations,
  fetchFeatureFlags,
  fetchGamificationSummary,
  fetchOnboardingQuest,
  fetchSyncNudges,
  fetchFirstDelight,
  fetchPartnerJournals,
  JOURNALS_INITIAL_LIMIT,
} from '@/services/api-client';
import type { AppreciationPublic } from '@/services/api-client';

export interface HomeAppreciationHistory {
  recent: AppreciationPublic[];
  thisWeek: AppreciationPublic[];
  weekRange: {
    from: string;
    to: string;
  };
}

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

export function useHomeAppreciationHistory(enabled = true) {
  const { user } = useAuth();
  const weekRange = useMemo(() => getHomeAppreciationWeekRange(), []);

  return useQuery<HomeAppreciationHistory>({
    queryKey: buildHomeAppreciationHistoryQueryKey(weekRange.from, weekRange.to),
    queryFn: async () => {
      const recent = await fetchAppreciations(
        { limit: 20 },
        { timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS },
      );
      const thisWeek = await fetchAppreciations(
        { from_date: weekRange.from, to_date: weekRange.to, limit: 50 },
        { timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS },
      );
      return {
        recent,
        thisWeek,
        weekRange,
      };
    },
    enabled: !!user && enabled,
    retry: 1,
    retryDelay: HOME_OPTIONAL_AUTO_RETRY_DELAY_MS,
    staleTime: 60_000,
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
