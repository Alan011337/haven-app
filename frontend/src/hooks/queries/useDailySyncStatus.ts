'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { HOME_OPTIONAL_DATA_TIMEOUT_MS } from '@/lib/home-performance';
import { queryKeys } from '@/lib/query-keys';
import { fetchDailySyncStatus } from '@/services/api-client';

export function useDailySyncStatus() {
  const { user, isLoading } = useAuth();
  return useQuery({
    queryKey: queryKeys.dailySyncStatus(),
    queryFn: () => fetchDailySyncStatus({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS }),
    enabled: !isLoading && !!user,
    retry: false,
    staleTime: 60_000,
  });
}
