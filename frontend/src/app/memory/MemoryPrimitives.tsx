'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Gift,
  Heart,
  Image as ImageIcon,
  LayoutGrid,
  List,
  MessageCircle,
  Sparkles,
} from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import { cn } from '@/lib/utils';
import type { CalendarDay, TimelineAttachmentMeta } from '@/services/memoryService';

export type MemoryCardKind = 'capsule' | 'journal' | 'card' | 'appreciation' | 'photo' | 'empty';
type MemoryPanelTone = 'default' | 'quiet' | 'error';

const panelToneClasses: Record<MemoryPanelTone, string> = {
  default: 'border-white/54 bg-white/84',
  quiet: 'border-primary/12 bg-white/76',
  error:
    'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,251,249,0.96),rgba(248,240,236,0.94))]',
};

const cardToneClasses: Record<MemoryCardKind, string> = {
  capsule:
    'border-white/54 bg-[linear-gradient(165deg,rgba(255,252,248,0.96),rgba(244,236,225,0.92))]',
  journal:
    'border-white/52 bg-[linear-gradient(165deg,rgba(255,253,249,0.95),rgba(242,235,226,0.92))]',
  card:
    'border-white/52 bg-[linear-gradient(165deg,rgba(255,251,248,0.95),rgba(243,233,226,0.92))]',
  appreciation:
    'border-white/52 bg-[linear-gradient(165deg,rgba(255,249,250,0.95),rgba(244,230,234,0.92))]',
  photo:
    'border-white/52 bg-[linear-gradient(165deg,rgba(253,250,246,0.96),rgba(239,232,224,0.92))]',
  empty:
    'border-white/50 bg-[linear-gradient(165deg,rgba(254,252,249,0.95),rgba(244,238,231,0.92))]',
};

function MemoryKindIcon({ kind }: { kind: MemoryCardKind }) {
  const iconClass = 'h-4 w-4';
  if (kind === 'capsule') return <Gift className={iconClass} aria-hidden />;
  if (kind === 'journal') return <BookOpen className={iconClass} aria-hidden />;
  if (kind === 'card') return <MessageCircle className={iconClass} aria-hidden />;
  if (kind === 'appreciation') return <Heart className={iconClass} aria-hidden />;
  if (kind === 'photo') return <ImageIcon className={iconClass} aria-hidden />;
  return <Sparkles className={iconClass} aria-hidden />;
}

function MemoryPhotoStrip({ attachments }: { attachments: TimelineAttachmentMeta[] }) {
  const withUrls = attachments.filter((a) => a.url);
  const withCaptionsOnly = withUrls.length === 0 ? attachments.filter((a) => a.caption?.trim()) : [];

  if (withUrls.length > 0) {
    return (
      <div className="flex gap-2.5 overflow-x-auto py-1" role="list" aria-label="照片">
        {withUrls.map((a) => (
          <div key={a.id} className="shrink-0" role="listitem">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={a.url!}
              alt={a.caption || a.file_name}
              className="h-24 w-24 rounded-[1.2rem] border border-white/56 object-cover shadow-soft"
              loading="lazy"
            />
            {a.caption ? (
              <p className="mt-1 max-w-[6rem] truncate text-caption text-muted-foreground">{a.caption}</p>
            ) : null}
          </div>
        ))}
      </div>
    );
  }

  if (withCaptionsOnly.length > 0) {
    return (
      <div className="space-y-1" role="list" aria-label="照片描述">
        {withCaptionsOnly.map((a) => (
          <p key={a.id} className="text-body-muted text-muted-foreground" role="listitem">
            📷 {a.caption}
          </p>
        ))}
      </div>
    );
  }

  return null;
}

interface MemoryShellProps {
  children: ReactNode;
}

