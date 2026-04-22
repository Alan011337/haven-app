'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';
import type { JournalAttachmentPublic } from '@/types';
import {
  buildJournalSectionDomId,
  type JournalOutlineEntry,
} from '@/lib/journal-outline';
import { JOURNAL_RHYTHM } from '@/features/journal/journal-document-rhythm';
import { JOURNAL_IMAGE_ALT_FALLBACK } from '@/features/journal/editor/journal-attachment-markdown';
import { resolveJournalFigureCaption } from '@/features/journal/journal-figure-caption';
import { cn } from '@/lib/utils';

export type JournalMarkdownVariant = 'partner' | 'read' | 'studio';

function resolveAttachmentUrl(
  rawTarget: string | Blob | undefined,
  attachments: JournalAttachmentPublic[],
): string | null {
  const target = typeof rawTarget === 'string' ? rawTarget.trim() : '';
  if (!target) return null;
  if (target.startsWith('attachment:')) {
    const attachmentId = target.replace('attachment:', '').trim();
    return attachments.find((attachment) => attachment.id === attachmentId)?.url ?? null;
  }
  if (target.startsWith('http://') || target.startsWith('https://')) {
    return target;
  }
  return null;
}

function transformJournalMarkdownUrl(rawUrl: string): string {
  const value = String(rawUrl ?? '').trim();
  if (!value) return '';
  if (
    value.startsWith('attachment:') ||
    value.startsWith('http://') ||
    value.startsWith('https://') ||
    value.startsWith('mailto:') ||
    value.startsWith('tel:')
  ) {
    return value;
  }
  return '';
}

