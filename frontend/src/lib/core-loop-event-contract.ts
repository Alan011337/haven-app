export const CORE_LOOP_EVENT_NAMES = [
  'daily_sync_submitted',
  'daily_card_revealed',
  'card_answer_submitted',
  'appreciation_sent',
  'daily_loop_completed',
] as const;

export type CoreLoopEventName = (typeof CORE_LOOP_EVENT_NAMES)[number];

// Keep this list aligned with backend/app/services/events_sanitize.py: ALLOWED_PROPS_KEYS.
export const CORE_LOOP_ALLOWED_PROPS = [
  'loop_version',
  'mood_label',
  'mood_score',
  'question_id',
  'card_id',
  'answered_by',
  'time_spent_sec',
  'content_length',
  'relationship_stage',
  'feature_flags',
  'auto_generated',
  'completion_version',
  'reaction',
  'flow_step',
  'step',
  'event_version',
] as const;

const ALLOWED_PROPS_SET = new Set<string>(CORE_LOOP_ALLOWED_PROPS);

export function sanitizeCoreLoopProps(
  props?: Record<string, unknown>,
): Record<string, unknown> {
  if (!props) return {};
  const cleaned: Record<string, unknown> = {};
  for (const [rawKey, value] of Object.entries(props)) {
    const key = `${rawKey}`.trim().toLowerCase();
    if (!key || !ALLOWED_PROPS_SET.has(key)) continue;
    if (
      value === null ||
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      cleaned[key] = value;
    }
  }
  return cleaned;
}

