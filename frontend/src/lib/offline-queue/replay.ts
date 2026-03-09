/**
 * P2-F: Replay one queued operation to the server (with Idempotency-Key).
 */

import api from '@/lib/api';
import type { OfflineOperation } from './types';

const BACKOFF_BASE_MS = 1000;
const BACKOFF_MAX_MS = 30_000;
const MAX_RETRIES = 10;

export function backoffDelayMs(retryCount: number): number {
  const delay = Math.min(
    BACKOFF_BASE_MS * Math.pow(2, retryCount),
    BACKOFF_MAX_MS
  );
  return delay;
}

export type ReplayResult = 'acked' | 'retry' | { failed: string };

/**
 * Send one operation to the server. Returns acked if 2xx (or replayed), { failed: message } if 4xx, retry if network/5xx.
 * P1: Sends X-Client-Timestamp (created_at_client) for journal_create so server can apply LWW.
 */
export async function replayOne(op: OfflineOperation): Promise<ReplayResult> {
  const { operation_id, type, payload, created_at_client } = op;
  const headers: Record<string, string> = {
    'Idempotency-Key': operation_id,
    'X-Client-Timestamp': String(created_at_client),
  };

  try {
    if (type === 'journal_create' && payload.journal_create) {
      const res = await api.post('/journals/', payload.journal_create, {
        headers,
      });
      if (res.status >= 200 && res.status < 300) return 'acked';
    } else if (type === 'card_respond' && payload.card_respond) {
      const { card_id, content } = payload.card_respond;
      const res = await api.post(
        '/cards/respond',
        { card_id, content },
        { headers }
      );
      if (res.status >= 200 && res.status < 300) return 'acked';
    } else if (type === 'deck_respond' && payload.deck_respond) {
      const { session_id, content } = payload.deck_respond;
      const res = await api.post(
        `/card-decks/respond/${session_id}`,
        { content },
        { headers }
      );
      if (res.status >= 200 && res.status < 300) return 'acked';
    }
    return 'retry';
  } catch (err: unknown) {
    const status = err && typeof err === 'object' && 'response' in err
      ? (err as { response?: { status?: number; data?: { detail?: string } } }).response?.status
      : undefined;
    const detail = err && typeof err === 'object' && 'response' in err
      ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : undefined;
    if (status !== undefined && status >= 400 && status < 500) {
      const message = status === 409 ? (detail || '已由其他裝置更新，以伺服器為準') : (detail || '伺服器拒絕請求，請檢查內容後重試');
      return { failed: message };
    }
    return 'retry';
  }
}

export function shouldRetry(op: OfflineOperation): boolean {
  return op.retry_count < MAX_RETRIES;
}
