'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowLeft,
  Check,
  Eye,
  FilePenLine,
  Images,
  ImagePlus,
  LayoutPanelTop,
  LoaderCircle,
  PenLine,
  Share2,
  Type,
  X,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import type {
  Journal,
  JournalAttachmentPublic,
  JournalCurrentVisibility,
  JournalVisibility,
} from '@/types';
import {
  buildJournalTranslationStatusPresentation,
  type JournalTranslationStatusPresentation,
} from '@/app/journal/journal-translation-status';
import type { JournalOutlineEntry } from '@/lib/journal-outline';
import { JournalRichMarkdown } from '@/lib/journal-markdown';
import { buildJournalExcerpt, deriveJournalTitle } from '@/lib/journal-format';
import { formatTranslationReadyAt } from '@/lib/format';
import { cn } from '@/lib/utils';

export type JournalStudioMode = 'compare' | 'read' | 'write';
export type JournalSaveState = 'draft' | 'dirty' | 'error' | 'saved' | 'saving';

export function JournalShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,rgba(255,252,247,0.98),rgba(244,238,231,0.96))]">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-35" aria-hidden />
      <div
        className="pointer-events-none absolute -left-24 top-10 h-80 w-80 rounded-full bg-primary/10 blur-hero-orb"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-0 right-0 h-[28rem] w-[28rem] rounded-full bg-accent/8 blur-hero-orb"
        aria-hidden
      />

      <main className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1520px] flex-col gap-8 px-4 pb-24 pt-6 md:px-8 lg:px-10">
        {children}
      </main>
    </div>
  );
}

export function JournalBackLink({ href = '/' }: { href?: string }) {
  return (
    <Link
      href={href}
      className="inline-flex w-fit items-center gap-2 rounded-full border border-white/60 bg-white/82 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden />
      返回
    </Link>
  );
}

export function JournalStatePanel({
  eyebrow,
  title,
  description,
  actions,
  tone = 'neutral',
}: {
  actions?: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
  tone?: 'error' | 'neutral';
}) {
  return (
    <section
      className={cn(
        'rounded-[2.4rem] border p-8 shadow-lift',
        tone === 'error'
          ? 'border-destructive/18 bg-[linear-gradient(180deg,rgba(255,246,246,0.96),rgba(255,250,249,0.92))]'
          : 'border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(249,244,237,0.76))]',
      )}
    >
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/82">{eyebrow}</p>
          <h1 className="font-art text-[2rem] leading-tight text-card-foreground">{title}</h1>
          <p className="max-w-2xl text-sm leading-7 text-muted-foreground">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
    </section>
  );
}

export function JournalStudioHero({
  eyebrow,
  title,
  description,
  actions,
  aside,
}: {
  actions?: ReactNode;
  aside?: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <section className="grid gap-6 rounded-[2.8rem] border border-white/55 bg-[linear-gradient(145deg,rgba(255,255,255,0.86),rgba(248,243,236,0.8))] p-6 shadow-lift backdrop-blur-xl lg:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)] lg:p-8">
      <div className="space-y-5">
        <div className="space-y-2">
          <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/82">{eyebrow}</p>
          <h1 className="max-w-3xl font-art text-[2.5rem] leading-[1.02] text-card-foreground md:text-[3.2rem]">
            {title}
          </h1>
          <p className="max-w-2xl text-[15px] leading-8 text-muted-foreground">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
      <div className="rounded-[2.2rem] border border-white/58 bg-[linear-gradient(180deg,rgba(255,253,249,0.94),rgba(246,240,233,0.9))] p-5 shadow-glass-inset">
        {aside}
      </div>
    </section>
  );
}

