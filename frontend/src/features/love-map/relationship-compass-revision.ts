// Pure helpers for the Relationship Compass evolution timeline.
//
// Scope: shape a `LoveMapRelationshipCompassChangePublic` row into the
// short summary line rendered under the Compass card ("調整了 身份、故事")
// and normalize the display date to a stable YYYY-MM-DD form.
//
// Kept framework-free and side-effect-free so it can run under the
// node --experimental-strip-types unit-test harness used by
// `npm run test:unit`.
//
// Source-of-truth note on labels: the server sends `label` on every
// entry in `change.fields[]`. This helper consumes that label as-is
// and does NOT maintain a parallel label dictionary. The local
// `COMPASS_FIELD_ORDER` exists ONLY for sort stability (so mixed
// updates render identity → story → future regardless of the order
// the server returns them in). If the backend ever renames a label,
// the helper picks it up automatically — no drift surface.

import type { LoveMapRelationshipCompassChangePublic } from '@/services/api-client';

const COMPASS_FIELD_ORDER = [
  'identity_statement',
  'story_anchor',
  'future_direction',
] as const;

type CompassFieldKey = (typeof COMPASS_FIELD_ORDER)[number];

function compassFieldRank(key: string): number {
  const idx = (COMPASS_FIELD_ORDER as readonly string[]).indexOf(key);
  // Unknown keys sink to the bottom rather than throwing — keeps the
  // timeline forward-compatible if the backend ever adds a 4th field.
  return idx === -1 ? COMPASS_FIELD_ORDER.length : idx;
}

export function summarizeCompassChange(
  change: LoveMapRelationshipCompassChangePublic,
): string {
  if (!change.fields.length) return '保留了原本的內容';

  const ordered = [...change.fields].sort(
    (a, b) => compassFieldRank(a.key) - compassFieldRank(b.key),
  );
  const labels = ordered.map((field) => field.label).join('、');

  const allAdded = ordered.every((field) => field.change_kind === 'added');
  if (allAdded) return `第一次寫下 ${labels}`;

  const allCleared = ordered.every((field) => field.change_kind === 'cleared');
  if (allCleared) return `暫時清空 ${labels}`;

  // Mixed kinds (added + updated, cleared + updated, etc.) all collapse
  // to the neutral verb so the timeline never over-claims. The user
  // sees the fields that moved; the detailed before/after stays in the
  // underlying row and is not surfaced here by design.
  return `調整了 ${labels}`;
}

export function formatCompassChangedAt(iso: string | null): string {
  if (!iso) return '—';
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return '—';
  const yyyy = parsed.getFullYear();
  const mm = String(parsed.getMonth() + 1).padStart(2, '0');
  const dd = String(parsed.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

// Re-export the canonical key list so product code and tests can assert
// against the same source of truth without duplicating the tuple.
export const COMPASS_FIELD_KEYS: readonly CompassFieldKey[] = COMPASS_FIELD_ORDER;