export function MemoryShell({ children }: MemoryShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.16),transparent_26%),radial-gradient(circle_at_88%_10%,rgba(231,236,232,0.48),transparent_28%),linear-gradient(180deg,#fcfaf6_0%,#f5efe7_48%,#efe7dd_100%)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-28" aria-hidden />
      <div className="pointer-events-none absolute -left-12 top-16 h-72 w-72 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />

      <div className="relative z-10 mx-auto max-w-[1540px] space-y-[clamp(1.5rem,3vw,2.75rem)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-white/54 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
              aria-label="返回首頁"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              回首頁
            </Link>
            <Link
              href="/love-map#story"
              className="inline-flex items-center gap-2 rounded-full border border-white/52 bg-white/64 px-4 py-2.5 text-sm font-medium text-card-foreground/88 shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-white/74 hover:text-card-foreground hover:shadow-lift focus-ring-premium"
            >
              Relationship System 故事摘要
              <Sparkles className="h-4 w-4" aria-hidden />
            </Link>
          </div>

          <Badge
            variant="metadata"
            size="md"
            className="border-white/50 bg-white/72 text-primary/78 shadow-soft"
          >
            Memory
          </Badge>
        </div>

        {children}
      </div>
    </div>
  );
}

interface MemoryCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  highlights?: ReactNode;
  featured: ReactNode;
  aside: ReactNode;
}

export function MemoryCover({
  eyebrow,
  title,
  description,
  pulse,
  highlights,
  featured,
  aside,
}: MemoryCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.95),rgba(246,239,230,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.74),transparent_36%),radial-gradient(circle_at_84%_12%,rgba(255,255,255,0.34),transparent_22%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute right-[-4rem] top-[-2rem] h-72 w-72 rounded-full bg-primary/10 blur-hero-orb"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-[-3rem] left-[-1rem] h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm"
        aria-hidden
      />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
        <div className="space-y-6">
          <div className="space-y-4">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h1 className="max-w-[56rem] type-h1 text-card-foreground">{title}</h1>
              <p className="max-w-[46rem] type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.9rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" aria-hidden />
            </span>
            <p className="type-body-muted text-card-foreground">{pulse}</p>
          </div>

          {highlights}
        </div>

        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
          <div>{featured}</div>
          <div className="space-y-4">{aside}</div>
        </div>
      </div>
    </section>
  );
}

interface MemoryOverviewCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}

export function MemoryOverviewCard({
  eyebrow,
  title,
  description,
  children,
}: MemoryOverviewCardProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.3rem] border-white/52 bg-white/80 p-5 md:p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        {children}
      </div>
    </GlassCard>
  );
}

type MemoryModeItem = {
  key: 'feed' | 'calendar';
  label: string;
  description: string;
  meta: string;
  active: boolean;
  onClick: () => void;
};

interface MemoryModeRailProps {
  items: MemoryModeItem[];
}

export function MemoryModeRail({ items }: MemoryModeRailProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.45rem] border-white/52 bg-white/82 p-5 md:p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">Memory Modes</p>
          <h2 className="type-h3 text-card-foreground">選一種方式，重新走回你們留下的生活。</h2>
          <p className="type-body-muted text-muted-foreground">
            一種沿著時間往回看，一種從月份與日子重走。兩種都不是掃描，而是慢慢回來。
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={item.onClick}
              aria-pressed={item.active}
              className={cn(
                'group rounded-[1.85rem] border px-4 py-4 text-left shadow-soft backdrop-blur-md transition-all duration-haven ease-haven focus-ring-premium',
                item.active
                  ? 'border-primary/18 bg-primary/10 text-card-foreground hover:-translate-y-0.5 hover:shadow-lift'
                  : 'border-white/50 bg-white/70 text-card-foreground hover:-translate-y-0.5 hover:border-primary/14 hover:shadow-lift',
              )}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/78 text-primary shadow-soft">
                      {item.key === 'feed' ? (
                        <List className="h-4 w-4" aria-hidden />
                      ) : (
                        <LayoutGrid className="h-4 w-4" aria-hidden />
                      )}
                    </span>
                    <span className="type-section-title">{item.label}</span>
                  </span>
                  <Badge
                    variant={item.active ? 'status' : 'metadata'}
                    size="sm"
                    className={item.active ? '' : 'border-white/54 bg-white/70'}
                  >
                    {item.active ? '目前展開' : '切換'}
                  </Badge>
                </div>
                <p className="type-body-muted text-muted-foreground">{item.description}</p>
                <p className="type-caption text-card-foreground/76">{item.meta}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

interface MemoryFeaturedMemoryCardProps {
  kind: MemoryCardKind;
  eyebrow: string;
  title: string;
  description: string;
  dateLabel?: string;
  badges?: string[];
  detailLines?: string[];
  support?: string;
  attachments?: TimelineAttachmentMeta[];
  focused?: boolean;
}

