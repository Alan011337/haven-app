'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Compass, Sparkles } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import { parseSharedFutureNotes } from '@/lib/shared-future-read-model';
import { cn } from '@/lib/utils';

type BlueprintStateTone = 'default' | 'quiet' | 'error';

const stateToneClasses: Record<BlueprintStateTone, string> = {
  default: 'border-white/54 bg-white/84',
  quiet: 'border-primary/12 bg-white/76',
  error:
    'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,251,249,0.96),rgba(248,240,236,0.94))]',
};

interface BlueprintShellProps {
  children: ReactNode;
}

export function BlueprintShell({ children }: BlueprintShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_26%),radial-gradient(circle_at_88%_10%,rgba(232,238,233,0.46),transparent_28%),linear-gradient(180deg,#fcfaf6_0%,#f5efe7_52%,#efe7de_100%)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
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
              href="/love-map"
              className="inline-flex items-center gap-2 rounded-full border border-white/52 bg-white/64 px-4 py-2.5 text-sm font-medium text-card-foreground/88 shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-white/74 hover:text-card-foreground hover:shadow-lift focus-ring-premium"
            >
              Relationship System 摘要
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>

          <Badge variant="metadata" size="md" className="border-white/50 bg-white/72 text-primary/78 shadow-soft">
            Shared Future Blueprint
          </Badge>
        </div>

        {children}
      </div>
    </div>
  );
}

interface BlueprintCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  primaryActionHref: string;
  primaryActionLabel: string;
  highlights?: ReactNode;
  aside: ReactNode;
}

export function BlueprintCover({
  eyebrow,
  title,
  description,
  pulse,
  primaryActionHref,
  primaryActionLabel,
  highlights,
  aside,
}: BlueprintCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.95),rgba(246,239,230,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.74),transparent_36%),radial-gradient(circle_at_84%_12%,rgba(255,255,255,0.34),transparent_22%)]"
        aria-hidden
      />
      <div className="pointer-events-none absolute right-[-4rem] top-[-2rem] h-72 w-72 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-3rem] left-[-1rem] h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <div className="space-y-4">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h1 className="max-w-[58rem] type-h1 text-card-foreground">{title}</h1>
              <p className="max-w-[48rem] type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.9rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Compass className="h-4 w-4" aria-hidden />
            </span>
            <p className="type-body-muted text-card-foreground">{pulse}</p>
          </div>

          {highlights}

          <a
            href={primaryActionHref}
            className="inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium"
          >
            {primaryActionLabel}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </a>
        </div>

        <div className="space-y-4">{aside}</div>
      </div>
    </section>
  );
}

interface BlueprintOverviewCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}

