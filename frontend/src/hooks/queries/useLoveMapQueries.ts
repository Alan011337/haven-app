'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchLoveMapCards, fetchLoveMapNotes } from '@/services/api-client';

export function useLoveMapCards() {
  return useQuery({
    queryKey: queryKeys.loveMapCards(),
    queryFn: fetchLoveMapCards,
    staleTime: 60_000,
  });
}

export function useLoveMapNotes() {
  return useQuery({
    queryKey: queryKeys.loveMapNotes(),
    queryFn: () => fetchLoveMapNotes().catch(() => []),
    staleTime: 60_000,
  });
}
