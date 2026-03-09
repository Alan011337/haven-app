/**
 * P2-F: IndexedDB access for offline operation queue.
 */

import {
  OFFLINE_DB_NAME,
  OFFLINE_DB_VERSION,
  OFFLINE_STORE_NAME,
  MAX_QUEUE_SIZE,
  type OfflineOperation,
  type OfflineOperationStatus,
} from './types';

let dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (typeof window === 'undefined' || !window.indexedDB) {
    return Promise.reject(new Error('IndexedDB not available'));
  }
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = window.indexedDB.open(OFFLINE_DB_NAME, OFFLINE_DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(OFFLINE_STORE_NAME)) {
        const store = db.createObjectStore(OFFLINE_STORE_NAME, {
          keyPath: 'operation_id',
        });
        store.createIndex('status', 'status', { unique: false });
        store.createIndex('created_at_client', 'created_at_client', {
          unique: false,
        });
      }
    };
  });
  return dbPromise;
}

export async function addOperation(op: OfflineOperation): Promise<void> {
  const db = await openDB();
  const count = await getCount(db);
  if (count >= MAX_QUEUE_SIZE) {
    throw new Error(
      `離線佇列已滿 (最多 ${MAX_QUEUE_SIZE} 筆)，請連線後同步再試。`
    );
  }
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_STORE_NAME);
    const req = store.add(op);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

function getCount(db: IDBDatabase): Promise<number> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readonly');
    const req = tx.objectStore(OFFLINE_STORE_NAME).count();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function getOperationsByStatus(
  statuses: OfflineOperationStatus[]
): Promise<OfflineOperation[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readonly');
    const store = tx.objectStore(OFFLINE_STORE_NAME);
    const index = store.index('status');
    const results: OfflineOperation[] = [];
    let pending = statuses.length;
    if (pending === 0) {
      resolve(results);
      return;
    }
    statuses.forEach((status) => {
      const req = index.getAll(IDBKeyRange.only(status));
      req.onsuccess = () => {
        results.push(...(req.result as OfflineOperation[]));
        pending--;
        if (pending === 0) {
          results.sort((a, b) => a.created_at_client - b.created_at_client);
          resolve(results);
        }
      };
      req.onerror = () => reject(req.error);
    });
  });
}

export async function updateOperationStatus(
  operation_id: string,
  status: OfflineOperationStatus,
  last_error?: string
): Promise<void> {
  const db = await openDB();
  const op = await getOperation(db, operation_id);
  if (!op) return;
  const updated: OfflineOperation = {
    ...op,
    status,
    ...(last_error !== undefined && { last_error }),
    ...(status === 'inflight' && { retry_count: op.retry_count + 1 }),
  };
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readwrite');
    const req = tx.objectStore(OFFLINE_STORE_NAME).put(updated);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

function getOperation(
  db: IDBDatabase,
  operation_id: string
): Promise<OfflineOperation | null> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readonly');
    const req = tx.objectStore(OFFLINE_STORE_NAME).get(operation_id);
    req.onsuccess = () => resolve(req.result ?? null);
    req.onerror = () => reject(req.error);
  });
}

export async function deleteOperation(operation_id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_STORE_NAME, 'readwrite');
    const req = tx.objectStore(OFFLINE_STORE_NAME).delete(operation_id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getPendingCount(): Promise<number> {
  const list = await getOperationsByStatus(['queued', 'inflight']);
  return list.length;
}

export async function getFailedCount(): Promise<number> {
  const list = await getOperationsByStatus(['failed']);
  return list.length;
}

export async function getAllPendingAndFailed(): Promise<OfflineOperation[]> {
  return getOperationsByStatus(['queued', 'inflight', 'failed']);
}
