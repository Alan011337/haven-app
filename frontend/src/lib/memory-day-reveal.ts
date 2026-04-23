import type { TimelineItem } from '@/services/memoryService';

export type MemoryDayRevealArtifactKind = 'journal' | 'card' | 'appreciation' | 'photo';

export type MemoryDayRevealArtifact = {
  key: string;
  kind: MemoryDayRevealArtifactKind;
  typeLabel: string;
  contextLabel: string;
  title: string;
  excerpt: string;
  metaLabel?: string;
  actionLabel: string;
  canOpen: boolean;
};

export type MemoryDayRevealCounts = Record<MemoryDayRevealArtifactKind, number> & {
  total: number;
};

export type MemoryDayRevealModel = {
  date: string;
  mode: 'empty' | 'single' | 'multi';
  counts: MemoryDayRevealCounts;
  artifacts: MemoryDayRevealArtifact[];
  summaryLabel: string;
};

export function getMemoryDayRevealArtifactKey(item: TimelineItem): string {
  if (item.type === 'card') {
    return `card:${item.session_id}`;
  }
  return `${item.type}:${item.id}`;
}

function cleanText(value: string | null | undefined): string | null {
  const cleaned = value?.replace(/\s+/g, ' ').trim();
  return cleaned ? cleaned : null;
}

function truncateText(value: string | null | undefined, max = 96): string {
  const cleaned = cleanText(value);
  if (!cleaned) return '';
  if (cleaned.length <= max) return cleaned;
  return `${cleaned.slice(0, max - 1)}…`;
}

function formatDateLabel(value: string | null | undefined): string | undefined {
  const cleaned = cleanText(value);
  if (!cleaned) return undefined;
  const date = new Date(cleaned);
  if (Number.isNaN(date.getTime())) return cleaned;
  return date.toLocaleDateString('zh-TW', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function buildJournalArtifact(item: Extract<TimelineItem, { type: 'journal' }>): MemoryDayRevealArtifact {
  const attachmentCount = item.attachments?.length || item.attachment_count || 0;
  const firstCaption = item.attachments?.find((attachment) => cleanText(attachment.caption))?.caption;
  const mood = cleanText(item.mood_label);
  const excerpt =
    truncateText(item.content_preview, 108) ||
    truncateText(firstCaption, 108) ||
    (attachmentCount > 0 ? `這一天留下了 ${attachmentCount} 張圖片。` : '這一天有一則日記可以打開。');

  return {
    key: getMemoryDayRevealArtifactKey(item),
    kind: 'journal',
    typeLabel: 'Journal',
    contextLabel: item.is_own ? '我寫下' : '伴侶寫下',
    title: mood ? `${mood} 的一頁日記` : '一頁被留下的日記',
    excerpt,
    metaLabel: formatDateLabel(item.created_at),
    actionLabel: '打開完整日記',
    canOpen: true,
  };
}

function buildCardArtifact(item: Extract<TimelineItem, { type: 'card' }>): MemoryDayRevealArtifact {
  const hasMine = Boolean(cleanText(item.my_answer));
  const hasPartner = Boolean(cleanText(item.partner_answer));
  const participation =
    hasMine && hasPartner ? '雙方都回答了' : hasMine ? '我回答了' : hasPartner ? '伴侶回答了' : '等待完整回答';

  return {
    key: getMemoryDayRevealArtifactKey(item),
    kind: 'card',
    typeLabel: 'Card',
    contextLabel: participation,
    title: truncateText(item.card_title, 74) || '一張關係卡片',
    excerpt: truncateText(item.card_question, 108) || '這一天有一段卡片對話可以打開。',
    metaLabel: formatDateLabel(item.revealed_at),
    actionLabel: '打開完整卡片對話',
    canOpen: true,
  };
}

function buildAppreciationArtifact(
  item: Extract<TimelineItem, { type: 'appreciation' }>,
): MemoryDayRevealArtifact {
  return {
    key: getMemoryDayRevealArtifactKey(item),
    kind: 'appreciation',
    typeLabel: 'Appreciation',
    contextLabel: item.is_mine ? '我寫給伴侶' : '伴侶寫給我',
    title: item.is_mine ? '我寫下的一段感謝' : '伴侶留下的一段感謝',
    excerpt: truncateText(item.body_text, 108) || '這一天有一段感謝可以打開。',
    metaLabel: formatDateLabel(item.created_at),
    actionLabel: '打開完整感謝',
    canOpen: true,
  };
}

function buildPhotoArtifact(item: Extract<TimelineItem, { type: 'photo' }>): MemoryDayRevealArtifact {
  return {
    key: getMemoryDayRevealArtifactKey(item),
    kind: 'photo',
    typeLabel: 'Photo',
    contextLabel: item.is_own ? '我留下' : '伴侶留下',
    title: item.is_own ? '我留下的一張照片' : '伴侶留下的一張照片',
    excerpt: truncateText(item.caption, 108) || '這一天有一張照片片段可以定位。',
    metaLabel: formatDateLabel(item.created_at),
    actionLabel: '定位照片片段',
    canOpen: false,
  };
}

function buildArtifact(item: TimelineItem): MemoryDayRevealArtifact {
  if (item.type === 'journal') return buildJournalArtifact(item);
  if (item.type === 'card') return buildCardArtifact(item);
  if (item.type === 'appreciation') return buildAppreciationArtifact(item);
  return buildPhotoArtifact(item);
}

export function buildMemoryDayRevealModel({
  date,
  items,
}: {
  date: string | null | undefined;
  items: TimelineItem[];
}): MemoryDayRevealModel {
  const artifacts = (items ?? []).map(buildArtifact);
  const counts: MemoryDayRevealCounts = {
    total: artifacts.length,
    journal: artifacts.filter((artifact) => artifact.kind === 'journal').length,
    card: artifacts.filter((artifact) => artifact.kind === 'card').length,
    appreciation: artifacts.filter((artifact) => artifact.kind === 'appreciation').length,
    photo: artifacts.filter((artifact) => artifact.kind === 'photo').length,
  };
  const mode = counts.total === 0 ? 'empty' : counts.total === 1 ? 'single' : 'multi';

  return {
    date: cleanText(date) ?? '',
    mode,
    counts,
    artifacts,
    summaryLabel:
      counts.total === 0
        ? '這一天暫時沒有可展開的片段'
        : counts.total === 1
          ? '這一天有 1 個真實片段'
          : `這一天有 ${counts.total} 個真實片段`,
  };
}
