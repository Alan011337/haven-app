export function deriveJournalAttachmentAlt(fileName: string): string {
  return (
    fileName
      .replace(/\.[^.]+$/, '')
      .replace(/[-_]+/g, ' ')
      .trim() || 'journal image'
  );
}

export function insertAttachmentMarkdown(
  content: string,
  {
    alt,
    attachmentId,
  }: {
    alt: string;
    attachmentId: string;
  },
): string {
  const block = `![${alt}](attachment:${attachmentId})`;
  const normalized = String(content ?? '').replace(/\r\n/g, '\n').trimEnd();
  if (!normalized.trim()) {
    return block;
  }
  return `${normalized}\n\n${block}`;
}

export function stripAttachmentMarkdown(content: string, attachmentId: string): string {
  return content
    .replace(
      new RegExp(`!\\[[^\\]]*\\]\\(attachment:${attachmentId}\\)\\n*`, 'g'),
      '',
    )
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function stripAllAttachmentMarkdown(content: string | null | undefined): string {
  return String(content ?? '')
    .replace(/!\[[^\]]*]\(attachment:[^)]+\)\n*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findAttachmentAlt(content: string, attachmentId: string): string | null {
  const match = String(content ?? '').match(
    new RegExp(`!\\[([^\\]]*)\\]\\(attachment:${escapeRegExp(attachmentId)}\\)`),
  );
  return match?.[1]?.trim() || null;
}

export function preserveAttachmentMarkdown(
  nextContent: string,
  {
    attachments,
    previousContent,
  }: {
    attachments: Array<{ file_name: string; id: string }>;
    previousContent: string;
  },
): string {
  let mergedContent = String(nextContent ?? '').replace(/\r\n/g, '\n').trim();

  for (const attachment of attachments) {
    const token = `attachment:${attachment.id}`;
    if (mergedContent.includes(token)) continue;

    mergedContent = insertAttachmentMarkdown(mergedContent, {
      alt:
        findAttachmentAlt(previousContent, attachment.id) ??
        deriveJournalAttachmentAlt(attachment.file_name),
      attachmentId: attachment.id,
    });
  }

  return mergedContent;
}

export function findInsertedAttachmentIds(content: string): string[] {
  return Array.from(
    new Set(
      Array.from(content.matchAll(/!\[[^\]]*]\(attachment:([^)]+)\)/g)).map(
        (match) => match[1]?.trim() ?? '',
      ),
    ),
  ).filter(Boolean);
}
