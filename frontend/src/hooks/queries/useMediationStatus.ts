'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchMediationStatus } from '@/services/api-client';

export function useMediationStatus() {
  return useMediationStatusEnabled(true);
}

export function useMediationStatusEnabled(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.mediationStatus(),
    queryFn: fetchMediationStatus,
    enabled,
    staleTime: 30_000,
  });
}
