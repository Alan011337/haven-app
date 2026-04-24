import type { LoveMapRelationshipCompassPublic, RelationshipKnowledgeSuggestionEvidencePublic } from '@/services/api-client';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isUuidLike(value: string): boolean {
  return UUID_RE.test(value);
}

/**
 * Trims; empty string means "unset" for display/diff.
 */
export function normalizeCompassFieldValue(value: string | null | undefined): string {
  return (value ?? '').trim();
}

export function compassFieldValuesEqual(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  return normalizeCompassFieldValue(a) === normalizeCompassFieldValue(b);
}

export type CompassFieldKey = 'identity_statement' | 'story_anchor' | 'future_direction';

const COMPASS_FIELD_KEYS: CompassFieldKey[] = ['identity_statement', 'story_anchor', 'future_direction'];

/**
 * How many of the three compass fields differ between saved and candidate (trimmed).
 */
export function countCompassFieldDifferences(
  saved: LoveMapRelationshipCompassPublic | null,
  candidate: Record<CompassFieldKey, string | null | undefined> | null | undefined,
): number {
  if (!candidate) return 0;
  let n = 0;
  for (const key of COMPASS_FIELD_KEYS) {
    const s = saved?.[key];
    const c = candidate[key];
    if (!compassFieldValuesEqual(s, c)) n += 1;
  }
  return n;
}

/**
 * Returns a product-native href when the evidence can be opened safely. Conservative:
 * only journal entries with a UUID `source_id` (matches Analysis deep-link trust bar).
 */
export function buildCompassSuggestionEvidenceArtifactHref(
  item: Pick<RelationshipKnowledgeSuggestionEvidencePublic, 'source_kind' | 'source_id'>,
): string | null {
  const kind = (item.source_kind || '').toLowerCase().trim();
  const id = normalizeCompassFieldValue(item.source_id);
  if (kind === 'journal' && id && isUuidLike(id)) {
    return `/journal/${encodeURIComponent(id)}`;
  }
  return null;
}
