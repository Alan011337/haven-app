'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { fetchDeckCardCounts, type DeckCardCount } from '@/services/deckService';

export function useDeckCardCounts() {
  return useQuery({
    queryKey: queryKeys.deckCardCounts(),
    queryFn: async (): Promise<Record<string, DeckCardCount>> => {
      const stats = await fetchDeckCardCounts();
      const next: Record<string, DeckCardCount> = {};
      for (const item of stats) {
        next[item.category] = item;
      }
      return next;
    },
    staleTime: 60_000,
  });
}
