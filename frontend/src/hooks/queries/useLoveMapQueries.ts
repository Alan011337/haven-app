'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import {
  fetchLoveMapCards,
  fetchLoveMapNotes,
  fetchLoveMapRelationshipCompassSuggestions,
  fetchLoveMapSharedFutureRefinements,
  fetchLoveMapSharedFutureSuggestions,
  fetchLoveMapSystem,
  fetchLoveMapWeeklyReviewCurrent,
} from '@/services/api-client';

export const loveMapRelationshipCompassSuggestionsQueryKey = ['loveMapRelationshipCompassSuggestions'] as const;

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

export function useLoveMapWeeklyReviewCurrent(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['loveMapWeeklyReviewCurrent'] as const,
    queryFn: fetchLoveMapWeeklyReviewCurrent,
    staleTime: 30_000,
    enabled: options?.enabled ?? true,
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

export function useLoveMapRelationshipCompassSuggestions(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: loveMapRelationshipCompassSuggestionsQueryKey,
    queryFn: fetchLoveMapRelationshipCompassSuggestions,
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
