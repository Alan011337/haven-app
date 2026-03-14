'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  ChevronRight,
  History,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

import Badge from '@/components/ui/Badge';
import { GlassCard } from '@/components/haven/GlassCard';
import { CardBackVariant } from '@/components/haven/CardBackVariant';
import type { DeckMeta } from '@/lib/deck-meta';
import { routeLinkCtaClasses } from '@/features/decks/ui/routeStyleHelpers';

type DeckMetric = {
  label: string;
  value: string;
  note: string;
};

type DeckStatusVariant = 'metadata' | 'status' | 'filter';

type DeckLibraryShellProps = {
  backHref?: string;
  backLabel: string;
  actions?: ReactNode;
  children: ReactNode;
};

type DeckLibraryCoverProps = {
  eyebrow: string;
  title: string;
  description: string;
  metrics: DeckMetric[];
  featured: ReactNode;
  rail: ReactNode;
};

type DeckLibrarySectionHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
};

type DeckLibraryBrowseBandProps = {
  eyebrow: string;
  title: string;
  description: string;
  resultCount: number;
  totalCount: number;
  controls: ReactNode;
  sortControl: ReactNode;
};

type SharedDeckCardProps = {
  deck: DeckMeta;
  href: string;
  eyebrow: string;
  spotlight: string;
  shortHook: string;
  progressLabel: string;
  countLabel: string;
  statusLabel: string;
  statusVariant: DeckStatusVariant;
  progressWidth: number;
  loading?: boolean;
};

type DeckLibraryFeaturedCardProps = SharedDeckCardProps & {
  ctaLabel: string;
};

type DeckLibraryRailCardProps = {
  eyebrow: string;
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
  icon?: LucideIcon;
};

function DeckPreviewFigure({
  deck,
  emphasis,
}: {
  deck: DeckMeta;
  emphasis: 'feature' | 'companion' | 'shelf';
}) {
  const sizeClass =
    emphasis === 'feature'
      ? 'mx-auto aspect-[4/5] w-full max-w-[13rem]'
      : emphasis === 'companion'
        ? 'aspect-[4/5] w-24 sm:w-28'
        : 'aspect-[4/5] w-20';

  return (
    <div className={`relative ${sizeClass}`}>
      <CardBackVariant deck={deck}>
        <div className="text-center">
          <deck.Icon
            className={
              emphasis === 'feature'
                ? 'mx-auto mb-3 h-8 w-8 text-white/92'
                : 'mx-auto mb-2 h-6 w-6 text-white/88'
            }
            strokeWidth={2}
            aria-hidden
          />
          <p className="type-micro uppercase tracking-[0.22em] text-white/82">
            {emphasis === 'feature' ? "Tonight's Pick" : 'Haven Deck'}
          </p>
        </div>
      </CardBackVariant>
    </div>
  );
}

function DeckProgressSummary({
  progressLabel,
  countLabel,
  progressWidth,
  loading = false,
}: {
  progressLabel: string;
  countLabel: string;
  progressWidth: number;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="stack-block">
        <div className="h-2 w-full animate-pulse rounded-full bg-muted/70" aria-hidden />
        <div className="h-4 w-2/3 animate-pulse rounded-full bg-muted/70" aria-hidden />
      </div>
    );
  }

  return (
    <div className="stack-block">
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted/70">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary via-accent to-primary/75 transition-all duration-haven ease-haven"
          style={{ width: `${Math.max(0, Math.min(100, progressWidth))}%` }}
        />
      </div>
      <div className="flex items-center justify-between gap-3 type-caption text-muted-foreground">
        <span className="tabular-nums">{progressLabel}</span>
        <span>{countLabel}</span>
      </div>
    </div>
  );
}

