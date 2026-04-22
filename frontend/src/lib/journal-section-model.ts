import type { JournalOutlineEntry } from '@/lib/journal-outline';

export type JournalSectionModel = JournalOutlineEntry & {
  characterCount: number;
  excerpt: string;
  isEmpty: boolean;
  isLight: boolean;
  paragraphCount: number;
};

const FENCED_CODE_BLOCK_RE = /^\s*```/;
const HEADING_RE = /^\s{0,3}(#{1,2})\s+(.+?)\s*#*\s*$/;
const IMAGE_MARKDOWN_RE = /!\[[^\]]*]\((?:attachment:[^)]+|https?:\/\/[^)]+)\)/g;
const LINK_MARKDOWN_RE = /\[([^\]]+)]\([^)]+\)/g;
const MARKDOWN_DECORATION_RE = /[`*_~>#-]/g;
const DEFAULT_TITLE_LABEL = '未命名的一頁';
const SYNTHETIC_TITLE_ID = 'journal-draft';
const LIGHT_SECTION_CHARACTER_THRESHOLD = 40;
const EXCERPT_CHARACTER_LIMIT = 96;

type HeadingLine = {
  entry: JournalOutlineEntry;
  lineIndex: number;
};

function normalizeLabel(value: string) {
  return value.replace(/\s+/g, ' ').trim();
}

function stripMarkdownForReading(value: string) {
  return value
    .replace(IMAGE_MARKDOWN_RE, ' ')
    .replace(LINK_MARKDOWN_RE, '$1')
    .replace(MARKDOWN_DECORATION_RE, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncateExcerpt(value: string) {
  if (value.length <= EXCERPT_CHARACTER_LIMIT) return value;
  return `${value.slice(0, EXCERPT_CHARACTER_LIMIT).trimEnd()}…`;
}

function buildReadableText(lines: string[]) {
  return stripMarkdownForReading(lines.join('\n'));
}

function countMeaningfulParagraphs(lines: string[]) {
  const paragraphs = lines
    .join('\n')
    .split(/\n{2,}/g)
    .map(stripMarkdownForReading)
    .filter(Boolean);
  return paragraphs.length;
}

function createSection({
  bodyLines,
  entry,
}: {
  bodyLines: string[];
  entry: JournalOutlineEntry;
}): JournalSectionModel {
  const readableText = buildReadableText(bodyLines);
  const characterCount = readableText.length;
  const isEmpty = characterCount === 0;

  return {
    ...entry,
    characterCount,
    excerpt: truncateExcerpt(readableText),
    isEmpty,
    isLight:
      entry.kind === 'heading' &&
      !isEmpty &&
      characterCount < LIGHT_SECTION_CHARACTER_THRESHOLD,
    paragraphCount: countMeaningfulParagraphs(bodyLines),
  };
}

function collectHeadingLines(content: string, headingEntries: JournalOutlineEntry[]) {
  const lines = String(content ?? '').replace(/\r\n/g, '\n').split('\n');
  const headingLines: HeadingLine[] = [];
  let insideCodeFence = false;
  let headingIndex = 0;

  lines.forEach((line, lineIndex) => {
    if (FENCED_CODE_BLOCK_RE.test(line)) {
      insideCodeFence = !insideCodeFence;
      return;
    }

    if (insideCodeFence) return;

    const match = line.match(HEADING_RE);
    if (!match) return;

    const nextEntry = headingEntries[headingIndex];
    const label = normalizeLabel(match[2] ?? '');
    if (!nextEntry || nextEntry.label !== label) return;

    headingLines.push({ entry: nextEntry, lineIndex });
    headingIndex += 1;
  });

  return {
    headingLines,
    lines,
  };
}

export function buildJournalSectionModel({
  content,
  outlineEntries,
  title,
}: {
  content: string;
  outlineEntries: JournalOutlineEntry[];
  title?: string | null;
}): JournalSectionModel[] {
  const normalizedTitle = normalizeLabel(title ?? '');
  const titleEntry = outlineEntries.find((entry) => entry.kind === 'title') ?? null;
  const headingEntries = outlineEntries.filter((entry) => entry.kind === 'heading');
  const { headingLines, lines } = collectHeadingLines(content, headingEntries);
  const sections: JournalSectionModel[] = [];
  const firstHeadingLine = headingLines[0]?.lineIndex ?? lines.length;
  const introLines = lines.slice(0, firstHeadingLine);
  const hasIntroText = Boolean(buildReadableText(introLines));

  if (titleEntry || hasIntroText || (!headingLines.length && !buildReadableText(lines))) {
    sections.push(
      createSection({
        bodyLines: introLines,
        entry: titleEntry ?? {
          depth: 0,
          id: SYNTHETIC_TITLE_ID,
          kind: 'title',
          label: normalizedTitle || DEFAULT_TITLE_LABEL,
        },
      }),
    );
  }

  headingLines.forEach((headingLine, index) => {
    const nextHeadingLine = headingLines[index + 1]?.lineIndex ?? lines.length;
    sections.push(
      createSection({
        bodyLines: lines.slice(headingLine.lineIndex + 1, nextHeadingLine),
        entry: headingLine.entry,
      }),
    );
  });

  return sections.length
    ? sections
    : [
        createSection({
          bodyLines: [],
          entry: {
            depth: 0,
            id: SYNTHETIC_TITLE_ID,
            kind: 'title',
            label: normalizedTitle || DEFAULT_TITLE_LABEL,
          },
        }),
      ];
}