export function BlueprintOverviewCard({
  eyebrow,
  title,
  description,
  children,
}: BlueprintOverviewCardProps) {
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

interface BlueprintWishStudioProps {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function BlueprintWishStudio({
  id,
  eyebrow,
  title,
  description,
  children,
  footer,
}: BlueprintWishStudioProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <GlassCard className="overflow-hidden rounded-[2.85rem] border-white/52 bg-[linear-gradient(165deg,rgba(255,252,248,0.95),rgba(243,236,227,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)] xl:gap-10">
          <div className="space-y-4 xl:sticky xl:top-24 xl:self-start">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h2 className="type-h2 text-card-foreground">{title}</h2>
              <p className="type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[2.2rem] border border-white/56 bg-white/76 p-5 shadow-soft backdrop-blur-md md:p-6">
              {children}
            </div>
            {footer}
          </div>
        </div>
      </GlassCard>
    </section>
  );
}

interface BlueprintFeaturedWishProps {
  title: string;
  notes?: string;
  authorLabel: string;
  createdLabel: string;
  spotlight: string;
}

function BlueprintStructuredWishSection({
  label,
  entries,
  compact = false,
}: {
  label: string;
  entries: string[];
  compact?: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className="type-micro uppercase text-primary/80">{label}</p>
      <div className="space-y-2">
        {entries.map((entry, index) => (
          <div
            key={`${label}-${index}-${entry}`}
            className={cn(
              'rounded-[1.2rem] border border-white/58 bg-white/72 shadow-soft',
              compact ? 'px-3 py-2.5' : 'px-4 py-3',
            )}
          >
            <p className={cn(compact ? 'type-caption leading-6 text-card-foreground' : 'type-body-muted text-card-foreground')}>
              {entry}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function BlueprintSharedFutureNotesPanel({
  notes,
  emptyText,
  compact = false,
}: {
  notes?: string;
  emptyText: string;
  compact?: boolean;
}) {
  const readModel = parseSharedFutureNotes(notes);

  if (!notes) {
    return (
      <p
        className={cn(
          compact ? 'type-caption leading-6 text-muted-foreground' : 'type-body-muted leading-7 text-card-foreground/88',
        )}
      >
        {emptyText}
      </p>
    );
  }

  if (!readModel.hasStructuredRefinements) {
    return (
      <p
        className={cn(
          compact ? 'type-caption leading-6 text-muted-foreground' : 'type-body-muted leading-7 text-card-foreground/88',
        )}
      >
        {notes}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {readModel.baseNote ? (
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">補充</p>
          <p
            className={cn(
              compact ? 'type-caption leading-6 text-muted-foreground' : 'type-body-muted leading-7 text-card-foreground/88',
            )}
          >
            {readModel.baseNote}
          </p>
        </div>
      ) : null}

      {readModel.nextSteps.length > 0 ? (
        <BlueprintStructuredWishSection label="下一步" entries={readModel.nextSteps} compact={compact} />
      ) : null}

      {readModel.cadences.length > 0 ? (
        <BlueprintStructuredWishSection label="節奏" entries={readModel.cadences} compact={compact} />
      ) : null}
    </div>
  );
}

export function BlueprintFeaturedWish({
  title,
  notes,
  authorLabel,
  createdLabel,
  spotlight,
}: BlueprintFeaturedWishProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.95rem] border-white/52 bg-[linear-gradient(165deg,rgba(255,253,250,0.95),rgba(244,237,229,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px] xl:gap-10">
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant="warning" size="sm">
              Featured Wish
            </Badge>
            <Badge variant="metadata" size="sm">
              {authorLabel}
            </Badge>
          </div>

          <div className="space-y-3">
            <h3 className="type-h2 text-card-foreground">{title}</h3>
            <div className="max-w-4xl">
              <BlueprintSharedFutureNotesPanel
                notes={notes}
                emptyText="這個願望暫時還沒有寫下更多細節。留白本身也是一種想像，等你們下次一起補上它。"
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[2rem] border border-white/56 bg-white/72 p-5 shadow-soft backdrop-blur-md">
            <div className="space-y-3">
              <p className="type-micro uppercase text-primary/80">Why it matters</p>
              <div className="flex items-start gap-3">
                <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Sparkles className="h-4 w-4" aria-hidden />
                </span>
                <p className="type-body-muted text-card-foreground">{spotlight}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-[1.7rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">寫下這一筆的人</p>
              <p className="mt-2 text-lg font-semibold text-card-foreground">{authorLabel}</p>
            </div>
            <div className="rounded-[1.7rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft">
              <p className="type-micro uppercase text-primary/80">加入藍圖的時間</p>
              <p className="mt-2 text-lg font-semibold text-card-foreground">{createdLabel}</p>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

interface BlueprintCompanionWishProps {
  title: string;
  notes?: string;
  authorLabel: string;
  createdLabel: string;
}

export function BlueprintCompanionWish({
  title,
  notes,
  authorLabel,
  createdLabel,
}: BlueprintCompanionWishProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.3rem] border-white/52 bg-white/80 p-5 shadow-soft backdrop-blur-xl md:p-6">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="metadata" size="sm">
            Companion Wish
          </Badge>
          <Badge variant="outline" size="sm">
            {authorLabel}
          </Badge>
        </div>

        <div className="space-y-3">
          <h3 className="type-h3 text-card-foreground">{title}</h3>
          <BlueprintSharedFutureNotesPanel
            notes={notes}
            emptyText="這個願望還保留著更多留白，等下一次一起補上更具體的想像。"
          />
        </div>

        <p className="type-caption text-card-foreground/76">{createdLabel}</p>
      </div>
    </GlassCard>
  );
}

interface BlueprintShelfWishProps {
  title: string;
  notes?: string;
  authorLabel: string;
  createdLabel: string;
}

export function BlueprintShelfWish({
  title,
  notes,
  authorLabel,
  createdLabel,
}: BlueprintShelfWishProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2rem] border-white/52 bg-white/78 p-5 shadow-soft backdrop-blur-md">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="metadata" size="sm">
            Quiet Wish
          </Badge>
          <Badge variant="outline" size="sm">
            {authorLabel}
          </Badge>
        </div>

        <div className="space-y-2.5">
          <h3 className="type-section-title text-card-foreground">{title}</h3>
          <BlueprintSharedFutureNotesPanel
            notes={notes}
            emptyText="先讓它留在這裡，等你們哪天回來時，再決定要替它補上哪一種細節。"
            compact
          />
        </div>

        <p className="type-caption text-card-foreground/72">{createdLabel}</p>
      </div>
    </GlassCard>
  );
}

interface BlueprintStatePanelProps {
  eyebrow: string;
  title: string;
  description: string;
  tone?: BlueprintStateTone;
  action?: ReactNode;
}

export function BlueprintStatePanel({
  eyebrow,
  title,
  description,
  tone = 'default',
  action,
}: BlueprintStatePanelProps) {
  return (
    <GlassCard
      className={cn(
        'overflow-hidden rounded-[2.3rem] p-6 shadow-soft backdrop-blur-xl md:p-7',
        stateToneClasses[tone],
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
