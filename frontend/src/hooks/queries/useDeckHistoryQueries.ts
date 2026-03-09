'use client';

import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import {
  fetchDeckHistory,
  fetchDeckHistorySummary,
  type DeckHistorySummary,
} from '@/services/deckService';

const PAGE_SIZE = 20;

export function useDeckHistoryInfiniteQuery(
  category: string | undefined,
  dateFilter: { revealed_from?: string; revealed_to?: string }
) {
  return useInfiniteQuery({
    queryKey: queryKeys.deckHistoryInfinite(
      category ?? '',
      dateFilter.revealed_from ?? '',
      dateFilter.revealed_to ?? ''
    ),
    queryFn: ({ pageParam }) =>
      fetchDeckHistory({
        category,
        limit: PAGE_SIZE,
        offset: pageParam as number,
        ...dateFilter,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((acc, p) => acc + p.length, 0);
      if (lastPage.length < PAGE_SIZE) return undefined;
      return totalFetched;
    },
    enabled: typeof window !== 'undefined',
  });
}

export function useDeckHistorySummaryQuery(
  category: string | undefined,
  dateFilter: { revealed_from?: string; revealed_to?: string }
) {
  return useQuery<DeckHistorySummary>({
    queryKey: queryKeys.deckHistorySummary(
      category ?? '',
      dateFilter.revealed_from ?? '',
      dateFilter.revealed_to ?? ''
    ),
    queryFn: () =>
      fetchDeckHistorySummary({
        category,
        ...dateFilter,
      }),
    enabled: typeof window !== 'undefined',
  });
}
