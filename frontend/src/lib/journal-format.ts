interface JournalTitleSource {
  content: string;
  title?: string | null;
}

export function deriveJournalTitle(source: JournalTitleSource): string {
  const explicitTitle = source.title?.trim();
  if (explicitTitle) return explicitTitle;
  const firstLine = source.content.split('\n').find((line) => line.trim());
  return firstLine?.trim().replace(/^#{1,6}\s+/, '').slice(0, 42) || '未命名手記';
}

const MARKDOWN_IMAGE_RE = /!\[[^\]]*]\((?:attachment:[^)]+|https?:\/\/[^)]+)\)/g;
const FIRST_IMAGE_URL_RE = /!\[[^\]]*]\(((?:attachment:[^)]+|https?:\/\/[^)]+))\)/;

/**
 * Extract the first image URL from journal markdown content.
 * Returns `null` if no image is found.
 */
export function extractFirstJournalImage(content: string): string | null {
  const match = content.match(FIRST_IMAGE_URL_RE);
  return match?.[1] ?? null;
}

export function buildJournalExcerpt(content: string): string {
  const cleaned = content
    .replace(MARKDOWN_IMAGE_RE, '')
    .replace(/```[\s\S]*?```/g, (block) =>
      block
        .replace(/^```[a-zA-Z0-9_-]*\n?/, '')
        .replace(/\n?```$/, '')
        .trim(),
    )
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return cleaned || '這一頁還在安靜長出第一段內容。';
}
