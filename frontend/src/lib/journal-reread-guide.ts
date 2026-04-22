import type { JournalSectionModel } from '@/lib/journal-section-model';

export type JournalRereadPathSlot = 'closing' | 'middle' | 'opener';

export type JournalRereadPathItem = {
  cue: string;
  excerpt: string;
  label: string;
  sectionId: string;
  sectionLabel: string;
  slot: JournalRereadPathSlot;
};

export type JournalRereadGuideModel = {
  emptyOrShort: boolean;
  imageCount: number;
  lightSectionCount: number;
  paragraphCount: number;
  pathItems: JournalRereadPathItem[];
  sectionCount: number;
  summary: string;
};

const DEFAULT_EXCERPT = '從這裡回到當時，先讓自己重新靠近這一段。';

function countContentParagraphs(content: string) {
  return String(content ?? '')
    .split(/\n{2,}/g)
    .map((paragraph) => paragraph.replace(/\s+/g, ' ').trim())
    .filter(Boolean).length;
}

function buildPathItem({
  section,
  slot,
}: {
  section: JournalSectionModel;
  slot: JournalRereadPathSlot;
}): JournalRereadPathItem {
  const labels = {
    closing: '收束',
    middle: '深入',
    opener: '入口',
  } satisfies Record<JournalRereadPathSlot, string>;
  const cues = {
    closing: '把這裡當作這一頁最後想留下的地方。',
    middle: '在這裡慢下來，看見正文真正展開的部分。',
    opener: '從這裡回到當時，先重新進入這一頁。',
  } satisfies Record<JournalRereadPathSlot, string>;

  return {
    cue: cues[slot],
    excerpt: section.excerpt || DEFAULT_EXCERPT,
    label: labels[slot],
    sectionId: section.id,
    sectionLabel: section.label,
    slot,
  };
}

function pushUniquePathItem(
  items: JournalRereadPathItem[],
  slot: JournalRereadPathSlot,
  section: JournalSectionModel | null | undefined,
) {
  if (!section || items.some((item) => item.sectionId === section.id)) return;
  items.push(buildPathItem({ section, slot }));
}

export function buildJournalRereadGuide({
  content,
  imageCount,
  sections,
}: {
  content: string;
  imageCount: number;
  sections: JournalSectionModel[];
}): JournalRereadGuideModel {
  const safeSections = Array.isArray(sections) ? sections : [];
  const meaningfulSections = safeSections.filter((section) => !section.isEmpty);
  const anchorSections = meaningfulSections.length ? meaningfulSections : safeSections;
  const sectionCount = safeSections.length;
  const paragraphCount =
    safeSections.reduce((total, section) => total + section.paragraphCount, 0) ||
    countContentParagraphs(content);
  const lightSectionCount = safeSections.filter((section) => section.isEmpty || section.isLight).length;
  const normalizedImageCount = Math.max(0, imageCount);
  const emptyOrShort = paragraphCount < 2 || anchorSections.length < 2;
  const pathItems: JournalRereadPathItem[] = [];
  const opener = anchorSections[0] ?? null;
  const closing =
    anchorSections.length > 1 ? (anchorSections[anchorSections.length - 1] ?? null) : null;
  const middleCandidates = anchorSections.slice(1, -1);
  const middle =
    middleCandidates.sort((left, right) => right.characterCount - left.characterCount)[0] ??
    (anchorSections.length > 2 ? anchorSections[1] : null);

  pushUniquePathItem(pathItems, 'opener', opener);
  pushUniquePathItem(pathItems, 'middle', middle);
  pushUniquePathItem(pathItems, 'closing', closing);

  const sectionLabel = sectionCount > 1 ? `${sectionCount} 個段落` : '一個入口';
  const paragraphLabel = paragraphCount > 0 ? `${paragraphCount} 段正文` : '還沒有正文';
  const imageLabel = normalizedImageCount > 0 ? `、${normalizedImageCount} 張圖片` : '';
  const lightLabel = lightSectionCount > 0 ? `，其中 ${lightSectionCount} 段還很輕` : '';

  return {
    emptyOrShort,
    imageCount: normalizedImageCount,
    lightSectionCount,
    paragraphCount,
    pathItems,
    sectionCount,
    summary: `${sectionLabel}、${paragraphLabel}${imageLabel}${lightLabel}。`,
  };
}
