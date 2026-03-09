'use client';

import { useEffect } from 'react';

import { initOfflineReplay } from '@/lib/offline-queue/queue';

export default function OfflineReplayBootstrap(): null {
  useEffect(() => {
    initOfflineReplay();
  }, []);

  return null;
}
