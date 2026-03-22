'use client';

import { useEffect } from 'react';
import { logClientError } from '@/lib/safe-error-log';

const HOME_REFRESH_INTERVAL_MS = 45_000;

type GetAdaptiveInterval = (
  baseMs: number,
  options?: { hiddenMultiplier?: number; disableWhenOffline?: boolean; jitterRatio?: number },
) => number | false;

export function useHomeAdaptiveRefresh(
  loadData: () => Promise<void>,
  getAdaptiveIntervalMs: GetAdaptiveInterval,
) {
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    let cancelled = false;
    let timer: number | null = null;

    const scheduleNextTick = () => {
      const nextInterval = getAdaptiveIntervalMs(HOME_REFRESH_INTERVAL_MS, {
        hiddenMultiplier: 4,
      });
      if (nextInterval === false || cancelled) {
        return;
      }
      timer = window.setTimeout(async () => {
        try {
          await loadData();
        } catch (error) {
          logClientError('home-adaptive-refresh-failed', error);
        } finally {
          if (!cancelled) {
            scheduleNextTick();
          }
        }
      }, nextInterval);
    };

    scheduleNextTick();

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [getAdaptiveIntervalMs, loadData]);
}