export function JournalSavePill({
  lastSavedAt,
  message,
  state,
}: {
  lastSavedAt?: string | null;
  message: string;
  state: JournalSaveState;
}) {
  const iconMap = {
    draft: FilePenLine,
    dirty: PenLine,
    error: AlertCircle,
    saved: Check,
    saving: LoaderCircle,
  } satisfies Record<JournalSaveState, typeof FilePenLine>;
  const Icon = iconMap[state];
  const toneClass =
    state === 'error'
      ? 'border-destructive/16 bg-destructive/[0.05] text-destructive'
      : state === 'saved'
        ? 'border-primary/10 bg-primary/[0.05] text-card-foreground'
        : 'border-white/52 bg-white/72 text-card-foreground';

  return (
    <div className={cn('inline-flex max-w-full items-center gap-2 rounded-full border px-3.5 py-2 text-sm shadow-soft', toneClass)}>
      <div className="flex min-w-0 items-center gap-2">
        <span
          className={cn(
            'inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/45 bg-white/72',
            state === 'saving' ? 'animate-spin' : '',
          )}
          aria-hidden
        >
          <Icon className="h-3.5 w-3.5" />
        </span>
        <p className="truncate text-sm font-medium leading-6">{message}</p>
        {lastSavedAt && state === 'saved' ? (
          <span className="shrink-0 text-xs text-muted-foreground">
            {new Date(lastSavedAt).toLocaleString('zh-TW', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function JournalModeToggle({
  canCompare = true,
  mode,
  onChange,
}: {
  canCompare?: boolean;
  mode: JournalStudioMode;
  onChange: (mode: JournalStudioMode) => void;
}) {
  const options = [
    { icon: FilePenLine, label: '寫作', value: 'write' },
    { icon: Eye, label: '閱讀', value: 'read' },
    ...(canCompare ? [{ icon: LayoutPanelTop, label: '對照', value: 'compare' }] : []),
  ] as Array<{
    icon: typeof FilePenLine;
    label: string;
    value: JournalStudioMode;
  }>;

  return (
    <div className="inline-flex flex-wrap items-center gap-1 rounded-full border border-white/55 bg-white/76 p-1 shadow-soft">
      {options.map((option) => {
        const Icon = option.icon;
        const active = option.value === mode;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-haven ease-haven',
              active
                ? 'bg-[rgba(93,73,46,0.1)] text-card-foreground shadow-soft'
                : 'text-muted-foreground hover:bg-white/82 hover:text-card-foreground',
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function JournalVisibilitySwitch({
  onChange,
  value,
}: {
  onChange: (value: JournalCurrentVisibility) => void;
  value: JournalVisibility;
}) {
  const options: Array<{
    description: string;
    label: string;
    value: JournalCurrentVisibility;
  }> = [
    {
      value: 'PRIVATE',
      label: '私密保存',
      description: '這一頁只留在你的 Journal 書房，伴侶看不到。',
    },
    {
      value: 'PARTNER_ORIGINAL',
      label: '伴侶看原文',
      description: '伴侶會看到你寫下的原文，也會看到同一組圖片。',
    },
    {
      value: 'PARTNER_TRANSLATED_ONLY',
      label: '伴侶看整理後的版本',
      description: '伴侶只會看到 Haven 整理後的版本，不會看到原文或圖片。',
    },
  ];

  return (
    <div className="space-y-2.5">
      {options.map((option) => {
        const active = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'flex w-full items-start justify-between gap-4 rounded-[1.4rem] border px-4 py-4 text-left shadow-soft transition-all duration-haven ease-haven',
              active
                ? 'border-primary/18 bg-primary/[0.075]'
                : 'border-white/56 bg-white/70 hover:border-primary/14 hover:bg-white/82',
            )}
          >
            <span className="space-y-1.5">
              <span className="block text-sm font-medium text-card-foreground">{option.label}</span>
              <span className="block text-xs leading-6 text-muted-foreground">{option.description}</span>
            </span>
            <span
              className={cn(
                'mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                active
                  ? 'border-primary/25 bg-primary text-primary-foreground'
                  : 'border-border/80 bg-white/82',
              )}
              aria-hidden
            >
              {active ? <Check className="h-3 w-3" /> : null}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function getTranslationStatusToneClasses(
  tone: JournalTranslationStatusPresentation['tone'],
) {
  if (tone === 'progress') {
    return {
      card: 'border-primary/16 bg-primary/[0.06]',
      chip: 'border-primary/16 bg-primary/[0.08] text-card-foreground',
      eyebrow: 'text-primary/80',
      heading: 'text-card-foreground',
      icon: 'border-primary/12 bg-primary/[0.1] text-primary',
      message: 'text-muted-foreground',
    };
  }
  if (tone === 'success') {
    return {
      card: 'border-emerald-500/18 bg-[linear-gradient(180deg,rgba(236,253,245,0.92),rgba(246,252,248,0.96))] shadow-[0_18px_36px_-26px_rgba(16,185,129,0.45)]',
      chip: 'border-emerald-500/20 bg-emerald-500/[0.12] text-emerald-950',
      eyebrow: 'text-emerald-700/90',
      heading: 'text-emerald-950',
      icon: 'border-emerald-500/18 bg-emerald-500/[0.14] text-emerald-700',
      message: 'text-emerald-900/80',
    };
  }
  if (tone === 'error') {
    return {
      card: 'border-destructive/14 bg-destructive/[0.05]',
      chip: 'border-destructive/16 bg-destructive/[0.08] text-card-foreground',
      eyebrow: 'text-primary/80',
      heading: 'text-card-foreground',
      icon: 'border-destructive/14 bg-destructive/[0.1] text-destructive',
      message: 'text-muted-foreground',
    };
  }
  return {
    card: 'border-white/56 bg-white/72',
    chip: 'border-white/56 bg-white/76 text-card-foreground',
    eyebrow: 'text-primary/80',
    heading: 'text-card-foreground',
    icon: 'border-white/56 bg-white/82 text-card-foreground',
    message: 'text-muted-foreground',
  };
}

function JournalTranslationStatusIcon({
  presentation,
}: {
  presentation: JournalTranslationStatusPresentation;
}) {
  const iconClassName = cn(
    'h-3.5 w-3.5',
    presentation.state === 'pending' ? 'animate-spin' : '',
  );

  if (presentation.state === 'pending') {
    return <LoaderCircle className={iconClassName} aria-hidden />;
  }
  if (presentation.state === 'ready') {
    return <Check className={iconClassName} aria-hidden />;
  }
  if (presentation.state === 'failed') {
    return <AlertCircle className={iconClassName} aria-hidden />;
  }
  return <Share2 className={iconClassName} aria-hidden />;
}

export function JournalTranslationStatusChip({
  className,
  presentation,
}: {
  className?: string;
  presentation: JournalTranslationStatusPresentation;
}) {
  const toneClasses = getTranslationStatusToneClasses(presentation.tone);

  return (
    <span
      data-state={presentation.state}
      data-testid="journal-translation-status-chip"
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold shadow-soft',
        toneClasses.chip,
        className,
      )}
    >
      <JournalTranslationStatusIcon presentation={presentation} />
      {presentation.shortLabel}
    </span>
  );
}

export function JournalTranslationReadyAtLine({
  className,
  presentation,
}: {
  className?: string;
  presentation: JournalTranslationStatusPresentation;
}) {
  if (presentation.state !== 'ready' || !presentation.readyAt) return null;

  const toneClasses = getTranslationStatusToneClasses(presentation.tone);

  return (
    <span
      className={cn(
        'text-[10px] font-medium tabular-nums tracking-wide',
        toneClasses.eyebrow,
        className,
      )}
    >
      {formatTranslationReadyAt(presentation.readyAt)} 整理好
    </span>
  );
}

export function JournalTranslationStatusCard({
  presentation,
}: {
  presentation: JournalTranslationStatusPresentation;
}) {
  const toneClasses = getTranslationStatusToneClasses(presentation.tone);

  return (
    <div
      data-state={presentation.state}
      data-testid="journal-translation-status-card"
      className={cn('rounded-[1.35rem] border p-4 shadow-soft', toneClasses.card)}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border shadow-soft',
            toneClasses.icon,
          )}
          aria-hidden
        >
          <JournalTranslationStatusIcon presentation={presentation} />
        </span>
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className={cn('text-[0.68rem] uppercase tracking-[0.24em]', toneClasses.eyebrow)}>伴侶閱讀狀態</p>
            <JournalTranslationStatusChip presentation={presentation} />
          </div>
          <p className={cn('text-sm font-medium', toneClasses.heading)}>
            {presentation.readyAt
              ? `${formatTranslationReadyAt(presentation.readyAt)} ${presentation.label}`
              : presentation.label}
          </p>
          <p className={cn('text-sm leading-7', toneClasses.message)}>{presentation.message}</p>
        </div>
      </div>
    </div>
  );
}

export function JournalCanvasFrame({
  children,
  tone = 'writing',
}: {
  children: ReactNode;
  tone?: 'reading' | 'writing';
}) {
  return (
    <section
      className={cn(
        'overflow-hidden rounded-[2.25rem] border shadow-soft',
        tone === 'reading'
          ? 'border-[rgba(219,204,187,0.3)] bg-[linear-gradient(180deg,rgba(255,253,250,0.96),rgba(248,242,235,0.94))]'
          : 'border-[rgba(219,204,187,0.28)] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(252,248,242,0.96))]',
      )}
    >
      {children}
    </section>
  );
}

export function JournalDocumentMap({
  activeSectionId,
  entries,
  onSelect,
}: {
  activeSectionId: string | null;
  entries: JournalOutlineEntry[];
  onSelect: (entry: JournalOutlineEntry) => void;
}) {
  return (
    <section
      data-testid="journal-document-map"
      className="rounded-[1.9rem] border border-white/56 bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(248,243,236,0.78))] p-4 shadow-soft md:p-5"
    >
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-sm font-medium text-card-foreground">
          <LayoutPanelTop className="h-4 w-4 text-primary/80" aria-hidden />
          Document Map
        </div>
        <p className="text-sm leading-7 text-muted-foreground">
          讓這一頁的段落有可返回的結構，不用每次都重新找位置。
        </p>
      </div>

      <div className="mt-4 space-y-2">
        {entries.map((entry) => {
          const active = entry.id === activeSectionId;
          return (
            <button
              key={entry.id}
              type="button"
              data-testid={`journal-document-map-entry-${entry.id}`}
              aria-pressed={active}
              onClick={() => onSelect(entry)}
              className={cn(
                'flex w-full items-center justify-between gap-3 rounded-[1.2rem] border px-3.5 py-3 text-left text-sm transition-all duration-haven ease-haven',
                active
                  ? 'border-primary/18 bg-primary/[0.075] text-card-foreground shadow-soft'
                  : 'border-white/56 bg-white/72 text-card-foreground hover:bg-white/84',
              )}
            >
              <span
                className={cn(
                  'truncate',
                  entry.depth === 0 ? 'font-semibold' : '',
                  entry.depth === 1 ? 'pl-3' : '',
                  entry.depth === 2 ? 'pl-6 text-muted-foreground' : '',
                )}
              >
                {entry.label}
              </span>
              <span className="text-[10px] uppercase tracking-[0.24em] text-primary/70">
                {entry.depth === 0 ? 'Title' : entry.depth === 1 ? 'H1' : 'H2'}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export function JournalReadSurface({
  attachments,
  content,
  headingEntries = [],
  meta,
  note,
  surface = 'read',
  title,
  titleSectionId = null,
  variant = 'default',
}: {
  attachments: JournalAttachmentPublic[];
  content: string;
  headingEntries?: JournalOutlineEntry[];
  meta?: string;
  note?: string;
  surface?: 'read' | 'write';
  title: string;
  titleSectionId?: string | null;
  variant?: 'compare' | 'default';
}) {
  return (
    <JournalCanvasFrame tone="reading">
      <div
        className={cn(
          'px-6 pb-10 pt-8 md:px-12 md:pb-14 md:pt-12',
          variant === 'compare' ? 'md:px-10 md:pb-10 md:pt-10' : '',
        )}
      >
        {meta ? (
          <p className="text-sm leading-7 text-muted-foreground">{meta}</p>
        ) : null}
        <h2
          id={titleSectionId ? `journal-${surface}-section-${titleSectionId}` : undefined}
          data-journal-section-id={titleSectionId ?? undefined}
          data-journal-surface={titleSectionId ? surface : undefined}
          data-testid={titleSectionId ? `journal-${surface}-section-${titleSectionId}` : undefined}
          className="mt-2 scroll-mt-32 font-art text-[2.45rem] leading-[0.98] tracking-[-0.03em] text-card-foreground md:scroll-mt-40 md:text-[3.45rem]"
        >
          {title}
        </h2>
        {note ? (
          <p className="mt-4 max-w-2xl text-sm leading-7 text-muted-foreground">{note}</p>
        ) : null}
        {content.trim() ? (
          <JournalRichMarkdown
            attachments={attachments}
            content={content}
            headingEntries={headingEntries}
            surface={surface}
            variant="read"
            className={variant === 'compare' ? 'max-w-[42rem]' : ''}
          />
        ) : (
          <div className="rounded-[1.8rem] border border-dashed border-border/75 bg-white/58 px-5 py-8 text-sm leading-7 text-muted-foreground">
            當你先留下第一段，這裡才會慢慢長出真正的作品感。
          </div>
        )}
      </div>
    </JournalCanvasFrame>
  );
}

export function JournalAssetTray({
  attachments,
  insertedAttachmentIds = [],
  onInsert,
  onRemove,
  pending,
}: {
  attachments: JournalAttachmentPublic[];
  insertedAttachmentIds?: string[];
  onInsert: (attachment: JournalAttachmentPublic) => void;
  onRemove: (attachment: JournalAttachmentPublic) => void;
  pending?: boolean;
}) {
  const insertedSet = new Set(insertedAttachmentIds);

  return (
    <section className="rounded-[1.75rem] border border-white/52 bg-[linear-gradient(180deg,rgba(255,255,255,0.8),rgba(248,243,236,0.76))] p-4 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium text-card-foreground">
            <Images className="h-4 w-4 text-primary/80" aria-hidden />
            Image Shelf
          </div>
          <p className="text-xs leading-6 text-muted-foreground">
            {attachments.length
              ? `${attachments.length} 張圖片已放進這一頁的素材層。`
              : '這一頁還沒有圖像素材。'}
          </p>
        </div>
      </div>

      {attachments.length === 0 ? (
        <div className="mt-4 rounded-[1.4rem] border border-dashed border-border/75 bg-white/56 px-4 py-5 text-sm leading-7 text-muted-foreground">
          當你拖放、上傳或插入圖片，它們會先收進這個 shelf，再慢慢被放進正文節奏裡。
        </div>
      ) : (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
          {attachments.map((attachment) => (
            <article
              key={attachment.id}
              className="min-w-[220px] max-w-[220px] overflow-hidden rounded-[1.45rem] border border-white/58 bg-white/84 shadow-soft"
            >
              {attachment.url ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element -- Signed attachment URLs are dynamic and unsuitable for Next image optimization. */}
                  <img
                    src={attachment.url}
                    alt={attachment.file_name}
                    className="max-h-36 w-full object-contain"
                  />
                </>
              ) : (
                <div className="flex h-36 items-center justify-center text-muted-foreground">
                  <ImagePlus className="h-6 w-6" aria-hidden />
                </div>
              )}
              <div className="space-y-3 p-3.5">
                <div className="space-y-1">
                  <p className="truncate text-sm font-medium text-card-foreground">{attachment.file_name}</p>
                  <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>
                    {Math.max(1, Math.round(attachment.size_bytes / 1024))} KB
                    </span>
                    {insertedSet.has(attachment.id) ? (
                      <span className="rounded-full border border-primary/12 bg-primary/[0.08] px-2 py-0.5 text-[11px] text-primary">
                        已放入正文
                      </span>
                    ) : null}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending || insertedSet.has(attachment.id)}
                    onClick={() => onInsert(attachment)}
                  >
                    {insertedSet.has(attachment.id) ? '已在正文' : '插入正文'}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={pending}
                    onClick={() => onRemove(attachment)}
                  >
                    移除
                  </Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export function JournalLibraryCard({
  journal,
  active,
}: {
  active?: boolean;
  journal: Journal;
}) {
  const translationStatus = buildJournalTranslationStatusPresentation({
    currentVisibility: journal.visibility,
    hasCurrentJournalId: true,
    hasExplicitVisibilitySelection: false,
    isDraft: Boolean(journal.is_draft),
    partnerTranslationReadyAt: journal.partner_translation_ready_at ?? null,
    partnerTranslationStatus: journal.partner_translation_status,
    persistedVisibility: journal.visibility,
  });
  const visibilityLabel =
    journal.visibility === 'PRIVATE'
      ? '私密保存'
      : journal.visibility === 'PRIVATE_LOCAL'
        ? '完全私密（舊版）'
        : journal.visibility === 'PARTNER_ORIGINAL'
          ? '伴侶看原文'
          : journal.visibility === 'PARTNER_ANALYSIS_ONLY'
            ? '伴侶只看分析（舊版）'
            : '伴侶看整理後的版本';

  return (
    <Link
      href={`/journal/${journal.id}`}
      className={cn(
        'rounded-[1.9rem] border p-5 shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift',
        active ? 'border-primary/20 bg-primary/10' : 'border-white/60 bg-white/78',
      )}
    >
      <div className="space-y-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-primary/80">{visibilityLabel}</p>
            {translationStatus ? <JournalTranslationStatusChip presentation={translationStatus} /> : null}
          </div>
          {translationStatus ? <JournalTranslationReadyAtLine presentation={translationStatus} /> : null}
          <h3 className="font-art text-[1.45rem] leading-tight text-card-foreground">
            {deriveJournalTitle(journal)}
          </h3>
        </div>
        <p className="line-clamp-5 whitespace-pre-wrap text-sm leading-7 text-muted-foreground">
          {buildJournalExcerpt(journal.content)}
        </p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {new Date(journal.created_at).toLocaleDateString('zh-TW', {
              month: 'numeric',
              day: 'numeric',
            })}
          </span>
          <span>{journal.attachments?.length ?? 0} 張圖</span>
        </div>
      </div>
    </Link>
  );
}

export function JournalMobileDock({
  imageCount = 0,
  onFormat,
  onImages,
  onVisibility,
}: {
  imageCount?: number;
  onFormat: () => void;
  onImages: () => void;
  onVisibility: () => void;
}) {
  return (
    <div className="fixed inset-x-0 bottom-4 z-[110] px-4 md:hidden">
      <div className="mx-auto grid max-w-[360px] grid-cols-3 items-center rounded-[1.6rem] border border-white/58 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(247,241,234,0.94))] px-2 py-2 shadow-lift backdrop-blur-xl">
        <button
          type="button"
          onClick={onFormat}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-[1.1rem] text-sm font-medium text-card-foreground transition hover:bg-white/82"
          aria-label="打開格式面板"
        >
          <Type className="h-4 w-4" aria-hidden />
          格式
        </button>
        <button
          type="button"
          onClick={onImages}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-[1.1rem] text-sm font-medium text-card-foreground transition hover:bg-white/82"
          aria-label="打開圖片素材層"
        >
          <ImagePlus className="h-4 w-4" aria-hidden />
          圖片
          {imageCount ? (
            <span className="rounded-full bg-primary/[0.08] px-1.5 py-0.5 text-[11px] text-primary">
              {imageCount}
            </span>
          ) : null}
        </button>
        <button
          type="button"
          onClick={onVisibility}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-[1.1rem] text-sm font-medium text-card-foreground transition hover:bg-white/82"
          aria-label="打開分享設定"
        >
          <Share2 className="h-4 w-4" aria-hidden />
          分享
        </button>
      </div>
    </div>
  );
}

export function JournalMobileSheet({
  children,
  description,
  onClose,
  open,
  title,
}: {
  children: ReactNode;
  description?: string;
  onClose: () => void;
  open: boolean;
  title: string;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[130] md:hidden" role="dialog" aria-modal="true" aria-label={title}>
      <button
        type="button"
        className="absolute inset-0 bg-[rgba(35,28,22,0.28)] backdrop-blur-[2px]"
        onClick={onClose}
        aria-label="關閉面板"
      />
      <div className="absolute inset-x-0 bottom-0 rounded-t-[2rem] border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(246,240,233,0.96))] px-5 pb-8 pt-5 shadow-modal">
        <div className="mx-auto mb-4 h-1.5 w-14 rounded-full bg-border/70" aria-hidden />
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h2 className="font-art text-[1.5rem] leading-tight text-card-foreground">{title}</h2>
            {description ? (
              <p className="max-w-sm text-sm leading-7 text-muted-foreground">{description}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/60 bg-white/78 text-card-foreground shadow-soft"
            aria-label="關閉"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div className="mt-5 max-h-[68vh] overflow-y-auto pb-4">{children}</div>
      </div>
    </div>
  );
}