export function MemoryFeaturedMemoryCard({
  kind,
  eyebrow,
  title,
  description,
  dateLabel,
  badges = [],
  detailLines = [],
  support,
  attachments,
  focused,
}: MemoryFeaturedMemoryCardProps) {
  const usesMatteFrame = kind === 'photo';

  return (
    <GlassCard
      data-memory-kind={kind}
      data-memory-focused={focused ? 'true' : undefined}
      className={cn(
        'overflow-hidden rounded-[2.95rem] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10',
        cardToneClasses[kind],
        focused && 'ring-2 ring-primary/30 ring-offset-2 ring-offset-white/60',
      )}
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-2.5">
          <Badge variant="warning" size="sm">
            {eyebrow}
          </Badge>
          {dateLabel ? (
            <Badge variant="metadata" size="sm" className="border-white/56 bg-white/72">
              {dateLabel}
            </Badge>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <span className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary shadow-soft">
              <MemoryKindIcon kind={kind} />
            </span>
            <div
              className={cn(
                'space-y-3',
                usesMatteFrame && 'rounded-[2.2rem] border border-white/58 bg-white/62 px-5 py-5 shadow-soft',
              )}
            >
              <h2 className="type-h2 text-card-foreground">{title}</h2>
              <p className="type-body-muted leading-7 text-card-foreground/88">{description}</p>
            </div>
          </div>

          {detailLines.length > 0 ? (
            <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
              <div className="space-y-2.5">
                {detailLines.map((line) => (
                  <p key={line} className="type-body-muted text-card-foreground">{line}</p>
                ))}
              </div>
            </div>
          ) : null}

          {attachments && attachments.length > 0 ? (
            <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
              <MemoryPhotoStrip attachments={attachments} />
            </div>
          ) : null}

          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {badges.map((badge, i) => (
                <Badge
                  key={badge}
                  variant={i === 0 ? 'default' : 'metadata'}
                  size="sm"
                  className={i === 0 ? '' : 'border-white/56 bg-white/72 text-card-foreground'}
                >
                  {badge}
                </Badge>
              ))}
            </div>
          ) : null}

          {support ? (
            <div className="rounded-[1.8rem] border border-white/56 bg-white/70 px-4 py-4 shadow-soft">
              <p className="type-body-muted text-card-foreground">{support}</p>
            </div>
          ) : null}
        </div>
      </div>
    </GlassCard>
  );
}

interface MemoryCompanionMemoryCardProps {
  kind: MemoryCardKind;
  eyebrow: string;
  title: string;
  description: string;
  dateLabel?: string;
  badges?: string[];
  detailLines?: string[];
  support?: string;
  attachments?: TimelineAttachmentMeta[];
}

export function MemoryCompanionMemoryCard({
  kind,
  eyebrow,
  title,
  description,
  dateLabel,
  badges = [],
  detailLines = [],
  support,
  attachments,
}: MemoryCompanionMemoryCardProps) {
  const usesMatteFrame = kind === 'photo';

  return (
    <GlassCard
      className={cn(
        'overflow-hidden rounded-[2.3rem] p-5 shadow-soft backdrop-blur-xl md:p-6',
        cardToneClasses[kind],
      )}
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/76 text-primary shadow-soft">
            <MemoryKindIcon kind={kind} />
          </span>
          <div className="space-y-1">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            {dateLabel ? <p className="type-caption text-muted-foreground">{dateLabel}</p> : null}
          </div>
        </div>

        <div
          className={cn(
            'space-y-3',
            usesMatteFrame && 'rounded-[1.75rem] border border-white/56 bg-white/64 px-4 py-4 shadow-soft',
          )}
        >
          <h3 className="type-h3 text-card-foreground">{title}</h3>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>

        {detailLines.length > 0 ? (
          <div className="grid gap-2">
            {detailLines.slice(0, 2).map((line) => (
              <p key={line} className="type-caption text-card-foreground/78">
                {line}
              </p>
            ))}
          </div>
        ) : null}

        {attachments && attachments.length > 0 ? (
          <MemoryPhotoStrip attachments={attachments} />
        ) : null}

        {badges.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {badges.slice(0, 2).map((badge, i) => (
              <Badge
                key={badge}
                variant={i === 0 ? 'default' : 'outline'}
                size="sm"
                className={i === 0 ? '' : 'border-white/56 bg-white/68'}
              >
                {badge}
              </Badge>
            ))}
          </div>
        ) : null}

        {support ? (
          <p className="type-caption leading-6 text-card-foreground/76">{support}</p>
        ) : null}
      </div>
    </GlassCard>
  );
}

