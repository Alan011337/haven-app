/**
 * P2-F Offline-First (RFC-004): operation queue types.
 * operation_id is the idempotency key sent to server (Idempotency-Key header).
 */

export type OfflineOperationType =
  | 'journal_create'
  | 'card_respond'
  | 'deck_respond';

export type OfflineOperationStatus =
  | 'queued'
  | 'inflight'
  | 'acked'
  | 'failed';

export interface OfflineOperationPayload {
  journal_create?: { content: string };
  card_respond?: { card_id: string; content: string };
  deck_respond?: { session_id: string; content: string };
}

export interface OfflineOperation {
  operation_id: string;
  type: OfflineOperationType;
  payload: OfflineOperationPayload;
  created_at_client: number;
  retry_count: number;
  last_error?: string;
  status: OfflineOperationStatus;
}

export const OFFLINE_DB_NAME = 'haven_offline_queue';
export const OFFLINE_DB_VERSION = 1;
export const OFFLINE_STORE_NAME = 'operations';
export const MAX_QUEUE_SIZE = 500;
