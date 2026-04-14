export type JournalOutlineEntry = {
  depth: 0 | 1 | 2;
  id: string;
  kind: 'heading' | 'title';
  label: string;
};

const FENCED_CODE_BLOCK_RE = /^\s*```/;
const HEADING_RE = /^\s{0,3}(#{1,2})\s+(.+?)\s*#*\s*$/;
const IMAGE_ONLY_RE = /^!\[[^\]]*]\((?:attachment:[^)]+|https?:\/\/[^)]+)\)$/;

function normalizeOutlineLabel(value: string) {
  return value.replace(/\s+/g, ' ').trim();
}

function buildOutlineSlug(label: string) {
  const normalized = label
    .normalize('NFKD')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  return normalized || 'section';
}

function buildSectionId(slug: string, seenCounts: Map<string, number>) {
  const nextCount = (seenCounts.get(slug) ?? 0) + 1;
  seenCounts.set(slug, nextCount);
  return nextCount === 1 ? slug : `${slug}-${nextCount}`;
}

function isMeaningfulOutlineLabel(value: string) {
  const normalized = normalizeOutlineLabel(value);
  return Boolean(normalized) && !IMAGE_ONLY_RE.test(normalized);
}

export function buildJournalOutline({
  content,
  title,
}: {
  content: string;
  title?: string | null;
}): JournalOutlineEntry[] {
  const entries: JournalOutlineEntry[] = [];
  const seenCounts = new Map<string, number>();
  const normalizedTitle = normalizeOutlineLabel(title ?? '');

  if (isMeaningfulOutlineLabel(normalizedTitle)) {
    const slug = buildOutlineSlug(normalizedTitle);
    entries.push({
      depth: 0,
      id: buildSectionId(slug, seenCounts),
      kind: 'title',
      label: normalizedTitle,
    });
  }

  const lines = String(content ?? '').replace(/\r\n/g, '\n').split('\n');
  let insideCodeFence = false;

  for (const line of lines) {
    if (FENCED_CODE_BLOCK_RE.test(line)) {
      insideCodeFence = !insideCodeFence;
      continue;
    }

    if (insideCodeFence) {
      continue;
    }

    const match = line.match(HEADING_RE);
    if (!match) {
      continue;
    }

    const depth = match[1]?.length === 1 ? 1 : 2;
    const label = normalizeOutlineLabel(match[2] ?? '');
    if (!isMeaningfulOutlineLabel(label)) {
      continue;
    }

    const slug = buildOutlineSlug(label);
    entries.push({
      depth,
      id: buildSectionId(slug, seenCounts),
      kind: 'heading',
      label,
    });
  }

  return entries;
}

export function buildJournalSectionDomId(
  surface: 'read' | 'write',
  sectionId: string,
) {
  return `journal-${surface}-section-${sectionId}`;
}