function DeckCardFooter({
  statusLabel,
  statusVariant,
  ctaLabel,
  featured = false,
}: {
  statusLabel: string;
  statusVariant: DeckStatusVariant;
  ctaLabel: string;
  featured?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.4rem] border border-white/50 bg-white/70 px-4 py-3 shadow-soft">
      <Badge
        variant={statusVariant}
        size="sm"
        className="bg-white/78 text-card-foreground/84 shadow-none"
      >
        {statusLabel}
      </Badge>
      <span
        className={
          featured
            ? 'inline-flex items-center gap-[var(--space-inline)] rounded-button border border-primary/16 bg-primary/8 px-5 py-3 type-label text-card-foreground shadow-soft'
            : 'inline-flex items-center gap-[var(--space-inline)] type-label text-card-foreground'
        }
      >
        {ctaLabel}
        <ChevronRight className="h-4 w-4" aria-hidden />
      </span>
    </div>
  );
}

export function DeckLibraryShell({
  backHref = '/',
  backLabel,
  actions,
  children,
}: DeckLibraryShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.16),transparent_24%),radial-gradient(circle_at_88%_8%,rgba(234,240,234,0.5),transparent_28%),linear-gradient(180deg,#fbf8f3_0%,#f5f0e8_54%,#f1ece4_100%)]">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.74),transparent_60%),radial-gradient(circle_at_76%_18%,rgba(255,255,255,0.24),transparent_22%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-12 top-24 h-72 w-72 rounded-full bg-primary/9 blur-hero-orb"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb"
        aria-hidden
      />

      <div className="relative mx-auto max-w-[1540px] space-y-[clamp(1.5rem,3vw,2.75rem)] px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link href={backHref} className={routeLinkCtaClasses.neutral}>
            <ArrowLeft className="h-4 w-4" aria-hidden />
            {backLabel}
          </Link>
          {actions}
        </div>

        {children}
      </div>
    </div>
  );
}

