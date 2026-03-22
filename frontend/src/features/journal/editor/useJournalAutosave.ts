'use client';

import { useEffect } from 'react';

interface UseJournalAutosaveOptions {
  debounceMs?: number;
  enabled: boolean;
  onAutosave: () => unknown | Promise<unknown>;
  pending: boolean;
  snapshot: string;
}

export function shouldScheduleJournalAutosave({
  enabled,
  pending,
}: Pick<UseJournalAutosaveOptions, 'enabled' | 'pending'>) {
  return enabled && !pending;
}

export function useJournalAutosave({
  debounceMs = 1200,
  enabled,
  onAutosave,
  pending,
  snapshot,
}: UseJournalAutosaveOptions) {
  useEffect(() => {
    if (!shouldScheduleJournalAutosave({ enabled, pending })) return;

    const timer = window.setTimeout(() => {
      void onAutosave();
    }, debounceMs);

    return () => window.clearTimeout(timer);
  }, [debounceMs, enabled, onAutosave, pending, snapshot]);
}