interface MemoryStreamMemoryCardProps {
  kind: MemoryCardKind;
  eyebrow: string;
  title: string;
  description: string;
  dateLabel?: string;
  badges?: string[];
  detailLines?: string[];
  support?: string;
  attachments?: TimelineAttachmentMeta[];
  focused?: boolean;
}

export function MemoryStreamMemoryCard({
  kind,
  eyebrow,
  title,
  description,
  dateLabel,
  badges = [],
  detailLines = [],
  support,
  attachments,
  focused,
}: MemoryStreamMemoryCardProps) {
  const usesMatteFrame = kind === 'photo';

  return (
    <GlassCard
      data-memory-kind={kind}
      data-memory-focused={focused ? 'true' : undefined}
      className={cn(
        'overflow-hidden rounded-[2rem] p-5 shadow-soft backdrop-blur-md md:p-6',
        cardToneClasses[kind],
        focused && 'ring-2 ring-primary/30 ring-offset-2 ring-offset-white/60',
      )}
    >
      <div className="grid gap-4 md:grid-cols-[auto_minmax(0,1fr)] md:items-start">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/78 text-primary shadow-soft">
          <MemoryKindIcon kind={kind} />
        </span>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="space-y-1">
              <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
              <h3 className="type-section-title text-card-foreground">{title}</h3>
            </div>
            {dateLabel ? <p className="type-caption text-muted-foreground">{dateLabel}</p> : null}
          </div>

          <div
            className={cn(
              usesMatteFrame && 'rounded-[1.45rem] border border-white/56 bg-white/62 px-4 py-3 shadow-soft',
            )}
          >
            <p className="type-caption leading-6 text-muted-foreground">{description}</p>
          </div>

          {detailLines.length > 0 ? (
            <div className="grid gap-1.5">
              {detailLines.slice(0, 2).map((line) => (
                <p key={line} className="type-caption text-card-foreground/78">
                  {line}
                </p>
              ))}
            </div>
          ) : null}

          {attachments && attachments.length > 0 ? (
            <MemoryPhotoStrip attachments={attachments} />
          ) : null}

          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {badges.map((badge, i) => (
                <Badge
                  key={badge}
                  variant={i === 0 ? 'default' : 'metadata'}
                  size="sm"
                  className={i === 0 ? '' : 'border-white/56 bg-white/70'}
                >
                  {badge}
                </Badge>
              ))}
            </div>
          ) : null}

          {support ? (
            <p className="type-caption leading-6 text-card-foreground/74">{support}</p>
          ) : null}
        </div>
      </div>
    </GlassCard>
  );
}

type MemoryCalendarSummary = {
  activeDays: number;
  journalDays: number;
  cardDays: number;
  appreciationDays: number;
  photoDays: number;
};