export function DeckLibraryCover({
  eyebrow,
  title,
  description,
  metrics,
  featured,
  rail,
}: DeckLibraryCoverProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[3rem] border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(247,242,235,0.74))] p-6 shadow-[0_28px_90px_rgba(63,44,26,0.1)] md:p-8 xl:p-10">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.74),transparent_38%),radial-gradient(circle_at_70%_12%,rgba(255,255,255,0.22),transparent_22%)]"
        aria-hidden
      />
      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.08fr)_320px]">
        <div className="stack-section">
          <div className="stack-block">
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/54 bg-white/76 px-4 py-2 shadow-soft">
              <span className="h-2 w-2 rounded-full bg-primary/75" aria-hidden />
              <span className="type-micro uppercase text-primary/82">Curated Collection</span>
            </div>
            <p className="type-micro uppercase text-primary/76">{eyebrow}</p>
          </div>

          <div className="stack-block">
            <h1 className="max-w-[32rem] type-h1 text-card-foreground">{title}</h1>
            <p className="max-w-[30rem] type-body-muted text-muted-foreground">{description}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
            {metrics.map((metric) => (
              <div
                key={metric.label}
                className="rounded-[1.7rem] border border-white/55 bg-white/70 p-4 shadow-soft"
              >
                <p className="type-micro uppercase text-primary/70">{metric.label}</p>
                <p className="mt-3 text-2xl font-semibold tabular-nums text-card-foreground">
                  {metric.value}
                </p>
                <p className="mt-2 type-caption text-muted-foreground">{metric.note}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="min-h-full">{featured}</div>

        <div className="stack-section">{rail}</div>
      </div>
    </GlassCard>
  );
}

export function DeckLibraryFeaturedCard({
  deck,
  href,
  eyebrow,
  spotlight,
  shortHook,
  progressLabel,
  countLabel,
  statusLabel,
  statusVariant,
  progressWidth,
  ctaLabel,
  loading = false,
}: DeckLibraryFeaturedCardProps) {
  return (
    <Link href={href} className="group block focus-visible:outline-none">
      <GlassCard className="h-full overflow-hidden rounded-[2.7rem] border-white/52 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.34),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.9),rgba(245,239,230,0.84))] p-6 shadow-soft transition-all duration-haven ease-haven group-hover:-translate-y-1 group-hover:shadow-[0_30px_80px_rgba(63,44,26,0.13)] md:p-7">
        <div className="relative z-10 flex h-full flex-col justify-between gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="metadata" size="sm" className="bg-white/78 text-primary/76 shadow-soft">
              {eyebrow}
            </Badge>
            <Badge variant={statusVariant} size="sm" className="bg-white/76 text-card-foreground/84 shadow-soft">
              {statusLabel}
            </Badge>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-center">
            <div className="stack-section">
              <div className="stack-block">
                <h2 className="type-h2 text-card-foreground">{deck.title}</h2>
                <p className="max-w-[32rem] type-body text-card-foreground/92">{spotlight}</p>
              </div>

              <div className="rounded-[1.7rem] border border-white/48 bg-white/66 p-4 shadow-soft">
                <p className="type-body-muted text-muted-foreground">{shortHook}</p>
              </div>

              <DeckProgressSummary
                progressLabel={progressLabel}
                countLabel={countLabel}
                progressWidth={progressWidth}
                loading={loading}
              />
            </div>

            <div className="flex items-center justify-center">
              <DeckPreviewFigure deck={deck} emphasis="feature" />
            </div>
          </div>

          <DeckCardFooter
            statusLabel={statusLabel}
            statusVariant={statusVariant}
            ctaLabel={ctaLabel}
            featured
          />
        </div>
      </GlassCard>
    </Link>
  );
}

export function DeckLibraryCompanionCard({
  deck,
  href,
  eyebrow,
  spotlight,
  shortHook,
  progressLabel,
  countLabel,
  statusLabel,
  statusVariant,
  progressWidth,
  loading = false,
}: SharedDeckCardProps) {
  return (
    <Link href={href} className="group block focus-visible:outline-none">
      <GlassCard className="h-full overflow-hidden rounded-[2.3rem] border-white/52 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(246,241,233,0.8))] p-5 shadow-soft transition-all duration-haven ease-haven group-hover:-translate-y-1 group-hover:shadow-lift md:p-6">
        <div className="flex h-full flex-col justify-between gap-5">
          <div className="flex items-start justify-between gap-4">
            <div className="stack-block">
              <p className="type-micro uppercase text-primary/74">{eyebrow}</p>
              <div className="stack-block">
                <h3 className="type-h3 text-card-foreground">{deck.title}</h3>
                <p className="type-caption text-muted-foreground">{spotlight}</p>
              </div>
            </div>
            <DeckPreviewFigure deck={deck} emphasis="companion" />
          </div>

          <div className="stack-block">
            <p className="type-body-muted text-card-foreground/88">{shortHook}</p>
            <DeckProgressSummary
              progressLabel={progressLabel}
              countLabel={countLabel}
              progressWidth={progressWidth}
              loading={loading}
            />
          </div>

          <DeckCardFooter
            statusLabel={statusLabel}
            statusVariant={statusVariant}
            ctaLabel="打開牌組"
          />
        </div>
      </GlassCard>
    </Link>
  );
}

export function DeckLibraryShelfCard({
  deck,
  href,
  eyebrow,
  spotlight,
  shortHook,
  progressLabel,
  countLabel,
  statusLabel,
  statusVariant,
  progressWidth,
  loading = false,
}: SharedDeckCardProps) {
  return (
    <Link href={href} className="group block focus-visible:outline-none">
      <GlassCard className="h-full overflow-hidden rounded-[2.05rem] border-white/52 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(247,242,236,0.8))] p-5 shadow-soft transition-all duration-haven ease-haven group-hover:-translate-y-px group-hover:shadow-lift">
        <div className="flex h-full flex-col justify-between gap-5">
          <div className="flex items-start justify-between gap-4">
            <div className="stack-block">
              <p className="type-micro uppercase text-primary/72">{eyebrow}</p>
              <div className="stack-block">
                <h3 className="type-section-title text-card-foreground">{deck.title}</h3>
                <p className="type-caption text-muted-foreground">{spotlight}</p>
              </div>
            </div>
            <DeckPreviewFigure deck={deck} emphasis="shelf" />
          </div>

          <div className="stack-block">
            <p className="type-caption leading-relaxed text-card-foreground/86">{shortHook}</p>
            <DeckProgressSummary
              progressLabel={progressLabel}
              countLabel={countLabel}
              progressWidth={progressWidth}
              loading={loading}
            />
          </div>

          <DeckCardFooter
            statusLabel={statusLabel}
            statusVariant={statusVariant}
            ctaLabel="打開牌組"
          />
        </div>
      </GlassCard>
    </Link>
  );
}

export function DeckLibraryRailCard({
  eyebrow,
  title,
  description,
  actionHref,
  actionLabel,
  icon: Icon = Sparkles,
}: DeckLibraryRailCardProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.1rem] border-white/55 bg-[linear-gradient(180deg,rgba(251,253,251,0.84),rgba(243,247,244,0.78))] p-5 shadow-soft">
      <div className="stack-section">
        <div className="stack-block">
          <span
            className="inline-flex h-11 w-11 items-center justify-center rounded-[1.15rem] border border-white/55 bg-white/76 shadow-soft"
            aria-hidden
          >
            <Icon className="h-4 w-4 text-primary" />
          </span>
          <div className="stack-block">
            <p className="type-micro uppercase text-primary/72">{eyebrow}</p>
            <h3 className="type-section-title text-card-foreground">{title}</h3>
            <p className="type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>

        {actionHref && actionLabel ? (
          <Link href={actionHref} className={routeLinkCtaClasses.neutral}>
            {actionLabel}
            <ChevronRight className="h-4 w-4" aria-hidden />
          </Link>
        ) : null}
      </div>
    </GlassCard>
  );
}

