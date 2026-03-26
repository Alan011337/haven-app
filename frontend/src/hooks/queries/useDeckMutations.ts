'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { drawDeckCard, respondToDeckCard } from '@/services/deckService';

export function useDrawDeckCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      category,
      forceNew,
      preferredDepth,
    }: {
      category: string;
      forceNew?: boolean;
      preferredDepth?: 1 | 2 | 3;
    }) => drawDeckCard(category, forceNew ?? false, preferredDepth),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deckHistoryInfinite'] });
      queryClient.invalidateQueries({ queryKey: ['deckHistorySummary'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() });
    },
  });
}

export function useRespondToDeckCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      content,
      idempotencyKey,
    }: {
      sessionId: string;
      content: string;
      idempotencyKey?: string;
    }) => respondToDeckCard(sessionId, content, { idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deckHistoryInfinite'] });
      queryClient.invalidateQueries({ queryKey: ['deckHistorySummary'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() });
    },
  });
}
