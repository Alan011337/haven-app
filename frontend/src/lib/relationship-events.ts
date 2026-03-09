import api from '@/lib/api';
import { capturePosthogEvent } from '@/lib/posthog';
import {
  type CoreLoopEventName,
  sanitizeCoreLoopProps,
} from '@/lib/core-loop-event-contract';

interface CoreLoopEventPayload {
  event_name: CoreLoopEventName;
  event_id: string;
  source?: string;
  session_id?: string;
  device_id?: string;
  occurred_at?: string;
  props?: Record<string, unknown>;
  context?: Record<string, unknown>;
  privacy?: Record<string, unknown>;
}

interface CoreLoopEventResult {
  accepted: boolean;
  deduped: boolean;
  event_name: CoreLoopEventName;
  loop_completed_today?: boolean;
}

let _dedupeSet: Set<string> | null = null;

function _getDedupeSet(): Set<string> {
  if (!_dedupeSet) {
    _dedupeSet = new Set();
  }
  return _dedupeSet;
}

function _generateEventId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function _capDedupeSet(dedupeSet: Set<string>): void {
  if (dedupeSet.size <= 500) return;
  const firstKey = dedupeSet.values().next().value;
  if (firstKey !== undefined) {
    dedupeSet.delete(firstKey);
  }
}

export async function trackCoreLoopEvent(
  payload: CoreLoopEventPayload
): Promise<CoreLoopEventResult | null> {
  const dedupeKey = `${payload.event_name}:${payload.event_id}`;
  const dedupeSet = _getDedupeSet();
  if (dedupeSet.has(dedupeKey)) {
    return null;
  }
  dedupeSet.add(dedupeKey);
  _capDedupeSet(dedupeSet);

  try {
    capturePosthogEvent(payload.event_name, {
      source: payload.source ?? 'web',
      has_session: Boolean(payload.session_id),
    });
    const response = await api.post<CoreLoopEventResult>('/users/events/core-loop', {
      event_name: payload.event_name,
      event_id: payload.event_id,
      source: payload.source ?? 'web',
      session_id: payload.session_id,
      device_id: payload.device_id,
      occurred_at: payload.occurred_at,
      props: sanitizeCoreLoopProps(payload.props),
      context: payload.context ?? {},
      privacy: payload.privacy ?? {},
    });
    return response.data;
  } catch {
    // 非關鍵路徑：追蹤失敗不影響主流程
    return null;
  }
}

export function trackDailySyncSubmitted(params?: {
  mood_score?: number;
  question_id?: string | null;
}): void {
  void trackCoreLoopEvent({
    event_name: 'daily_sync_submitted',
    event_id: _generateEventId('daily-sync'),
    props: {
      mood_score: params?.mood_score,
      question_id: params?.question_id ?? undefined,
    },
  });
}

export function trackDailyCardRevealed(params?: {
  session_id?: string | null;
  card_id?: string;
}): void {
  void trackCoreLoopEvent({
    event_name: 'daily_card_revealed',
    event_id: _generateEventId('daily-reveal'),
    session_id: params?.session_id ?? undefined,
    props: {
      card_id: params?.card_id ?? undefined,
    },
  });
}

export function trackCardAnswerSubmitted(params?: {
  session_id?: string | null;
  card_id?: string;
  content_length?: number;
}): void {
  void trackCoreLoopEvent({
    event_name: 'card_answer_submitted',
    event_id: _generateEventId('card-answer'),
    session_id: params?.session_id ?? undefined,
    props: {
      card_id: params?.card_id ?? undefined,
      content_length: params?.content_length ?? undefined,
    },
  });
}

export async function trackAppreciationSent(params?: {
  content_length?: number;
}): Promise<boolean> {
  const result = await trackCoreLoopEvent({
    event_name: 'appreciation_sent',
    event_id: _generateEventId('appreciation'),
    props: {
      content_length: params?.content_length ?? undefined,
    },
  });
  return Boolean(result?.loop_completed_today);
}

export function trackDailyLoopCompleted(params?: {
  loop_id?: string;
}): void {
  void trackCoreLoopEvent({
    event_name: 'daily_loop_completed',
    event_id: params?.loop_id ?? _generateEventId('daily-loop-completed'),
    props: {
      completion_version: 'v1',
    },
  });
}
