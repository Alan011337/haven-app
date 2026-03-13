import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, ChevronRight, Sparkles, type LucideIcon } from 'lucide-react';

import Button from '@/components/ui/Button';
import { GlassCard } from '@/components/haven/GlassCard';
import { CardBackVariant } from '@/components/haven/CardBackVariant';
import { getDeckDisplayName, getDeckMeta, type DeckMeta } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
import type { DeckHistoryEntry } from '@/services/deckService';

type DeckShellProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  backHref?: string;
  backLabel: string;
  onBack?: () => void;
  actions?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  containerClassName?: string;
};

export function DeckShell({
  eyebrow,
  title,
  subtitle,
  backHref,
  backLabel,
  onBack,
  actions,
  aside,
  children,
  containerClassName = 'max-w-6xl',
}: DeckShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]" aria-hidden />
      <div className={`relative mx-auto space-y-6 px-4 py-6 sm:px-6 lg:px-8 ${containerClassName}`}>
        <div className="flex items-center justify-between gap-4">
          {onBack ? (
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/74 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              {backLabel}
            </button>
          ) : (
            <Link
              href={backHref ?? '/'}
              className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/74 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              {backLabel}
            </Link>
          )}
          {actions}
        </div>

        <GlassCard className="overflow-hidden rounded-[2rem] border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(248,244,238,0.72))] p-6 shadow-[0_22px_80px_rgba(63,44,26,0.08)] md:p-8">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px] xl:items-end">
            <div className="space-y-4">
              <p className="text-[0.74rem] uppercase tracking-[0.34em] text-primary/72">{eyebrow}</p>
              <h1 className="max-w-4xl font-art text-[2rem] leading-tight text-card-foreground md:text-[3.2rem]">
                {title}
              </h1>
              <p className="max-w-3xl text-sm leading-7 text-muted-foreground md:text-base">
                {subtitle}
              </p>
            </div>
            {aside ? <div className="xl:justify-self-end">{aside}</div> : null}
          </div>
        </GlassCard>

        {children}
      </div>
    </div>
  );
}

type DeckHeroMetric = {
  label: string;
  value: string;
  note: string;
};

type DeckHeroPanelProps = {
  eyebrow: string;
  title: string;
  description: string;
  metrics: DeckHeroMetric[];
  aside: ReactNode;
};

export function DeckHeroPanel({
  eyebrow,
  title,
  description,
  metrics,
  aside,
}: DeckHeroPanelProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_360px] xl:items-stretch">
      <GlassCard className="overflow-hidden rounded-[2rem] border-white/52 bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(247,243,236,0.75))] p-6 md:p-7">
        <div className="space-y-5">
          <div className="space-y-3">
            <p className="text-[0.72rem] uppercase tracking-[0.32em] text-primary/70">{eyebrow}</p>
            <h2 className="max-w-3xl font-art text-[1.8rem] leading-tight text-card-foreground md:text-[2.5rem]">
              {title}
            </h2>
            <p className="max-w-3xl text-sm leading-7 text-muted-foreground md:text-base">
              {description}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {metrics.map((metric, index) => (
              <div
                key={metric.label}
                className={`rounded-[1.4rem] border border-white/55 bg-white/68 p-4 shadow-soft animate-slide-up-fade${index > 0 ? `-${Math.min(index, 5)}` : ''}`}
              >
                <p className="text-[0.68rem] uppercase tracking-[0.24em] text-primary/68">{metric.label}</p>
                <p className="mt-3 text-2xl font-semibold text-card-foreground tabular-nums">{metric.value}</p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{metric.note}</p>
              </div>
            ))}
          </div>
        </div>
      </GlassCard>

      {aside}
    </div>
  );
}

type DeckCollectionTileProps = {
  deck: DeckMeta;
  href: string;
  eyebrow: string;
  spotlight: string;
  shortHook: string;
  progressLabel: string;
  countLabel: string;
  statusLabel: string;
  progressWidth: number;
  emphasis?: 'feature' | 'standard';
  loading?: boolean;
};

