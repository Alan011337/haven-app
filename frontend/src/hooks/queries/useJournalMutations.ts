'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { enqueueOptimisticJournalFailure } from '@/lib/optimistic-sync';
import { logClientError } from '@/lib/safe-error-log';
import { createJournal, deleteJournal, type CreateJournalOptions } from '@/services/api-client';

export function useCreateJournal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ content, options }: { content: string; options?: CreateJournalOptions }) =>
      createJournal(content, options),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.journals() });
      await queryClient.cancelQueries({ queryKey: queryKeys.partnerJournals() });
      await queryClient.cancelQueries({ queryKey: queryKeys.partnerStatus() });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() });
    },
    onError: (error, variables) => {
      enqueueOptimisticJournalFailure(variables.content);
      logClientError('journal_create_mutation_failed', error);
      queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() });
    },
  });
}

export function useDeleteJournal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string | number) => deleteJournal(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() });
    },
  });
}
