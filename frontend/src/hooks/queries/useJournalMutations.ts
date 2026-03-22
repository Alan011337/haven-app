'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { enqueueOptimisticJournalFailure } from '@/lib/optimistic-sync';
import { logClientError } from '@/lib/safe-error-log';
import {
  createJournal,
  deleteJournal,
  deleteJournalAttachment,
  type CreateJournalOptions,
  type JournalUpsertPayload,
  updateJournal,
  uploadJournalAttachment,
} from '@/services/api-client';

export function useCreateJournal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ draft, options }: { draft: string | JournalUpsertPayload; options?: CreateJournalOptions }) =>
      createJournal(draft, options),
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
      const content =
        typeof variables.draft === 'string' ? variables.draft : variables.draft.content;
      enqueueOptimisticJournalFailure(content);
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

export function useUpdateJournal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { content?: string; is_draft?: boolean; title?: string | null; visibility?: JournalUpsertPayload['visibility'] } }) =>
      updateJournal(id, payload),
    onSuccess: (journal) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerStatus() });
      queryClient.setQueryData(queryKeys.journalDetail(journal.id), journal);
    },
  });
}

export function useUploadJournalAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ journalId, file }: { journalId: string; file: File }) =>
      uploadJournalAttachment(journalId, file),
    onSuccess: (_attachment, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.journalDetail(variables.journalId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
    },
  });
}

export function useDeleteJournalAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ journalId, attachmentId }: { journalId: string; attachmentId: string }) =>
      deleteJournalAttachment(journalId, attachmentId),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.journalDetail(variables.journalId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
    },
  });
}
