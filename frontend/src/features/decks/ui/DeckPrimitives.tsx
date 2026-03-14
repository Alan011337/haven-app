import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, ChevronRight, Sparkles, type LucideIcon } from 'lucide-react';

import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { GlassCard } from '@/components/haven/GlassCard';
import { routeLinkCtaClasses } from './routeStyleHelpers';
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
      <div className={`relative mx-auto stack-section px-4 py-6 sm:px-6 lg:px-8 ${containerClassName}`}>
        <div className="stack-inline justify-between">
          {onBack ? (
            <button
              type="button"
              onClick={onBack}
              className={routeLinkCtaClasses.neutral}
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              {backLabel}
            </button>
          ) : (
            <Link
              href={backHref ?? '/'}
              className={routeLinkCtaClasses.neutral}
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              {backLabel}
            </Link>
          )}
          {actions}
        </div>

        <GlassCard className="overflow-hidden rounded-[2rem] border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(248,244,238,0.72))] p-6 shadow-[0_22px_80px_rgba(63,44,26,0.08)] md:p-8">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px] xl:items-end">
            <div className="stack-block">
              <p className="type-micro uppercase text-primary/72">{eyebrow}</p>
              <h1 className="max-w-4xl type-h1 text-card-foreground">
                {title}
              </h1>
              <p className="max-w-3xl type-body-muted text-muted-foreground">
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

type DeckCollectionTileProps = {
  deck: DeckMeta;
  href: string;
  shortHook: string;
  progressLabel: string;
  progressWidth: number;
  emphasis?: 'feature' | 'standard';
  loading?: boolean;
};

export function DeckCollectionTile({
  deck,
  href,
  shortHook,
  progressLabel,
  progressWidth,
  emphasis = 'standard',
  loading = false,
}: DeckCollectionTileProps) {
  const isFeature = emphasis === 'feature';

  return (
    <Link href={href} prefetch className="group focus-visible:outline-none">
      <article
        className={`relative overflow-hidden rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] shadow-soft transition-all duration-haven ease-haven hover:-translate-y-1 hover:shadow-lift focus-visible:ring-2 focus-visible:ring-ring${
          isFeature ? ' ring-1 ring-primary/10' : ''
        }`}
      >
        {/* Deck color accent strip */}
        <div className={`h-1.5 w-full bg-gradient-to-r ${deck.color}`} aria-hidden />

        <div className={isFeature ? 'space-y-4 p-6' : 'space-y-4 p-5'}>
          {/* Icon + Title + Hook */}
          <div className="flex items-start gap-3.5">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/55 bg-white/74 shadow-soft" aria-hidden>
              <deck.Icon className={`h-5 w-5 ${deck.iconColor}`} strokeWidth={2.2} />
            </span>
            <div className="min-w-0">
              <h3 className="font-art text-lg leading-tight text-card-foreground">
                {deck.title}
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground line-clamp-2">
                {shortHook}
              </p>
            </div>
          </div>

          {/* Progress */}
          {loading ? (
            <div className="space-y-2.5">
              <div className="h-1.5 w-full rounded-full bg-muted/70 animate-pulse" aria-hidden />
              <div className="h-4 w-20 rounded-full bg-muted/50 animate-pulse" aria-hidden />
            </div>
          ) : (
            <div className="space-y-2">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/50">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${deck.color} transition-all duration-haven ease-haven`}
                  style={{ width: `${Math.max(0, Math.min(100, progressWidth))}%` }}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs tabular-nums text-muted-foreground">{progressLabel}</span>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-card-foreground/60 transition-colors duration-haven group-hover:text-card-foreground">
                  打開
                  <ChevronRight className="h-3.5 w-3.5 transition-transform duration-haven ease-haven group-hover:translate-x-0.5" aria-hidden />
                </span>
              </div>
            </div>
          )}
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
          <div className="stack-block">
            <p className="type-micro uppercase text-primary/70">{eyebrow}</p>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
            <p className="max-w-2xl type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>
        {children}
        {actionLabel
          ? actionHref ? (
              <Link
                href={actionHref}
                className={routeLinkCtaClasses.primary}
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
      <div className="stack-section">
        <div className="stack-block">
          <div className="flex flex-wrap items-center gap-3">
            <p className="type-micro uppercase text-primary/70">{eyebrow}</p>
            {badge ? (
              <Badge variant="metadata" size="sm" className="bg-white/74 text-card-foreground shadow-soft">
                {badge}
              </Badge>
            ) : null}
          </div>
          <h2 className="type-h2 text-card-foreground">
            {title}
          </h2>
          <p className="max-w-3xl type-body-muted text-muted-foreground">
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
      <div className="stack-section p-6 md:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="stack-block">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="metadata" size="sm" className="bg-white/72 text-primary/72">
                {deckTitle}
              </Badge>
              <Badge variant="status" size="sm" className={depth.badgeClass}>
                深度 {depthLevel} · {depth.label}
              </Badge>
            </div>
            <h3 className="max-w-3xl type-h3 text-card-foreground">
              {entry.card_question}
            </h3>
          </div>
          <div className="stack-block text-right">
            <div className="type-micro uppercase text-muted-foreground">解鎖日期</div>
            <div className="type-caption tabular-nums text-card-foreground">
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
            <p className="type-micro uppercase text-primary/72">我的回應</p>
            <p className="mt-3 type-body text-card-foreground">{entry.my_answer}</p>
          </section>
          <section className="rounded-[1.5rem] border border-white/55 bg-white/74 p-5">
            <p className="type-micro uppercase text-muted-foreground">伴侶回應</p>
            <p className="mt-3 type-body text-card-foreground">{entry.partner_answer}</p>
          </section>
        </div>
      </div>
    </article>
  );
}
