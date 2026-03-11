'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { cardService } from '@/services/cardService';

export function useDailyStatus(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dailyStatus(),
    queryFn: () => cardService.getDailyStatus(),
    staleTime: 30_000,
    enabled,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
