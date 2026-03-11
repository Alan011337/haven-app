'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { queryKeys } from '@/lib/query-keys';
import {
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
    queryFn: () => fetchJournals({ limit: JOURNALS_INITIAL_LIMIT, offset: 0 }),
    enabled: !!user && enabled,
    staleTime: JOURNALS_STALE_TIME_MS,
  });
}
