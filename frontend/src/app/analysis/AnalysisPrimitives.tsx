'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  BarChart3,
  BellRing,
  HeartHandshake,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Target,
  Waves,
} from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import type { AnalysisUnderstandingBriefModel } from '@/lib/analysis-v2-understanding-brief';

type AnalysisTone = 'default' | 'strength' | 'attention' | 'quiet' | 'error';

const stateToneClasses: Record<AnalysisTone, string> = {
  default: 'border-white/56 bg-white/84',
  strength:
    'border-accent/18 bg-[linear-gradient(180deg,rgba(250,253,250,0.96),rgba(239,245,238,0.93))]',
  attention:
    'border-primary/16 bg-[linear-gradient(180deg,rgba(255,251,246,0.96),rgba(246,238,229,0.93))]',
  quiet: 'border-primary/12 bg-white/80',
  error:
    'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,250,248,0.96),rgba(248,240,236,0.94))]',
};

function toneBadgeVariant(tone: AnalysisTone) {
  if (tone === 'strength') return 'success';
  if (tone === 'attention') return 'warning';
  if (tone === 'error') return 'destructive';
  return 'metadata';
}

function toneIcon(tone: AnalysisTone) {
  if (tone === 'strength') return <Sparkles className="h-[18px] w-[18px]" aria-hidden />;
  if (tone === 'attention') return <Target className="h-[18px] w-[18px]" aria-hidden />;
  if (tone === 'error') return <BellRing className="h-[18px] w-[18px]" aria-hidden />;
  return <Lightbulb className="h-[18px] w-[18px]" aria-hidden />;
}

export function AnalysisShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fbf7f1_0%,#f4ede4_50%,#ece3d7_100%)]">
      <Sidebar />

      <main className="relative min-h-screen overflow-hidden pt-14 md:ml-64 md:pt-0">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.16),transparent_26%),radial-gradient(circle_at_82%_12%,rgba(220,229,233,0.46),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.24),transparent_36%)]"
          aria-hidden
        />
        <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-26" aria-hidden />
        <div className="pointer-events-none absolute -left-10 top-20 h-72 w-72 rounded-full bg-primary/7 blur-hero-orb" aria-hidden />
        <div className="pointer-events-none absolute right-[-4rem] top-28 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />

        <div className="relative z-10 mx-auto max-w-[1560px] space-y-[clamp(1.5rem,3vw,2.75rem)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}

export function AnalysisCover({
  eyebrow,
  title,
  description,
  pulse,
  actions,
  highlights,
  featured,
  aside,
}: {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  actions?: ReactNode;
  highlights?: ReactNode;
  featured: ReactNode;
  aside: ReactNode;
}) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/56 bg-[linear-gradient(165deg,rgba(255,252,248,0.96),rgba(244,238,229,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.78),transparent_34%),radial-gradient(circle_at_82%_14%,rgba(255,255,255,0.34),transparent_22%)]"
        aria-hidden
      />
      <div className="pointer-events-none absolute right-[-3rem] top-[-3rem] h-72 w-72 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-4rem] left-[-2rem] h-64 w-64 rounded-full bg-accent/8 blur-hero-orb-sm" aria-hidden />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] xl:gap-8">
        <div className="space-y-6">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="metadata" size="md" className="border-white/56 bg-white/76 text-primary/82 shadow-soft">
                Analysis
              </Badge>
              <p className="type-micro uppercase text-primary/82">{eyebrow}</p>
            </div>

            <div className="space-y-3">
              <h1 className="max-w-[56rem] type-h1 text-card-foreground">{title}</h1>
              <p className="max-w-[46rem] type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.9rem] border border-white/56 bg-white/74 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <HeartHandshake className="h-4 w-4" aria-hidden />
            </span>
            <p className="type-body-muted text-card-foreground">{pulse}</p>
          </div>

          {highlights}
          {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
        </div>

        <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
          <div>{featured}</div>
          <div className="space-y-4">{aside}</div>
        </div>
      </div>
    </section>
  );
}