export function DeckLibraryBrowseBand({
  eyebrow,
  title,
  description,
  resultCount,
  totalCount,
  controls,
  sortControl,
}: DeckLibraryBrowseBandProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.35rem] border-white/54 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(247,243,236,0.78))] p-5 md:p-6">
      <div className="stack-section">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="stack-block">
            <p className="type-micro uppercase text-primary/72">{eyebrow}</p>
            <div className="stack-block">
              <h2 className="type-h3 text-card-foreground">{title}</h2>
              <p className="type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/55 bg-white/74 px-4 py-3 shadow-soft">
            <span className="type-micro uppercase text-primary/74">顯示中</span>
            <Badge
              variant="metadata"
              size="md"
              className="bg-white/82 tabular-nums text-card-foreground shadow-none"
            >
              {resultCount}/{totalCount}
            </Badge>
          </div>
        </div>

        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-2">{controls}</div>
          <div className="shrink-0">{sortControl}</div>
        </div>
      </div>
    </GlassCard>
  );
}

export function DeckLibrarySectionHeader({
  eyebrow,
  title,
  description,
  aside,
}: DeckLibrarySectionHeaderProps) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="stack-block max-w-3xl">
        <p className="type-micro uppercase text-primary/72">{eyebrow}</p>
        <div className="stack-block">
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </div>
  );
}

export function DeckLibraryFallbackCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <GlassCard className="h-full overflow-hidden rounded-[2.7rem] border-white/52 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(246,241,234,0.82))] p-6 shadow-soft md:p-7">
      <div className="flex h-full flex-col justify-between gap-6">
        <div className="stack-block">
          <Badge variant="metadata" size="sm" className="w-fit bg-white/78 text-primary/76 shadow-soft">
            Curator&apos;s Pause
          </Badge>
          <div className="stack-block">
            <h2 className="type-h2 text-card-foreground">{title}</h2>
            <p className="type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>

        <div className="rounded-[1.7rem] border border-white/48 bg-white/70 p-5 shadow-soft">
          <p className="type-body-muted text-card-foreground/86">
            這一頁仍然保留圖書館的整體氣氛，等你換個條件後再把館藏慢慢展開。
          </p>
        </div>
      </div>
    </GlassCard>
  );
}

export function DeckLibraryArchiveShortcut() {
  return (
    <Link href="/decks/history" className={routeLinkCtaClasses.neutral}>
      <History className="h-4 w-4" aria-hidden />
      對話檔案館
    </Link>
  );
}