export function DeckCollectionTile({
  deck,
  href,
  eyebrow,
  spotlight,
  shortHook,
  progressLabel,
  countLabel,
  statusLabel,
  progressWidth,
  emphasis = 'standard',
  loading = false,
}: DeckCollectionTileProps) {
  const isFeature = emphasis === 'feature';

  return (
    <Link href={href} prefetch className="group focus-visible:outline-none">
      <article
        className={`relative overflow-hidden rounded-[2rem] border border-white/52 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(246,241,234,0.76))] p-5 shadow-soft transition-all duration-haven ease-haven hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(63,44,26,0.12)] ${
          isFeature ? 'min-h-[22rem] md:min-h-[24rem]' : 'min-h-[18rem]'
        }`}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.5),transparent_40%)]" aria-hidden />
        <div className="relative flex h-full flex-col justify-between">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-3">
              <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/70">{eyebrow}</p>
              <div className="space-y-2">
                <h3 className="font-art text-[1.45rem] leading-tight text-card-foreground md:text-[1.7rem]">
                  {deck.title}
                </h3>
                <p className="max-w-[32rem] text-sm leading-6 text-muted-foreground">{spotlight}</p>
              </div>
            </div>
            <div className="relative h-20 w-16 shrink-0 overflow-hidden rounded-[1rem] shadow-soft ring-1 ring-black/5">
              <CardBackVariant deck={deck}>
                <deck.Icon className={`h-5 w-5 ${deck.iconColor}`} strokeWidth={2.2} aria-hidden />
              </CardBackVariant>
            </div>
          </div>

          <div className="space-y-4">
            <p className="text-sm leading-6 text-card-foreground/88">{shortHook}</p>
            {loading ? (
              <div className="space-y-3">
                <div className="h-2 w-full rounded-full bg-muted/70 animate-pulse" aria-hidden />
                <div className="h-9 w-full rounded-full bg-muted/70 animate-pulse" aria-hidden />
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <div className="h-2 w-full overflow-hidden rounded-full bg-muted/70">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${deck.color} transition-all duration-haven ease-haven`}
                      style={{ width: `${Math.max(0, Math.min(100, progressWidth))}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                    <span className="tabular-nums">{progressLabel}</span>
                    <span>{countLabel}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-full border border-white/55 bg-white/66 px-4 py-3">
                  <span className="text-xs font-medium uppercase tracking-[0.22em] text-primary/72">{statusLabel}</span>
                  <span className="inline-flex items-center gap-1 text-sm font-medium text-card-foreground">
                    打開牌組
                    <ChevronRight className="h-4 w-4 transition-transform duration-haven ease-haven group-hover:translate-x-0.5" aria-hidden />
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </article>
    </Link>
  );
}

type DeckStatePanelProps = {
  eyebrow: string;
  title: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  tone?: 'paper' | 'mist' | 'ritual';
  children?: ReactNode;
};

export function DeckStatePanel({
  eyebrow,
  title,
  description,
  icon: Icon = Sparkles,
  actionLabel,
  actionHref,
  onAction,
  tone = 'paper',
  children,
}: DeckStatePanelProps) {
  const toneClass =
    tone === 'ritual'
      ? 'bg-[linear-gradient(180deg,rgba(255,255,255,0.8),rgba(245,240,231,0.82))]'
      : tone === 'mist'
        ? 'bg-[linear-gradient(180deg,rgba(248,252,250,0.84),rgba(241,247,244,0.74))]'
        : 'bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(247,243,236,0.76))]';

  return (
    <GlassCard className={`overflow-hidden rounded-[2rem] border-white/52 p-6 md:p-7 ${toneClass}`}>
      <div className="space-y-5">
        <div className="flex items-start gap-3">
          <span className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/55 bg-white/74 shadow-soft" aria-hidden>
            <Icon className="h-4 w-4 text-primary" />
          </span>
          <div className="space-y-2">
            <p className="text-[0.7rem] uppercase tracking-[0.3em] text-primary/70">{eyebrow}</p>
            <h3 className="font-art text-[1.5rem] leading-tight text-card-foreground">{title}</h3>
            <p className="max-w-2xl text-sm leading-7 text-muted-foreground">{description}</p>
          </div>
        </div>
        {children}
        {actionLabel
          ? actionHref ? (
              <Link
                href={actionHref}
                className="inline-flex items-center gap-2 rounded-full border border-primary/16 bg-primary/8 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
              >
                {actionLabel}
                <ChevronRight className="h-4 w-4" aria-hidden />
              </Link>
            ) : onAction ? (
                <Button variant="primary" size="lg" onClick={onAction}>
                  {actionLabel}
                </Button>
              ) : null
          : null}
      </div>
    </GlassCard>
  );
}