const FENCED_CODE_BLOCK_RE = /^\s*```/;
const HEADING_RE = /^\s{0,3}(#{1,2})\s+(.+?)\s*#*\s*$/;

function normalizeHeadingLabel(value: string) {
  return value.replace(/\s+/g, ' ').trim();
}

function buildHeadingEntryByLine(
  content: string,
  headingEntries: JournalOutlineEntry[],
) {
  const entryByLine = new Map<number, JournalOutlineEntry>();
  const lines = String(content ?? '').replace(/\r\n/g, '\n').split('\n');
  let headingEntryIndex = 0;
  let insideCodeFence = false;

  lines.forEach((line, index) => {
    if (FENCED_CODE_BLOCK_RE.test(line)) {
      insideCodeFence = !insideCodeFence;
      return;
    }

    if (insideCodeFence) return;

    const match = line.match(HEADING_RE);
    if (!match) return;

    const entry = headingEntries[headingEntryIndex] ?? null;
    const label = normalizeHeadingLabel(match[2] ?? '');
    if (entry && entry.label === label) {
      entryByLine.set(index + 1, entry);
    }
    headingEntryIndex += 1;
  });

  return entryByLine;
}

function buildMarkdownComponents(
  attachments: JournalAttachmentPublic[],
  content: string,
  variant: JournalMarkdownVariant,
  headingEntries: JournalOutlineEntry[],
  surface: 'read' | 'write',
): Components {
  const isPartner = variant === 'partner';
  const isRead = variant === 'read';
  const headingBase = 'font-art tracking-[-0.026em] text-card-foreground';
  const paragraphClass = isPartner
    ? 'leading-[2] text-[1rem] text-card-foreground'
    : isRead
      ? JOURNAL_RHYTHM.paragraph
      : 'leading-[2.02] text-[1.04rem] text-card-foreground md:text-[1.06rem]';
  const listClass = isPartner
    ? 'my-6 ml-5 space-y-2.5 text-[1rem] leading-[2] text-card-foreground marker:text-primary/50'
    : 'my-6 ml-6 space-y-2.5 text-[1.04rem] leading-[2] text-card-foreground marker:text-primary/52 md:text-[1.06rem]';
  const figureClass = isPartner
    ? 'my-9 overflow-hidden rounded-[2rem] border border-[rgba(219,204,187,0.32)] bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(249,244,237,0.9))] shadow-soft'
    : isRead
      ? JOURNAL_RHYTHM.figure
      : 'my-10 overflow-hidden rounded-[2rem] border border-[rgba(219,204,187,0.34)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(249,244,237,0.9))] shadow-soft md:mx-[-1.25rem]';
  const headingEntryByLine = buildHeadingEntryByLine(content, headingEntries);

  const resolveHeadingEntry = (node: unknown) => {
    const line = (node as { position?: { start?: { line?: number } } } | null)?.position
      ?.start?.line;
    return typeof line === 'number' ? (headingEntryByLine.get(line) ?? null) : null;
  };

  return {
    h1: ({ children, node }) => {
      const entry = resolveHeadingEntry(node);
      return (
        <h1
          id={entry ? buildJournalSectionDomId(surface, entry.id) : undefined}
          data-journal-section-id={entry?.id}
          data-journal-surface={entry ? surface : undefined}
          data-testid={entry ? `journal-${surface}-section-${entry.id}` : undefined}
          className={
            isRead
              ? cn(JOURNAL_RHYTHM.h1, JOURNAL_RHYTHM.scrollMarginClass, 'mt-2')
              : cn(
                  headingBase,
                  'scroll-mt-32 md:scroll-mt-40',
                  'mt-2 text-[2.3rem] leading-[1.02] md:text-[2.85rem]',
                )
          }
        >
          {children}
        </h1>
      );
    },
    h2: ({ children, node }) => {
      const entry = resolveHeadingEntry(node);
      return (
        <h2
          id={entry ? buildJournalSectionDomId(surface, entry.id) : undefined}
          data-journal-section-id={entry?.id}
          data-journal-surface={entry ? surface : undefined}
          data-testid={entry ? `journal-${surface}-section-${entry.id}` : undefined}
          className={
            isRead
              ? cn(JOURNAL_RHYTHM.h2, JOURNAL_RHYTHM.scrollMarginClass)
              : cn(
                  headingBase,
                  'scroll-mt-32 md:scroll-mt-40',
                  'mt-10 text-[1.76rem] leading-[1.1] md:text-[2rem]',
                )
          }
        >
          {children}
        </h2>
      );
    },
    h3: ({ children }) => (
      <h3
        className={
          isRead
            ? cn(JOURNAL_RHYTHM.h3, JOURNAL_RHYTHM.scrollMarginClass)
            : cn(headingBase, 'mt-8 text-[1.36rem] leading-[1.2] md:text-[1.5rem]')
        }
      >
        {children}
      </h3>
    ),
    p: ({ children, node }) => {
      const childNodes = Array.isArray((node as { children?: Array<{ type?: string; tagName?: string; value?: string }> })?.children)
        ? (node as { children: Array<{ type?: string; tagName?: string; value?: string }> }).children
        : [];
      const meaningfulChildren = childNodes.filter((child) => {
        if (child.type !== 'text') return true;
        return Boolean(child.value?.trim());
      });

      if (
        meaningfulChildren.length === 1 &&
        meaningfulChildren[0]?.type === 'element' &&
        meaningfulChildren[0]?.tagName === 'img'
      ) {
        return <>{children}</>;
      }

      return (
        <p
          className={cn(
            isRead ? JOURNAL_RHYTHM.paragraphMargin : 'my-[1.35rem]',
            paragraphClass,
          )}
        >
          {children}
        </p>
      );
    },
    ul: ({ children }) => (
      <ul className={isRead ? JOURNAL_RHYTHM.ul : cn('list-disc', listClass)}>
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className={isRead ? JOURNAL_RHYTHM.ol : cn('list-decimal', listClass)}>
        {children}
      </ol>
    ),
    li: ({ children }) => (
      <li className={isRead ? JOURNAL_RHYTHM.listItem : 'pl-1'}>{children}</li>
    ),
    blockquote: ({ children }) => (
      <blockquote
        className={
          isRead
            ? JOURNAL_RHYTHM.quote
            : 'my-10 rounded-[1.8rem] border border-primary/12 bg-primary/[0.045] px-6 py-5 font-art text-[1.16rem] leading-[1.88] text-card-foreground md:px-8 md:py-6'
        }
      >
        {children}
      </blockquote>
    ),
    a: ({ children, href }) => {
      const resolvedHref = resolveAttachmentUrl(href, attachments) ?? href ?? '#';
      return (
        <a
          href={resolvedHref}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-primary underline decoration-primary/28 underline-offset-4 transition-colors duration-haven ease-haven hover:text-primary/80"
        >
          {children}
        </a>
      );
    },
    code: ({ children, className }) => {
      const inline = !className;
      if (inline) {
        return (
          <code className="rounded-md bg-[rgba(72,55,36,0.08)] px-1.5 py-0.5 font-mono text-[0.95em] text-card-foreground">
            {children}
          </code>
        );
      }

      return (
        <code className="font-mono text-sm leading-7 text-card-foreground">
          {children}
        </code>
      );
    },
    pre: ({ children }) => (
      <pre className="my-10 overflow-x-auto rounded-[1.7rem] border border-[rgba(219,204,187,0.34)] bg-[rgba(72,55,36,0.045)] px-5 py-5 text-sm leading-7 text-card-foreground shadow-glass-inset md:px-6 md:py-6">
        {children}
      </pre>
    ),
    hr: () => (
      <hr
        className={isRead ? JOURNAL_RHYTHM.hr : 'my-12 border-none h-px bg-primary/[0.12]'}
      />
    ),
    del: ({ children }) => (
      <del className="text-muted-foreground/70 decoration-muted-foreground/36">
        {children}
      </del>
    ),
    img: ({ alt, src }) => {
      const resolvedSrc = resolveAttachmentUrl(src, attachments);
      const rawTarget = typeof src === 'string' ? src.trim() : '';
      const attachmentId = rawTarget.startsWith('attachment:')
        ? rawTarget.replace('attachment:', '').trim() || null
        : null;
      const attachment = attachmentId
        ? attachments.find((item) => item.id === attachmentId)
        : null;
      // SR alt binds to the raw humanized alt (or the shared fallback
      // constant) independently of the visible-caption decision. The
      // quality gate below only suppresses the *visible* figcaption for
      // junk-like filenames; screen-reader users always get a descriptor.
      const rawAlt = (typeof alt === 'string' ? alt.trim() : '') || JOURNAL_IMAGE_ALT_FALLBACK;
      const caption = resolveJournalFigureCaption({
        caption: attachment?.caption,
        alt,
      });

      if (!resolvedSrc) {
        return (
          <div className="my-8 rounded-[1.7rem] border border-dashed border-border/80 bg-[linear-gradient(180deg,rgba(255,250,246,0.9),rgba(246,240,233,0.84))] px-5 py-8 text-sm leading-7 text-muted-foreground">
            這張圖片正在同步，Haven 會在附件準備好後把它補回這一頁。
          </div>
        );
      }

      return (
        <figure data-testid="journal-figure" className={figureClass}>
          {/* eslint-disable-next-line @next/next/no-img-element -- Signed attachment URLs are dynamic and unsuitable for Next image optimization. */}
          <img
            data-testid="journal-figure-image"
            alt={rawAlt}
            className={
              isRead
                ? JOURNAL_RHYTHM.figureImage
                : 'max-h-[42rem] w-full bg-[rgba(246,239,231,0.72)] object-contain'
            }
            src={resolvedSrc}
          />
          {caption.kind !== 'none' ? (
            <figcaption
              data-testid="journal-figure-caption"
              data-caption-kind={caption.kind}
              className={
                caption.kind === 'authored'
                  ? JOURNAL_RHYTHM.figcaptionAuthored
                  : JOURNAL_RHYTHM.figcaptionAlt
              }
            >
              {caption.text}
            </figcaption>
          ) : null}
        </figure>
      );
    },
  };
}

export function JournalRichMarkdown({
  attachments,
  headingEntries = [],
  content,
  className,
  surface = 'read',
  variant = 'studio',
}: {
  attachments: JournalAttachmentPublic[];
  className?: string;
  content: string;
  headingEntries?: JournalOutlineEntry[];
  surface?: 'read' | 'write';
  variant?: JournalMarkdownVariant;
}) {
  return (
    <div
      className={cn(
        'mx-auto w-full max-w-[42rem]',
        variant === 'read' ? JOURNAL_RHYTHM.containerMaxW : '',
        variant === 'partner' ? 'max-w-[43rem]' : '',
        className,
      )}
    >
      <ReactMarkdown
        components={buildMarkdownComponents(attachments, content, variant, headingEntries, surface)}
        remarkPlugins={[remarkGfm]}
        urlTransform={transformJournalMarkdownUrl}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
