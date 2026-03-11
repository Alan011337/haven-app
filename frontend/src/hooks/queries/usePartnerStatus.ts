'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { queryKeys } from '@/lib/query-keys';
import { fetchPartnerStatus } from '@/services/api-client';

export function usePartnerStatus() {
  const { user, isLoading } = useAuth();
  return useQuery({
    queryKey: queryKeys.partnerStatus(),
    queryFn: fetchPartnerStatus,
    enabled: !isLoading && !!user,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
