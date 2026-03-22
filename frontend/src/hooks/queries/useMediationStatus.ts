'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { HOME_OPTIONAL_AUTO_RETRY_DELAY_MS, HOME_OPTIONAL_DATA_TIMEOUT_MS } from '@/lib/home-performance';
import { queryKeys } from '@/lib/query-keys';
import { fetchMediationStatus } from '@/services/api-client';

export function useMediationStatus() {
  return useMediationStatusEnabled(true);
}

export function useMediationStatusEnabled(enabled: boolean) {
  const { user, isLoading } = useAuth();
  return useQuery({
    queryKey: queryKeys.mediationStatus(),
    queryFn: () => fetchMediationStatus({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS }),
    enabled: enabled && !isLoading && !!user,
    retry: 1,
    retryDelay: HOME_OPTIONAL_AUTO_RETRY_DELAY_MS,
    staleTime: 30_000,
  });
}