export function AnalysisOverviewCard({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.25rem] border-white/54 bg-white/80 p-5 md:p-6">
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

export function AnalysisPulseCard({
  score,
  label,
  summary,
  periodLabel,
  metricRows,
  footer,
}: {
  score: number | null;
  label: string;
  summary: string;
  periodLabel: string;
  metricRows?: ReactNode;
  footer?: ReactNode;
}) {
  const normalizedScore = typeof score === 'number' ? Math.max(0, Math.min(100, score)) : null;

  return (
    <GlassCard className="overflow-hidden rounded-[2.8rem] border-white/56 bg-[linear-gradient(165deg,rgba(255,253,249,0.96),rgba(243,237,228,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8">
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <Badge variant="metadata" size="sm" className="border-white/54 bg-white/74">
              Relationship Read
            </Badge>
            <div className="space-y-2">
              <h2 className="type-h2 text-card-foreground">{label}</h2>
              <p className="max-w-3xl type-body-muted text-card-foreground/84">{summary}</p>
            </div>
          </div>

          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[1.65rem] border border-white/60 bg-white/78 text-primary shadow-soft">
            <BarChart3 className="h-5 w-5" aria-hidden />
          </span>
        </div>

        <div className="grid gap-5 md:grid-cols-[180px_minmax(0,1fr)] md:items-end">
          <div className="space-y-2">
            <div className="flex items-end gap-3">
              <span className="text-[clamp(3.25rem,7vw,5rem)] font-semibold leading-none tracking-tight text-card-foreground tabular-nums">
                {normalizedScore ?? '—'}
              </span>
              <span className="pb-2 type-caption uppercase tracking-[0.18em] text-muted-foreground">
                pulse
              </span>
            </div>
            <p className="type-caption text-muted-foreground">{periodLabel}</p>
          </div>

          <div className="space-y-4">
            <div className="h-3 overflow-hidden rounded-full bg-white/60 shadow-glass-inset">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,rgba(182,142,85,0.28),rgba(182,142,85,0.92))]"
                style={{ width: `${normalizedScore ?? 0}%` }}
              />
            </div>
            {metricRows}
          </div>
        </div>

        {footer}
      </div>
    </GlassCard>
  );
}

