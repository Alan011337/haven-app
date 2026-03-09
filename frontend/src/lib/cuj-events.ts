/**
 * CUJ (Critical User Journey) event tracking client.
 *
 * Emits standardized stage events to POST /users/events/cuj (baseURL already includes /api)
 * for SLI computation (CP-01, CUJ-01, CUJ-02, SLO-01).
 */

import api from '@/lib/api';

export type CujEventName =
  | 'RITUAL_LOAD'
  | 'RITUAL_DRAW'
  | 'RITUAL_RESPOND'
  | 'RITUAL_UNLOCK'
  | 'JOURNAL_SUBMIT'
  | 'JOURNAL_PERSIST'
  | 'JOURNAL_ANALYSIS_QUEUED'
  | 'JOURNAL_ANALYSIS_DELIVERED'
  | 'BIND_START'
  | 'BIND_SUCCESS'
  | 'AI_FEEDBACK_DOWNVOTE';

interface CujEventPayload {
  event_name: CujEventName;
  event_id: string;
  source?: string;
  mode?: string;
  session_id?: string;
  /** Optional: same request_id across JOURNAL_* events for per-request timeline (CUJ-02). */
  request_id?: string;
  metadata?: Record<string, unknown>;
}

let _dedupeSet: Set<string> | null = null;

function _getDedupeSet(): Set<string> {
  if (!_dedupeSet) {
    _dedupeSet = new Set();
  }
  return _dedupeSet;
}

function _generateEventId(): string {
  return `fe-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Track a CUJ stage event. Fire-and-forget with client-side dedup.
 */
export function trackCujEvent(payload: CujEventPayload): void {
  const dedupeKey = `${payload.event_name}:${payload.event_id}`;
  const dedupeSet = _getDedupeSet();
  if (dedupeSet.has(dedupeKey)) {
    return;
  }
  dedupeSet.add(dedupeKey);

  // Cap dedup set to prevent memory leak
  if (dedupeSet.size > 500) {
    const firstKey = dedupeSet.values().next().value;
    if (firstKey !== undefined) {
      dedupeSet.delete(firstKey);
    }
  }

  const body: Record<string, unknown> = {
    event_name: payload.event_name,
    event_id: payload.event_id,
    source: payload.source ?? 'web',
    mode: payload.mode,
    session_id: payload.session_id,
    metadata_json: payload.metadata ? JSON.stringify(payload.metadata) : undefined,
  };
  if (payload.request_id && payload.request_id.length >= 8) {
    body.request_id = payload.request_id;
  }

  api.post('/users/events/cuj', body).catch(() => {
    // Swallow errors — CUJ tracking is non-critical
  });
}

/** Convenience: track ritual card draw */
export function trackRitualDraw(sessionId?: string): void {
  trackCujEvent({
    event_name: 'RITUAL_DRAW',
    event_id: _generateEventId(),
    mode: 'DAILY_RITUAL',
    session_id: sessionId,
  });
}

/** Convenience: track ritual respond */
export function trackRitualRespond(sessionId?: string): void {
  trackCujEvent({
    event_name: 'RITUAL_RESPOND',
    event_id: _generateEventId(),
    mode: 'DAILY_RITUAL',
    session_id: sessionId,
  });
}

/** Convenience: track ritual unlock */
export function trackRitualUnlock(sessionId?: string): void {
  trackCujEvent({
    event_name: 'RITUAL_UNLOCK',
    event_id: _generateEventId(),
    mode: 'DAILY_RITUAL',
    session_id: sessionId,
  });
}

/** Convenience: track journal submit. Pass request_id for CUJ-02 journal timeline (same as X-Request-Id on journal create). */
export function trackJournalSubmit(metadata?: Record<string, unknown>, requestId?: string): void {
  trackCujEvent({
    event_name: 'JOURNAL_SUBMIT',
    event_id: _generateEventId(),
    request_id: requestId,
    metadata,
  });
}

/** Convenience: track bind start */
export function trackBindStart(): void {
  trackCujEvent({
    event_name: 'BIND_START',
    event_id: _generateEventId(),
  });
}

/** Convenience: track bind success */
export function trackBindSuccess(): void {
  trackCujEvent({
    event_name: 'BIND_SUCCESS',
    event_id: _generateEventId(),
  });
}

/** Convenience: track AI feedback downvote (SLO-05 hallucination proxy) */
export function trackAiFeedbackDownvote(
  journalId: string,
  reason?: string,
): void {
  trackCujEvent({
    event_name: 'AI_FEEDBACK_DOWNVOTE',
    event_id: _generateEventId(),
    metadata: { journal_id: journalId, reason },
  });
}
