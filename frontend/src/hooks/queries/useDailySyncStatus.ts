'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchDailySyncStatus } from '@/services/api-client';

export function useDailySyncStatus() {
  return useQuery({
    queryKey: queryKeys.dailySyncStatus(),
    queryFn: fetchDailySyncStatus,
    staleTime: 60_000,
  });
}
