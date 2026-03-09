const DEFAULT_HIDDEN_MULTIPLIER = 3;
const DEFAULT_OFFLINE_DISABLE = true;

export type AdaptivePollingOptions = {
  hiddenMultiplier?: number;
  disableWhenOffline?: boolean;
  jitterRatio?: number;
};

export function getAdaptiveIntervalMs(
  baseMs: number,
  options?: AdaptivePollingOptions,
): number | false {
  const safeBaseMs = Math.max(250, Number(baseMs) || 1000);
  if (typeof window === 'undefined') {
    return safeBaseMs;
  }
  const disableWhenOffline = options?.disableWhenOffline ?? DEFAULT_OFFLINE_DISABLE;
  if (disableWhenOffline && typeof navigator !== 'undefined' && !navigator.onLine) {
    return false;
  }
  const hiddenMultiplier = Math.max(1, Number(options?.hiddenMultiplier) || DEFAULT_HIDDEN_MULTIPLIER);
  if (typeof document !== 'undefined' && document.hidden) {
    const hiddenInterval = Math.round(safeBaseMs * hiddenMultiplier);
    const jitterRatio = Math.max(0, Math.min(0.5, Number(options?.jitterRatio) || 0));
    if (jitterRatio <= 0) return hiddenInterval;
    const jitter = Math.round(hiddenInterval * jitterRatio * Math.random());
    return hiddenInterval + jitter;
  }
  const jitterRatio = Math.max(0, Math.min(0.5, Number(options?.jitterRatio) || 0));
  if (jitterRatio <= 0) return safeBaseMs;
  const jitter = Math.round(safeBaseMs * jitterRatio * Math.random());
  return safeBaseMs + jitter;
}

export function buildAdaptiveRefetchInterval(
  baseMs: number,
  options?: AdaptivePollingOptions,
): () => number | false {
  return () => getAdaptiveIntervalMs(baseMs, options);
}
