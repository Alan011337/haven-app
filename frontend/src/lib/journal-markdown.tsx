'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';
import type { JournalAttachmentPublic } from '@/types';
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

function buildMarkdownComponents(
  attachments: JournalAttachmentPublic[],
  variant: JournalMarkdownVariant,
): Components {
  const isPartner = variant === 'partner';
  const isRead = variant === 'read';
  const headingBase = 'font-art tracking-[-0.026em] text-card-foreground';
  const paragraphClass = isPartner
    ? 'leading-[2] text-[1rem] text-card-foreground'
    : isRead
      ? 'leading-[2.05] text-[1.08rem] text-card-foreground md:text-[1.1rem]'
      : 'leading-[2.02] text-[1.04rem] text-card-foreground md:text-[1.06rem]';
  const listClass = isPartner
    ? 'my-6 ml-5 space-y-2.5 text-[1rem] leading-[2] text-card-foreground marker:text-primary/50'
    : isRead
      ? 'my-7 ml-6 space-y-3 text-[1.08rem] leading-[2] text-card-foreground marker:text-primary/52 md:text-[1.1rem]'
      : 'my-6 ml-6 space-y-2.5 text-[1.04rem] leading-[2] text-card-foreground marker:text-primary/52 md:text-[1.06rem]';
  const figureClass = isPartner
    ? 'my-9 overflow-hidden rounded-[2rem] border border-[rgba(219,204,187,0.32)] bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(249,244,237,0.9))] shadow-soft'
    : isRead
      ? 'my-12 overflow-hidden rounded-[2.15rem] border border-[rgba(219,204,187,0.3)] bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(249,244,237,0.92))] shadow-soft md:mx-[-2.75rem]'
      : 'my-10 overflow-hidden rounded-[2rem] border border-[rgba(219,204,187,0.34)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(249,244,237,0.9))] shadow-soft md:mx-[-1.25rem]';

  return {
    h1: ({ children }) => (
      <h1
        className={cn(
          headingBase,
          isRead
            ? 'mt-2 text-[2.55rem] leading-[0.98] md:text-[3.25rem]'
            : 'mt-2 text-[2.3rem] leading-[1.02] md:text-[2.85rem]',
        )}
      >
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2
        className={cn(
          headingBase,
          isRead
            ? 'mt-12 text-[1.9rem] leading-[1.08] md:text-[2.2rem]'
            : 'mt-10 text-[1.76rem] leading-[1.1] md:text-[2rem]',
        )}
      >
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3
        className={cn(
          headingBase,
          isRead
            ? 'mt-10 text-[1.45rem] leading-[1.16] md:text-[1.62rem]'
            : 'mt-8 text-[1.36rem] leading-[1.2] md:text-[1.5rem]',
        )}
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
        <p className={cn(isRead ? 'my-7' : 'my-[1.35rem]', paragraphClass)}>
          {children}
        </p>
      );
    },
    ul: ({ children }) => <ul className={cn('list-disc', listClass)}>{children}</ul>,
    ol: ({ children }) => <ol className={cn('list-decimal', listClass)}>{children}</ol>,
    li: ({ children }) => <li className="pl-1">{children}</li>,
    blockquote: ({ children }) => (
      <blockquote className="my-10 rounded-[1.8rem] border border-primary/12 bg-primary/[0.045] px-6 py-5 font-art text-[1.16rem] leading-[1.88] text-card-foreground md:px-8 md:py-6">
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
      <hr className="my-12 border-none h-px bg-primary/[0.12]" />
    ),
    del: ({ children }) => (
      <del className="text-muted-foreground/70 decoration-muted-foreground/36">
        {children}
      </del>
    ),
    img: ({ alt, src }) => {
      const resolvedSrc = resolveAttachmentUrl(src, attachments);
      if (!resolvedSrc) {
        return (
          <div className="my-8 rounded-[1.7rem] border border-dashed border-border/80 bg-[linear-gradient(180deg,rgba(255,250,246,0.9),rgba(246,240,233,0.84))] px-5 py-8 text-sm leading-7 text-muted-foreground">
            這張圖片正在同步，Haven 會在附件準備好後把它補回這一頁。
          </div>
        );
      }

      return (
        <figure className={figureClass}>
          {/* eslint-disable-next-line @next/next/no-img-element -- Signed attachment URLs are dynamic and unsuitable for Next image optimization. */}
          <img
            alt={alt || 'journal image'}
            className="max-h-[42rem] w-full bg-[rgba(246,239,231,0.72)] object-contain"
            src={resolvedSrc}
          />
          {alt ? (
            <figcaption className="border-t border-white/58 px-5 py-3.5 text-sm leading-7 text-muted-foreground md:px-6">
              {alt}
            </figcaption>
          ) : null}
        </figure>
      );
    },
  };
}

export function JournalRichMarkdown({
  attachments,
  content,
  className,
  variant = 'studio',
}: {
  attachments: JournalAttachmentPublic[];
  className?: string;
  content: string;
  variant?: JournalMarkdownVariant;
}) {
  return (
    <div
      className={cn(
        'mx-auto w-full max-w-[42rem]',
        variant === 'read' ? 'max-w-[46rem]' : '',
        variant === 'partner' ? 'max-w-[43rem]' : '',
        className,
      )}
    >
      <ReactMarkdown
        components={buildMarkdownComponents(attachments, variant)}
        remarkPlugins={[remarkGfm]}
        urlTransform={transformJournalMarkdownUrl}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
