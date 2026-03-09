import { getAdaptiveIntervalMs } from '@/lib/polling-policy';

export interface AdaptivePollingOptions {
  baseIntervalMs: number;
  hiddenMultiplier?: number;
  jitterRatio?: number;
  offlineRetryMs?: number;
  runImmediately?: boolean;
  onTick: () => Promise<void> | void;
  onError?: (error: unknown) => void;
}

export function startAdaptivePolling(options: AdaptivePollingOptions): () => void {
  const {
    baseIntervalMs,
    hiddenMultiplier = 3,
    jitterRatio = 0.1,
    offlineRetryMs = 3000,
    runImmediately = true,
    onTick,
    onError,
  } = options;

  let cancelled = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const clearTimer = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const schedule = () => {
    if (cancelled) return;
    const nextInterval = getAdaptiveIntervalMs(baseIntervalMs, {
      hiddenMultiplier,
      jitterRatio,
    });
    const waitMs = nextInterval === false ? offlineRetryMs : nextInterval;
    timer = setTimeout(async () => {
      if (cancelled) return;
      if (nextInterval !== false) {
        try {
          await onTick();
        } catch (error) {
          onError?.(error);
        }
      }
      schedule();
    }, waitMs);
  };

  const handleContextChange = () => {
    if (cancelled) return;
    clearTimer();
    schedule();
  };

  if (runImmediately) {
    Promise.resolve(onTick()).catch((error) => {
      onError?.(error);
    });
  }
  schedule();

  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', handleContextChange);
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('online', handleContextChange);
    window.addEventListener('offline', handleContextChange);
  }

  return () => {
    cancelled = true;
    clearTimer();
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', handleContextChange);
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', handleContextChange);
      window.removeEventListener('offline', handleContextChange);
    }
  };
}
