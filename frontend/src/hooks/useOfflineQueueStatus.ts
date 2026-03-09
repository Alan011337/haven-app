'use client';

import { useEffect, useState } from 'react';

import { getPendingCount, getFailedCount } from '@/lib/offline-queue/db';

export function useOfflineQueueStatus(): {
  pendingCount: number;
  failedCount: number;
} {
  const [pendingCount, setPendingCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);

  const refresh = () => {
    getPendingCount().then(setPendingCount).catch(() => setPendingCount(0));
    getFailedCount().then(setFailedCount).catch(() => setFailedCount(0));
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    refresh();
    const onChange = () => refresh();
    window.addEventListener('haven:offline-queue-change', onChange);
    return () => window.removeEventListener('haven:offline-queue-change', onChange);
  }, []);

  return { pendingCount, failedCount };
}
