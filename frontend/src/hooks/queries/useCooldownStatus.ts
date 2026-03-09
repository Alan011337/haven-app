'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchCooldownStatus } from '@/services/api-client';

export function useCooldownStatus() {
  return useQuery({
    queryKey: queryKeys.cooldownStatus(),
    queryFn: fetchCooldownStatus,
    staleTime: 10_000,
  });
}