type DeckRoomStageProps = {
  eyebrow: string;
  title: string;
  description: string;
  badge?: string;
  tone?: 'paper' | 'mist' | 'ritual';
  footer?: ReactNode;
  children: ReactNode;
};

export function DeckRoomStage({
  eyebrow,
  title,
  description,
  badge,
  tone = 'ritual',
  footer,
  children,
}: DeckRoomStageProps) {
  const toneClass =
    tone === 'mist'
      ? 'bg-[radial-gradient(circle_at_top_right,rgba(223,234,228,0.3),transparent_32%),linear-gradient(180deg,rgba(250,252,251,0.82),rgba(241,247,244,0.76))]'
      : tone === 'paper'
        ? 'bg-[radial-gradient(circle_at_top_right,rgba(214,181,136,0.12),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.84),rgba(247,243,236,0.8))]'
        : 'bg-[radial-gradient(circle_at_top,rgba(214,181,136,0.16),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.86),rgba(244,239,231,0.84))]';

  return (
    <GlassCard className={`overflow-hidden rounded-[2rem] border-white/55 p-6 md:p-8 ${toneClass}`}>
      <div className="space-y-6">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-[0.72rem] uppercase tracking-[0.3em] text-primary/70">{eyebrow}</p>
            {badge ? (
              <span className="rounded-full border border-white/55 bg-white/74 px-3 py-1 text-[0.66rem] uppercase tracking-[0.24em] text-card-foreground shadow-soft">
                {badge}
              </span>
            ) : null}
          </div>
          <h2 className="font-art text-[1.9rem] leading-tight text-card-foreground md:text-[2.6rem]">
            {title}
          </h2>
          <p className="max-w-3xl text-sm leading-7 text-muted-foreground md:text-base">
            {description}
          </p>
        </div>
        {children}
        {footer}
      </div>
    </GlassCard>
  );
}

type DeckArchiveCardProps = {
  entry: DeckHistoryEntry;
  className?: string;
};

export function DeckArchiveCard({ entry, className = '' }: DeckArchiveCardProps) {
  const deckMeta = getDeckMeta(entry.category);
  const deckTitle = getDeckDisplayName(entry.category);
  const depthLevel = resolveDepthLevel(entry.depth_level);
  const depth = getDepthPresentation(depthLevel);

  return (
    <article
      className={`relative overflow-hidden rounded-[2rem] border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(248,244,238,0.78))] shadow-soft ${className}`}
    >
      <div className={`absolute inset-x-0 top-0 h-1 ${depth.topAccentClass}`} aria-hidden />
      <div className="space-y-6 p-6 md:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-white/55 bg-white/72 px-3 py-1 text-[0.66rem] uppercase tracking-[0.24em] text-primary/72">
                {deckTitle}
              </span>
              <span className={`rounded-full px-3 py-1 text-[0.66rem] uppercase tracking-[0.24em] ${depth.badgeClass}`}>
                深度 {depthLevel} · {depth.label}
              </span>
            </div>
            <h3 className="max-w-3xl font-art text-[1.35rem] leading-tight text-card-foreground md:text-[1.6rem]">
              {entry.card_question}
            </h3>
          </div>
          <div className="space-y-2 text-right">
            <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">解鎖日期</div>
            <div className="text-sm font-medium tabular-nums text-card-foreground">
              {new Date(entry.revealed_at).toLocaleDateString('zh-TW')}
            </div>
            {deckMeta ? (
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/55 bg-white/76 shadow-soft" aria-hidden>
                <deckMeta.Icon className={`h-5 w-5 ${deckMeta.iconColor}`} strokeWidth={2.2} />
              </span>
            ) : null}
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <section className="rounded-[1.5rem] border border-primary/12 bg-primary/6 p-5">
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/72">我的回應</p>
            <p className="mt-3 text-sm leading-7 text-card-foreground">{entry.my_answer}</p>
          </section>
          <section className="rounded-[1.5rem] border border-white/55 bg-white/74 p-5">
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-muted-foreground">伴侶回應</p>
            <p className="mt-3 text-sm leading-7 text-card-foreground">{entry.partner_answer}</p>
          </section>
        </div>
      </div>
    </article>
  );
}
