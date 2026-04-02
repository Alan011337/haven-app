'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import {
  fetchLoveMapCards,
  fetchLoveMapNotes,
  fetchLoveMapSharedFutureRefinements,
  fetchLoveMapSharedFutureSuggestions,
  fetchLoveMapSystem,
} from '@/services/api-client';

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

export function useLoveMapSystem() {
  return useQuery({
    queryKey: queryKeys.loveMapSystem(),
    queryFn: fetchLoveMapSystem,
    staleTime: 60_000,
  });
}

export function useLoveMapSharedFutureSuggestions(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.loveMapSharedFutureSuggestions(),
    queryFn: fetchLoveMapSharedFutureSuggestions,
    staleTime: 30_000,
    enabled: options?.enabled ?? true,
  });
}

export function useLoveMapSharedFutureRefinements(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.loveMapSharedFutureRefinements(),
    queryFn: fetchLoveMapSharedFutureRefinements,
    staleTime: 30_000,
    enabled: options?.enabled ?? true,
  });
}
