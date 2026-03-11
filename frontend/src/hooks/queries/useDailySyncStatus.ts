'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { queryKeys } from '@/lib/query-keys';
import { fetchDailySyncStatus } from '@/services/api-client';

export function useDailySyncStatus() {
  const { user, isLoading } = useAuth();
  return useQuery({
    queryKey: queryKeys.dailySyncStatus(),
    queryFn: fetchDailySyncStatus,
    enabled: !isLoading && !!user,
    staleTime: 60_000,
  });
}
