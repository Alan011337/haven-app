export const DEFAULT_BASE_RETRY_DELAY_MS = 1_000;
export const DEFAULT_MAX_RETRY_DELAY_MS = 15_000;
export const DEFAULT_RETRY_JITTER_RATIO = 0.2;
export const SERVER_PRESSURE_CLOSE_CODES = new Set([1011, 1012, 1013]);

export type DisconnectReasonBucket = 'auth_or_policy' | 'transport_or_server';

type ReconnectDelayInput = {
  retryCount: number;
  closeCode: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  jitterRatio?: number;
  randomFn?: () => number;
};

export function classifyDisconnectReason(closeCode: number): DisconnectReasonBucket {
  return closeCode === 1008 ? 'auth_or_policy' : 'transport_or_server';
}

export function resolveReconnectCap(maxReconnectAttempts: number, closeCode: number): number {
  if (!SERVER_PRESSURE_CLOSE_CODES.has(closeCode)) {
    return maxReconnectAttempts;
  }
  return Math.max(3, Math.floor(maxReconnectAttempts / 2));
}

export function computeReconnectDelayMs({
  retryCount,
  closeCode,
  baseDelayMs = DEFAULT_BASE_RETRY_DELAY_MS,
  maxDelayMs = DEFAULT_MAX_RETRY_DELAY_MS,
  jitterRatio = DEFAULT_RETRY_JITTER_RATIO,
  randomFn = Math.random,
}: ReconnectDelayInput): number {
  const safeRetry = Math.max(0, Math.floor(retryCount));
  const safeBase = Math.max(50, Math.floor(baseDelayMs));
  const safeMax = Math.max(safeBase, Math.floor(maxDelayMs));
  let delay = Math.min(safeBase * 2 ** safeRetry, safeMax);

  if (SERVER_PRESSURE_CLOSE_CODES.has(closeCode)) {
    delay = Math.min(Math.max(delay, 2_000), 30_000);
  }

  const safeJitterRatio = Math.min(Math.max(jitterRatio, 0), 0.5);
  const rawRandom = randomFn();
  const safeRandom = Number.isFinite(rawRandom) ? Math.min(Math.max(rawRandom, 0), 1) : 0;
  const jitter = Math.floor(delay * safeJitterRatio * safeRandom);
  return delay + jitter;
}
