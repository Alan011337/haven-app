/**
 * P2-F: Enqueue and replay loop. Call enqueue when a write fails (network); replay on online.
 */

import {
  addOperation,
  getOperationsByStatus,
  updateOperationStatus,
  deleteOperation,
} from './db';
import { replayOne, backoffDelayMs, shouldRetry } from './replay';
import type { OfflineOperation, OfflineOperationType } from './types';

const REPLAY_DEBOUNCE_MS = 1500;
let replayTimeout: ReturnType<typeof setTimeout> | null = null;
let isReplaying = false;

function emitQueueChange(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('haven:offline-queue-change'));
  }
}

export function generateOperationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildPayload(
  type: OfflineOperationType,
  payload: { content: string } | { card_id: string; content: string } | { session_id: string; content: string }
): OfflineOperation['payload'] {
  if (type === 'journal_create' && 'content' in payload) {
    return { journal_create: { content: payload.content } };
  }
  if (type === 'card_respond' && 'card_id' in payload) {
    return { card_respond: { card_id: payload.card_id, content: payload.content } };
  }
  if (type === 'deck_respond' && 'session_id' in payload) {
    return { deck_respond: { session_id: payload.session_id, content: payload.content } };
  }
  return {};
}

/**
 * Enqueue a write that failed (e.g. network). Call this after API throws.
 */
export async function enqueue(
  operation_id: string,
  type: OfflineOperationType,
  payload: { content: string } | { card_id: string; content: string } | { session_id: string; content: string }
): Promise<void> {
  const op: OfflineOperation = {
    operation_id,
    type,
    payload: buildPayload(type, payload),
    created_at_client: Date.now(),
    retry_count: 0,
    status: 'queued',
  };
  await addOperation(op);
  emitQueueChange();
}

/**
 * Start replay: process queued/inflight items one by one with backoff on retry.
 */
export async function startReplay(): Promise<void> {
  if (typeof window === 'undefined') return;
  if (isReplaying) return;
  isReplaying = true;
  try {
    let list = await getOperationsByStatus(['queued', 'inflight']);
    while (list.length > 0) {
      const op = list[0];
      await updateOperationStatus(op.operation_id, 'inflight');
      emitQueueChange();
      const result = await replayOne(op);
      if (result === 'acked') {
        await deleteOperation(op.operation_id);
        emitQueueChange();
      } else if (typeof result === 'object' && 'failed' in result) {
        await updateOperationStatus(
          op.operation_id,
          'failed',
          result.failed
        );
        emitQueueChange();
      } else {
        const errMsg = '網路不穩，稍後自動重試';
        if (shouldRetry(op)) {
          await updateOperationStatus(op.operation_id, 'queued', errMsg);
        } else {
          await updateOperationStatus(op.operation_id, 'failed', errMsg);
        }
        emitQueueChange();
        const delay = backoffDelayMs(op.retry_count);
        await new Promise((r) => setTimeout(r, delay));
      }
      list = await getOperationsByStatus(['queued', 'inflight']);
    }
  } finally {
    isReplaying = false;
  }
}

function scheduleReplay(): void {
  if (replayTimeout) clearTimeout(replayTimeout);
  replayTimeout = setTimeout(() => {
    replayTimeout = null;
    void startReplay();
  }, REPLAY_DEBOUNCE_MS);
}

/**
 * Call once on app init (client) to listen for online and replay.
 */
export function initOfflineReplay(): void {
  if (typeof window === 'undefined') return;
  window.addEventListener('online', scheduleReplay);
  scheduleReplay();
}
