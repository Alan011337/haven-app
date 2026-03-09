'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchPartnerStatus } from '@/services/api-client';

export function usePartnerStatus() {
  return useQuery({
    queryKey: queryKeys.partnerStatus(),
    queryFn: fetchPartnerStatus,
    // Only run on client; fetchPartnerStatus returns default when no token
    enabled: typeof window !== 'undefined',
  });
}
