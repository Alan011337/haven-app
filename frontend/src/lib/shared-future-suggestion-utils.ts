export type SharedFutureEvidenceItem = {
  source_kind: string;
  label: string;
  excerpt: string;
};

export type SharedFutureEvidenceKind = 'card' | 'appreciation' | 'story_time_capsule' | 'time_capsule_item';

const ALLOWED_EVIDENCE_KINDS: ReadonlySet<string> = new Set([
  'card',
  'appreciation',
  'story_time_capsule',
  'time_capsule_item',
]);

export function filterSharedFutureEvidence(
  evidence: readonly SharedFutureEvidenceItem[],
): SharedFutureEvidenceItem[] {
  return (Array.isArray(evidence) ? evidence : []).filter((item) =>
    ALLOWED_EVIDENCE_KINDS.has((item?.source_kind ?? '').trim().toLowerCase()),
  );
}

export function sharedFutureEvidenceKindLabel(kind: string): string {
  const normalized = (kind || '').trim().toLowerCase();
  if (normalized === 'card') return '共同卡片';
  if (normalized === 'appreciation') return '感恩';
  return 'Story';
}

export function buildSavedSharedFuturePreviewTitles(
  savedItems: readonly { title: string }[] | null | undefined,
  limit = 3,
): { titles: string[]; moreCount: number } {
  const titles = (Array.isArray(savedItems) ? savedItems : [])
    .map((item) => (item?.title ?? '').trim())
    .filter(Boolean);
  const preview = titles.slice(0, Math.max(0, limit));
  return {
    titles: preview,
    moreCount: Math.max(0, titles.length - preview.length),
  };
}

