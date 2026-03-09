const STORAGE_KEY = 'haven.optimisticSyncQueue.v1';

type PendingOperation = {
  kind: 'journal_create';
  payload: {
    contentLength: number;
    createdAt: string;
  };
};

type QueueEnvelope = {
  schemaVersion: 'v1';
  operations: PendingOperation[];
};

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function loadQueue(): QueueEnvelope {
  if (!isBrowser()) {
    return { schemaVersion: 'v1', operations: [] };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { schemaVersion: 'v1', operations: [] };
    const parsed = JSON.parse(raw) as QueueEnvelope;
    if (!parsed || parsed.schemaVersion !== 'v1' || !Array.isArray(parsed.operations)) {
      return { schemaVersion: 'v1', operations: [] };
    }
    return parsed;
  } catch {
    return { schemaVersion: 'v1', operations: [] };
  }
}

function saveQueue(envelope: QueueEnvelope): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(envelope));
}

export function enqueueOptimisticJournalFailure(content: string): void {
  const queue = loadQueue();
  queue.operations.push({
    kind: 'journal_create',
    payload: {
      contentLength: Math.max(0, content.length),
      createdAt: new Date().toISOString(),
    },
  });
  // Keep queue bounded for safety.
  if (queue.operations.length > 100) {
    queue.operations = queue.operations.slice(queue.operations.length - 100);
  }
  saveQueue(queue);
}

export function clearOptimisticSyncQueue(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getOptimisticSyncQueueSize(): number {
  return loadQueue().operations.length;
}