export function AnalysisUnderstandingBrief({
  model,
  onSelectEvidence,
}: {
  model: AnalysisUnderstandingBriefModel;
  onSelectEvidence: (evidenceId: string) => void;
}) {
  return (
    <section
      data-testid="analysis-v2-brief"
      className="overflow-hidden rounded-[2.6rem] border border-white/56 bg-[linear-gradient(165deg,rgba(255,253,249,0.94),rgba(243,237,228,0.88))] p-5 shadow-lift backdrop-blur-xl md:p-6"
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="metadata" size="sm" className="border-white/54 bg-white/72">
                Analysis V2
              </Badge>
              <p className="type-micro uppercase text-primary/80">Understanding Brief</p>
            </div>
            <h2 className="type-h3 text-card-foreground">{model.title}</h2>
            <p className="type-body-muted text-muted-foreground">{model.description}</p>
          </div>
          <div className="max-w-sm rounded-[1.6rem] border border-white/56 bg-white/72 p-4 shadow-soft">
            <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Grounding</p>
            <p className="mt-2 type-body-muted text-card-foreground">{model.sourceNote}</p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-4">
          {model.cards.map((card) => (
            <GlassCard
              key={card.key}
              data-testid={`analysis-v2-brief-card-${card.key}`}
              className={cn(
                'overflow-hidden rounded-[2rem] p-5 shadow-soft backdrop-blur-md',
                stateToneClasses[card.tone],
              )}
            >
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <span
                    className={cn(
                      'mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-[1.1rem] border shadow-soft',
                      card.tone === 'attention'
                        ? 'border-primary/18 bg-primary/10 text-primary'
                        : card.tone === 'strength'
                          ? 'border-accent/18 bg-accent/10 text-card-foreground'
                          : 'border-white/56 bg-white/72 text-primary',
                    )}
                  >
                    {toneIcon(card.tone)}
                  </span>
                  <div className="min-w-0 space-y-2">
                    <p className="type-micro uppercase text-primary/76">{card.question}</p>
                    <h3 className="type-section-title text-card-foreground">{card.title}</h3>
                    <p className="type-body-muted text-muted-foreground">{card.description}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2" aria-label={`${card.question} 的依據來源`}>
                  {card.sources.length ? (
                    card.sources.map((source) => (
                      <Badge
                        key={source}
                        variant="outline"
                        size="sm"
                        className="border-white/54 bg-white/72"
                      >
                        {source}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="metadata" size="sm" className="border-white/54 bg-white/72">
                      等待更多來源
                    </Badge>
                  )}
                </div>

                {card.action.evidenceId ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-full"
                    onClick={() => onSelectEvidence(card.action.evidenceId as string)}
                  >
                    {card.action.label}
                  </Button>
                ) : card.action.href ? (
                  <AnalysisLinkAction href={card.action.href} label={card.action.label} />
                ) : null}
              </div>
            </GlassCard>
          ))}
        </div>
      </div>
    </section>
  );
}

export function AnalysisSection({
  eyebrow,
  title,
  description,
  badge,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  badge?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
          <div className="space-y-1">
            <h2 className="type-h3 text-card-foreground">{title}</h2>
            <p className="type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>
        {badge}
      </div>
      {children}
    </section>
  );
}

export function AnalysisEvidenceStudio({
  eyebrow,
  title,
  description,
  lenses,
  activeLensId,
  onSelectLens,
  panel,
}: {
  eyebrow: string;
  title: string;
  description: string;
  lenses: Array<{
    id: string;
    tone?: AnalysisTone;
    eyebrow: string;
    title: string;
    summary: string;
    meta?: string;
  }>;
  activeLensId: string;
  onSelectLens: (lensId: string) => void;
  panel: ReactNode;
}) {
  return (
    <section id="analysis-evidence" className="space-y-4">
      <div className="space-y-2">
        <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
        <div className="space-y-1">
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
        <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/56 bg-white/78 p-4 shadow-soft backdrop-blur-md md:p-5">
          <div className="space-y-3">
            {lenses.map((lens) => {
              const active = activeLensId === lens.id;
              return (
                <button
                  key={lens.id}
                  type="button"
                  onClick={() => onSelectLens(lens.id)}
                  aria-pressed={active}
                  className={cn(
                    'w-full rounded-[1.6rem] border px-4 py-4 text-left transition-all duration-haven ease-haven focus-ring-premium',
                    active
                      ? 'border-primary/24 bg-primary/10 shadow-soft'
                      : 'border-white/56 bg-white/72 hover:-translate-y-0.5 hover:bg-white/84 hover:shadow-soft',
                  )}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={cn(
                        'mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-[1rem] border shadow-soft',
                        lens.tone === 'attention'
                          ? 'border-primary/18 bg-primary/10 text-primary'
                          : lens.tone === 'strength'
                            ? 'border-accent/18 bg-accent/10 text-card-foreground'
                            : 'border-white/56 bg-white/72 text-primary',
                      )}
                    >
                      {toneIcon(lens.tone ?? 'default')}
                    </span>
                    <div className="min-w-0 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="type-micro uppercase text-primary/76">{lens.eyebrow}</p>
                        <Badge variant={toneBadgeVariant(lens.tone ?? 'default')} size="sm">
                          {lens.tone === 'strength'
                            ? 'Strength'
                            : lens.tone === 'attention'
                              ? 'Attention'
                              : 'Lens'}
                        </Badge>
                      </div>
                      <h3 className="type-section-title text-card-foreground">{lens.title}</h3>
                      <p className="type-body-muted text-muted-foreground">{lens.summary}</p>
                      {lens.meta ? <p className="type-caption text-card-foreground/72">{lens.meta}</p> : null}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </GlassCard>

        <div>{panel}</div>
      </div>
    </section>
  );
}

export function AnalysisSignalCard({
  tone = 'default',
  eyebrow,
  title,
  description,
  meta,
  actions,
}: {
  tone?: AnalysisTone;
  eyebrow: string;
  title: string;
  description: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <GlassCard className={cn('overflow-hidden rounded-[2rem] p-5 shadow-soft backdrop-blur-md md:p-6', stateToneClasses[tone])}>
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-[1.2rem] border shadow-soft',
              tone === 'attention'
                ? 'border-primary/18 bg-primary/10 text-primary'
                : tone === 'strength'
                  ? 'border-accent/18 bg-accent/10 text-card-foreground'
                  : tone === 'error'
                    ? 'border-destructive/18 bg-destructive/10 text-destructive'
                    : 'border-white/56 bg-white/72 text-primary',
            )}
          >
            {toneIcon(tone)}
          </span>
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <p className="type-micro uppercase text-primary/76">{eyebrow}</p>
              <Badge variant={toneBadgeVariant(tone)} size="sm">
                {tone === 'strength'
                  ? 'Strength'
                  : tone === 'attention'
                    ? 'Attention'
                    : tone === 'error'
                      ? 'Source'
                      : 'Signal'}
              </Badge>
            </div>
            <h3 className="type-section-title text-card-foreground">{title}</h3>
            <p className="type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>
        {meta}
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </GlassCard>
  );
}

export function AnalysisEvidencePanel({
  tone = 'default',
  eyebrow,
  title,
  description,
  meta,
  summary,
  stats,
  children,
  actions,
}: {
  tone?: AnalysisTone;
  eyebrow: string;
  title: string;
  description: string;
  meta?: string;
  summary?: string;
  stats?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <GlassCard
      data-testid="analysis-evidence-panel"
      className={cn('overflow-hidden rounded-[2.4rem] p-5 shadow-lift backdrop-blur-xl md:p-6', stateToneClasses[tone])}
    >
      <div className="space-y-5">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-[1.2rem] border shadow-soft',
              tone === 'attention'
                ? 'border-primary/18 bg-primary/10 text-primary'
                : tone === 'strength'
                  ? 'border-accent/18 bg-accent/10 text-card-foreground'
                  : 'border-white/56 bg-white/72 text-primary',
            )}
          >
            {toneIcon(tone)}
          </span>
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <p className="type-micro uppercase text-primary/76">{eyebrow}</p>
              <Badge variant={toneBadgeVariant(tone)} size="sm">
                {tone === 'strength'
                  ? 'Strength'
                  : tone === 'attention'
                    ? 'Attention'
                    : 'Evidence'}
              </Badge>
            </div>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
            <p className="type-body-muted text-muted-foreground">{description}</p>
            {meta ? <p className="type-caption text-card-foreground/72">{meta}</p> : null}
          </div>
        </div>

        {summary ? (
          <div className="rounded-[1.6rem] border border-white/56 bg-white/72 p-4 shadow-soft">
            <p className="type-caption uppercase tracking-[0.18em] text-primary/76">How Haven Reads This</p>
            <p className="mt-2 type-body-muted text-card-foreground">{summary}</p>
          </div>
        ) : null}

        {stats}
        {children}
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </GlassCard>
  );
}

export function AnalysisEvidenceEntryCard({
  eyebrow,
  title,
  description,
  meta,
  badges,
}: {
  eyebrow: string;
  title: string;
  description: string;
  meta?: string;
  badges?: string[];
}) {
  return (
    <div className="rounded-[1.6rem] border border-white/56 bg-white/72 p-4 shadow-soft">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="type-micro uppercase text-primary/76">{eyebrow}</p>
          {meta ? <span className="type-caption text-muted-foreground">{meta}</span> : null}
        </div>
        <div className="space-y-2">
          <h4 className="text-base font-semibold text-card-foreground">{title}</h4>
          <p className="type-body-muted text-card-foreground">{description}</p>
        </div>
        {badges?.length ? (
          <div className="flex flex-wrap gap-2">
            {badges.map((badge) => (
              <Badge key={badge} variant="outline" size="sm" className="border-white/54 bg-white/72">
                {badge}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function AnalysisReflectionCard({
  eyebrow,
  title,
  description,
  href,
  actionLabel,
}: {
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  actionLabel: string;
}) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.1rem] border-white/54 bg-white/80 p-5 shadow-soft backdrop-blur-md md:p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/76">{eyebrow}</p>
          <h3 className="type-section-title text-card-foreground">{title}</h3>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        <AnalysisLinkAction href={href} label={actionLabel} />
      </div>
    </GlassCard>
  );
}

export function AnalysisLinkAction({
  href,
  label,
}: {
  href: string;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium"
    >
      {label}
      <ArrowRight className="h-4 w-4" aria-hidden />
    </Link>
  );
}

export function AnalysisStatePanel({
  tone = 'default',
  eyebrow,
  title,
  description,
  actions,
}: {
  tone?: AnalysisTone;
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <GlassCard className={cn('overflow-hidden rounded-[2.3rem] p-5 shadow-soft backdrop-blur-xl md:p-6', stateToneClasses[tone])}>
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-[1.2rem] border shadow-soft',
              tone === 'error'
                ? 'border-destructive/18 bg-destructive/10 text-destructive'
                : 'border-white/56 bg-white/72 text-primary',
            )}
          >
            {tone === 'error' ? (
              <BellRing className="h-[18px] w-[18px]" aria-hidden />
            ) : (
              <Waves className="h-[18px] w-[18px]" aria-hidden />
            )}
          </span>
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/76">{eyebrow}</p>
            <h2 className="type-h3 text-card-foreground">{title}</h2>
            <p className="type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </GlassCard>
  );
}

export function AnalysisDiagnosticsCard({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <AnalysisOverviewCard eyebrow={eyebrow} title={title} description={description}>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </AnalysisOverviewCard>
  );
}

export function AnalysisRefreshButton({
  loading = false,
  onClick,
  label = '重新整理洞察',
  variant = 'outline',
}: {
  loading?: boolean;
  onClick: () => void;
  label?: string;
  variant?: 'primary' | 'outline';
}) {
  return (
    <Button
      size="lg"
      variant={variant === 'primary' ? 'primary' : 'outline'}
      loading={loading}
      leftIcon={!loading ? <RefreshCw className="h-4 w-4" aria-hidden /> : undefined}
      onClick={onClick}
    >
      {label}
    </Button>
  );
}
