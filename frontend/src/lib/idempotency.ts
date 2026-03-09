const MIN_IDEMPOTENCY_KEY_LENGTH = 8;

export function normalizeIdempotencyKey(raw?: string | null): string | null {
  const normalized = `${raw ?? ''}`.trim();
  if (normalized.length < MIN_IDEMPOTENCY_KEY_LENGTH) {
    return null;
  }
  return normalized;
}

export function buildIdempotencyHeaders(raw?: string | null): Record<string, string> | undefined {
  const key = normalizeIdempotencyKey(raw);
  if (!key) {
    return undefined;
  }
  return {
    'Idempotency-Key': key,
  };
}
