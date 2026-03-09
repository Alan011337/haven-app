import type { QueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import type { Journal } from '@/types';

export const sortJournalsDesc = (items: Journal[] | undefined | null): Journal[] => {
  if (!Array.isArray(items) || items.length === 0) {
    return [];
  }
  return [...items].sort(
    (a: Journal, b: Journal) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
};

export const invalidateHomeHeaderQueries = async (queryClient: QueryClient): Promise<void> => {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: queryKeys.gamificationSummary() }),
    queryClient.invalidateQueries({ queryKey: queryKeys.onboardingQuest() }),
    queryClient.invalidateQueries({ queryKey: queryKeys.syncNudges() }),
    queryClient.invalidateQueries({ queryKey: queryKeys.firstDelight() }),
  ]);
};
