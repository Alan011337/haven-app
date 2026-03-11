'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { HOME_STATUS_TIMEOUT_MS } from '@/lib/home-performance';
import { queryKeys } from '@/lib/query-keys';
import { DEFAULT_PARTNER_STATUS, fetchPartnerStatus } from '@/services/api-client';

export function usePartnerStatus() {
  const { user, isLoading } = useAuth();
  return useQuery({
    queryKey: queryKeys.partnerStatus(),
    queryFn: () => fetchPartnerStatus({ timeout: HOME_STATUS_TIMEOUT_MS }),
    enabled: !isLoading && !!user,
    staleTime: 30_000,
    initialData: DEFAULT_PARTNER_STATUS,
    retry: false,
    refetchOnWindowFocus: false,
  });
}
