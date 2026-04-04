import type {
  JournalUpsertPayload,
  UpdateJournalPayload,
} from '@/services/api-client';
import type { JournalVisibility } from '@/types';

interface JournalDraftFields {
  content: string;
  isDraft?: boolean;
  title: string;
  visibility?: JournalVisibility;
}

export function normalizeJournalDraftContent(content: string | null | undefined): string {
  return String(content ?? '').replace(/\r\n/g, '\n');
}

export function resolveJournalDraftContent({
  editorMarkdown,
  fallbackContent,
}: {
  editorMarkdown?: string | null;
  fallbackContent?: string | null;
}): string {
  const normalizedFallback = normalizeJournalDraftContent(fallbackContent);
  if (typeof editorMarkdown === 'string') {
    const normalizedEditor = normalizeJournalDraftContent(editorMarkdown);
    if (normalizedEditor.length > 0 || !hasJournalDraftContent(normalizedFallback)) {
      return normalizedEditor;
    }
  }
  return normalizedFallback;
}

export function hasJournalDraftContent(content: string | null | undefined): boolean {
  return normalizeJournalDraftContent(content).trim().length > 0;
}

export function hasJournalSubstantiveContent(content: string | null | undefined): boolean {
  return normalizeJournalDraftContent(content)
    .replace(/!\[[^\]]*]\(attachment:[^)]+\)\n*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
    .length > 0;
}

export function normalizeJournalDraftTitle(title: string | null | undefined): string | null {
  const normalized = String(title ?? '').trim();
  return normalized.length > 0 ? normalized : null;
}

export function buildCreateJournalPayload({
  content,
  isDraft = false,
  title,
  visibility,
}: JournalDraftFields): JournalUpsertPayload {
  return {
    content: normalizeJournalDraftContent(content),
    content_format: 'markdown',
    is_draft: isDraft,
    title: normalizeJournalDraftTitle(title),
    visibility: visibility ?? 'PRIVATE',
  };
}

export function buildUpdateJournalPayload({
  content,
  isDraft,
  requestAnalysis = false,
  title,
  visibility,
}: JournalDraftFields & { requestAnalysis?: boolean }): UpdateJournalPayload {
  return {
    content: normalizeJournalDraftContent(content),
    is_draft: isDraft,
    request_analysis: requestAnalysis,
    title: normalizeJournalDraftTitle(title),
    ...(visibility ? { visibility } : {}),
  };
}
