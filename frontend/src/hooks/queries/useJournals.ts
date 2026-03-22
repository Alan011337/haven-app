'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { queryKeys } from '@/lib/query-keys';
import { HOME_TIMELINE_TIMEOUT_MS } from '@/lib/home-performance';
import {
  fetchJournalById,
  fetchJournals,
  JOURNALS_INITIAL_LIMIT,
} from '@/services/api-client';

/** 1 minute: avoid refetch on every focus when user navigates back to home. */
const JOURNALS_STALE_TIME_MS = 60_000;

export function useJournals(enabled = true) {
  const { user } = useAuth();
  // ✅ 使用 AuthContext 檢查用戶是否登入，而不是 localStorage
  
  return useQuery({
    queryKey: queryKeys.journals(),
    queryFn: () =>
      fetchJournals(
        { limit: JOURNALS_INITIAL_LIMIT, offset: 0 },
        { timeout: HOME_TIMELINE_TIMEOUT_MS },
      ),
    enabled: !!user && enabled,
    staleTime: JOURNALS_STALE_TIME_MS,
    retry: false,
  });
}

export function useJournalDetail(journalId: string | null, enabled = true) {
  const { user } = useAuth();

  return useQuery({
    queryKey: journalId ? queryKeys.journalDetail(journalId) : ['journalDetail', 'missing'],
    queryFn: () => fetchJournalById(journalId ?? ''),
    enabled: !!user && !!journalId && enabled,
    staleTime: JOURNALS_STALE_TIME_MS,
    retry: false,
  });
}
