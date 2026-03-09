export interface ApiEnvelopeError {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiEnvelope<T = unknown> {
  data: T | null;
  meta: {
    request_id?: string;
    [key: string]: unknown;
  };
  error: ApiEnvelopeError | null;
}

export function isApiEnvelopePayload(payload: unknown): payload is ApiEnvelope {
  if (!payload || typeof payload !== 'object') return false;
  const record = payload as Record<string, unknown>;
  return 'data' in record && 'meta' in record && 'error' in record;
}

export function unwrapApiEnvelopeData<T = unknown>(payload: unknown): T | unknown {
  if (!isApiEnvelopePayload(payload)) return payload;
  return payload.data;
}

export function normalizeApiEnvelopeError(payload: unknown): {
  detail: unknown;
  message: string;
  code: string;
} | null {
  if (!isApiEnvelopePayload(payload) || !payload.error) {
    return null;
  }
  const details = payload.error.details;
  return {
    detail: details ?? payload.error.message,
    message: payload.error.message,
    code: payload.error.code,
  };
}