interface MemoryCalendarAtlasProps {
  calendar: { year: number; month: number; days: CalendarDay[] } | null;
  year: number;
  month: number;
  loading: boolean;
  summary: MemoryCalendarSummary;
  selectedDate?: string | null;
  onSelectDate?: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export function MemoryCalendarAtlas({
  calendar,
  year,
  month,
  loading,
  summary,
  selectedDate,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
}: MemoryCalendarAtlasProps) {
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

  if (loading) {
    return (
      <GlassCard className="overflow-hidden rounded-[2.85rem] border-white/52 bg-white/82 p-6 shadow-lift backdrop-blur-xl md:p-8">
        <div className="space-y-5">
          <div className="flex items-center justify-between gap-4">
            <div className="h-11 w-11 animate-pulse rounded-full bg-muted" aria-hidden />
            <div className="h-8 w-44 animate-pulse rounded-[1.2rem] bg-muted" aria-hidden />
            <div className="h-11 w-11 animate-pulse rounded-full bg-muted" aria-hidden />
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-24 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft"
                aria-hidden
              />
            ))}
          </div>

          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: 35 }).map((_, index) => (
              <div
                key={index}
                className="min-h-[88px] animate-pulse rounded-[1.25rem] bg-white/76 shadow-soft"
                aria-hidden
              />
            ))}
          </div>
        </div>
      </GlassCard>
    );
  }

  const monthStart = new Date(year, month - 1, 1);
  const monthEnd = new Date(year, month, 0);
  const startPad = monthStart.getDay();
  const daysByDate = (calendar?.days ?? []).reduce((acc, day) => {
    acc[day.date] = day;
    return acc;
  }, {} as Record<string, CalendarDay>);

  /** Format a local Date as YYYY-MM-DD without UTC shift from toISOString. */
  const fmtLocal = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  const cells: Array<{ date: string; day: CalendarDay | null; isCurrentMonth: boolean }> = [];

  for (let i = 0; i < startPad; i += 1) {
    const dateKey = fmtLocal(new Date(year, month - 1, -startPad + i + 1));
    cells.push({
      date: dateKey,
      day: daysByDate[dateKey] ?? null,
      isCurrentMonth: false,
    });
  }

  for (let dayNumber = 1; dayNumber <= monthEnd.getDate(); dayNumber += 1) {
    const dateKey = `${year}-${String(month).padStart(2, '0')}-${String(dayNumber).padStart(2, '0')}`;
    cells.push({
      date: dateKey,
      day:
        daysByDate[dateKey] ?? {
          date: dateKey,
          mood_color: null,
          journal_count: 0,
          card_count: 0,
          appreciation_count: 0,
          has_photo: false,
        },
      isCurrentMonth: true,
    });
  }

  while (cells.length % 7 !== 0) {
    const offset = cells.length - (startPad + monthEnd.getDate()) + 1;
    const dateKey = fmtLocal(new Date(year, month, offset));
    cells.push({
      date: dateKey,
      day: daysByDate[dateKey] ?? null,
      isCurrentMonth: false,
    });
  }

  const today = fmtLocal(new Date());

  return (
    <GlassCard className="overflow-hidden rounded-[2.85rem] border-white/52 bg-[linear-gradient(165deg,rgba(255,252,248,0.95),rgba(243,236,227,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/80">Memory Atlas</p>
            <h2 className="type-h2 text-card-foreground">
              {year} 年 {month} 月
            </h2>
            <p className="type-body-muted text-muted-foreground">
              從月份與日期看見你們留下痕跡的密度，而不是只看單一一段故事。
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onPrevMonth}
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/56 bg-white/74 text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
              aria-label="上個月"
            >
              <ChevronLeft className="h-5 w-5" aria-hidden />
            </button>
            <button
              type="button"
              onClick={onNextMonth}
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/56 bg-white/74 text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
              aria-label="下個月"
            >
              <ChevronRight className="h-5 w-5" aria-hidden />
            </button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-5">
          <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">有痕跡的日子</p>
            <p className="mt-2 text-2xl font-semibold text-card-foreground">{summary.activeDays}</p>
          </div>
          <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">寫下日記</p>
            <p className="mt-2 text-2xl font-semibold text-card-foreground">{summary.journalDays}</p>
          </div>
          <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">留下卡片</p>
            <p className="mt-2 text-2xl font-semibold text-card-foreground">{summary.cardDays}</p>
          </div>
          <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">有感恩記錄</p>
            <p className="mt-2 text-2xl font-semibold text-card-foreground">{summary.appreciationDays}</p>
          </div>
          <div className="rounded-[1.8rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">有照片記錄</p>
            <p className="mt-2 text-2xl font-semibold text-card-foreground">{summary.photoDays}</p>
          </div>
        </div>

        <div className="rounded-[2.15rem] border border-white/56 bg-white/74 p-4 shadow-soft backdrop-blur-md md:p-5">
          <div className="grid grid-cols-7 gap-2">
            {weekdays.map((weekday) => (
              <div
                key={weekday}
                className="pb-2 text-center text-caption font-medium text-muted-foreground"
              >
                {weekday}
              </div>
            ))}

            {cells.map((cell) => {
              const day = cell.day;
              const hasJournal = Boolean(day?.journal_count);
              const hasCard = Boolean(day?.card_count);
              const hasAppreciation = Boolean(day?.appreciation_count);
              const hasPhoto = Boolean(day?.has_photo);
              const hasContent = hasJournal || hasCard || hasAppreciation || hasPhoto;
              const isSelected = cell.date === selectedDate;
              const cellLabel = [
                cell.date,
                hasJournal ? `日記 ${day?.journal_count ?? 0} 則` : null,
                hasCard ? `卡片 ${day?.card_count ?? 0} 張` : null,
                hasAppreciation ? `感恩 ${day?.appreciation_count ?? 0} 則` : null,
                hasPhoto ? '有照片' : null,
                hasContent ? '可展開這一天' : null,
              ]
                .filter(Boolean)
                .join('，');
              const cellClasses = cn(
                'min-h-[88px] rounded-[1.25rem] border px-2.5 py-2.5 shadow-soft transition-all duration-haven ease-haven',
                cell.isCurrentMonth
                  ? hasContent
                    ? 'border-primary/14 bg-primary/7'
                    : 'border-white/52 bg-white/72'
                  : 'border-white/46 bg-white/52 text-muted-foreground/68',
                cell.date === today ? 'ring-2 ring-primary/40 ring-offset-2 ring-offset-background' : '',
                isSelected ? 'border-primary/28 bg-primary/12 ring-2 ring-primary/24 ring-offset-2 ring-offset-background' : '',
                hasContent && cell.isCurrentMonth ? 'cursor-pointer hover:-translate-y-0.5 hover:shadow-lift' : '',
              );

              const cellContent = (
                <div className="flex h-full flex-col justify-between gap-3">
                  <span className="text-sm font-medium tabular-nums text-card-foreground/86">
                    {parseInt(cell.date.slice(8, 10), 10)}
                  </span>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {hasJournal ? (
                      <span className="inline-flex h-2.5 w-2.5 rounded-full bg-primary/80" aria-hidden />
                    ) : null}
                    {hasCard ? (
                      <span className="inline-flex h-2.5 w-2.5 rounded-full bg-accent/85" aria-hidden />
                    ) : null}
                    {hasAppreciation ? (
                      <span className="inline-flex h-2.5 w-2.5 rounded-full bg-rose-400/70" aria-hidden />
                    ) : null}
                    {hasPhoto ? (
                      <span className="inline-flex h-2.5 w-2.5 rounded-full border border-primary/35 bg-white/90" aria-hidden />
                    ) : null}
                  </div>
                </div>
              );

              if (hasContent && cell.isCurrentMonth) {
                return (
                  <button
                    key={cell.date}
                    type="button"
                    onClick={() => onSelectDate?.(cell.date)}
                    aria-pressed={isSelected}
                    aria-label={cellLabel}
                    className={cn(cellClasses, 'text-left focus-ring-premium')}
                  >
                    {cellContent}
                  </button>
                );
              }

              return (
                <div key={cell.date} className={cellClasses} aria-label={cellLabel}>
                  {cellContent}
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 rounded-[1.9rem] border border-white/56 bg-white/70 px-4 py-4 shadow-soft">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-primary/80" aria-hidden />
            <span className="type-caption text-muted-foreground">有日記</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-accent/85" aria-hidden />
            <span className="type-caption text-muted-foreground">有卡片</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-rose-400/70" aria-hidden />
            <span className="type-caption text-muted-foreground">有感恩</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full border border-primary/35 bg-white/90" aria-hidden />
            <span className="type-caption text-muted-foreground">有照片</span>
          </div>
          <p className="type-caption text-card-foreground/72">點亮的日子可以直接展開當天的片段。</p>
        </div>
      </div>
    </GlassCard>
  );
}

interface MemoryStatePanelProps {
  eyebrow: string;
  title: string;
  description: string;
  tone?: MemoryPanelTone;
  action?: ReactNode;
}

export function MemoryStatePanel({
  eyebrow,
  title,
  description,
  tone = 'default',
  action,
}: MemoryStatePanelProps) {
  return (
    <GlassCard
      className={cn(
        'overflow-hidden rounded-[2.3rem] p-6 shadow-soft backdrop-blur-xl md:p-7',
        panelToneClasses[tone],
      )}
    >
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="max-w-3xl type-body-muted text-muted-foreground">{description}</p>
        </div>

        {action ? <div className="flex flex-wrap gap-3">{action}</div> : null}
      </div>
    </GlassCard>
  );
}
