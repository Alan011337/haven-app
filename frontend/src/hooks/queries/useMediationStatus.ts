'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { queryKeys } from '@/lib/query-keys';
import { fetchMediationStatus } from '@/services/api-client';

export function useMediationStatus() {
  return useMediationStatusEnabled(true);
}

export function useMediationStatusEnabled(enabled: boolean) {
  const { user, isLoading } = useAuth();
  return useQuery({
    queryKey: queryKeys.mediationStatus(),
    queryFn: fetchMediationStatus,
    enabled: enabled && !isLoading && !!user,
    staleTime: 30_000,
  });
}
