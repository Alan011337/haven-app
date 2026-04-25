'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, BookOpen, Check, CheckCircle2, Gift, Heart, MessageCircle, Sparkles, X } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import {
  buildCompassSuggestionEvidenceArtifactHref,
  compassFieldValuesEqual,
  normalizeCompassFieldValue,
} from '@/lib/compass-suggestion-utils';
import { parseSharedFutureNotes } from '@/lib/shared-future-read-model';
import {
  buildSavedSharedFuturePreviewTitles,
  filterSharedFutureEvidence,
  sharedFutureEvidenceKindLabel,
} from '@/lib/shared-future-suggestion-utils';
import { formatCompassChangedAt } from '@/features/love-map/relationship-compass-revision';
import type { RelationshipEvolutionEvent } from '@/features/love-map/relationship-system-evolution';
import type {
  RelationshipWeeklyReviewRitualModel,
  WeeklyReviewPromptKey,
} from '@/features/love-map/relationship-weekly-review';
import { cn } from '@/lib/utils';
import type {
  LoveMapRelationshipCompassPublic,
  LoveMapWeeklyReviewAnswersPublic,
  RelationshipKnowledgeSuggestionEvidencePublic,
} from '@/services/api-client';

type StateTone = 'default' | 'quiet' | 'error';

const stateToneClasses: Record<StateTone, string> = {
  default: 'border-white/54 bg-white/84',
  quiet: 'border-primary/12 bg-white/76',
  error: 'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,251,249,0.96),rgba(248,240,236,0.94))]',
};

function StoryKindIcon({ kind }: { kind: 'card' | 'appreciation' | 'journal' }) {
  if (kind === 'card') {
    return <MessageCircle className="h-4 w-4" aria-hidden />;
  }
  if (kind === 'journal') {
    return <BookOpen className="h-4 w-4" aria-hidden />;
  }
  return <Heart className="h-4 w-4" aria-hidden />;
}

export function LoveMapShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_26%),radial-gradient(circle_at_88%_10%,rgba(233,239,233,0.5),transparent_28%),linear-gradient(180deg,#fcfaf6_0%,#f6f0e9_52%,#f1ebe2_100%)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-30" aria-hidden />
      <div className="pointer-events-none absolute -left-12 top-20 h-72 w-72 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />

      <div className="relative z-10 mx-auto max-w-[1540px] space-y-[clamp(1.5rem,3vw,2.75rem)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-white/54 bg-white/76 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
              aria-label="返回首頁"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              回首頁
            </Link>
            <Link
              href="/blueprint"
              className="inline-flex items-center gap-2 rounded-full border border-white/52 bg-white/64 px-4 py-2.5 text-sm font-medium text-card-foreground/88 shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-white/74 hover:text-card-foreground hover:shadow-lift focus-ring-premium"
            >
              Blueprint 工作台
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>

          <Badge variant="metadata" size="md" className="border-white/50 bg-white/72 text-primary/78 shadow-soft">
            Relationship System
          </Badge>
        </div>

        {children}
      </div>
    </div>
  );
}

interface LoveMapSystemCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  primaryHref: string;
  primaryLabel: string;
  highlights: ReactNode;
  aside: ReactNode;
  dataTestId?: string;
}

export function LoveMapSystemCover({
  eyebrow,
  title,
  description,
  pulse,
  primaryHref,
  primaryLabel,
  highlights,
  aside,
  dataTestId,
}: LoveMapSystemCoverProps) {
  return (
    <section
      className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.94),rgba(246,239,230,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10"
      data-testid={dataTestId}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.72),transparent_36%),radial-gradient(circle_at_86%_12%,rgba(255,255,255,0.34),transparent_22%)]" aria-hidden />
      <div className="pointer-events-none absolute right-[-4rem] top-[-2rem] h-72 w-72 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-3rem] left-[-1rem] h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_370px]">
        <div className="space-y-6">
          <div className="space-y-4">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h1 className="max-w-[56rem] type-h1 text-card-foreground">{title}</h1>
              <p className="max-w-[48rem] type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.85rem] border border-white/56 bg-white/70 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Heart className="h-4 w-4" aria-hidden />
            </span>
            <p className="type-body-muted text-card-foreground">{pulse}</p>
          </div>

          {highlights}

          <a
            href={primaryHref}
            className="inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium"
          >
            {primaryLabel}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </a>
        </div>

        <div className="space-y-4">{aside}</div>
      </div>
    </section>
  );
}

type LoveMapSystemStatusTone = 'saved' | 'pending' | 'evolving';

const systemStatusToneClasses: Record<LoveMapSystemStatusTone, string> = {
  saved: 'border-primary/12 bg-primary/8',
  pending: 'border-accent/18 bg-accent/10',
  evolving: 'border-white/58 bg-white/74',
};

interface LoveMapSystemStatusCardProps {
  eyebrow: string;
  title: string;
  value: string;
  description: string;
  tone: LoveMapSystemStatusTone;
  dataTestId?: string;
  /** When set, the entire card becomes an in-page anchor (e.g. `#evolution`). */
  href?: string;
}

export function LoveMapSystemStatusCard({
  eyebrow,
  title,
  value,
  description,
  tone,
  dataTestId,
  href,
}: LoveMapSystemStatusCardProps) {
  const shellClass = cn(
    'rounded-[1.85rem] border px-4 py-4 shadow-soft backdrop-blur-md',
    systemStatusToneClasses[tone],
    href &&
      'block cursor-pointer transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium',
  );

  const inner = (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="type-micro uppercase text-primary/78">{eyebrow}</p>
          <p className="type-section-title text-card-foreground">{title}</p>
        </div>
        <Badge variant={tone === 'pending' ? 'status' : tone === 'saved' ? 'success' : 'metadata'} size="sm">
          {value}
        </Badge>
      </div>
      <p className="mt-3 type-caption text-muted-foreground">{description}</p>
    </>
  );

  if (href) {
    return (
      <a href={href} className={shellClass} data-testid={dataTestId}>
        {inner}
      </a>
    );
  }

  return (
    <div className={shellClass} data-testid={dataTestId}>
      {inner}
    </div>
  );
}

export function LoveMapRelationshipEvolutionPanel({ events }: { events: RelationshipEvolutionEvent[] }) {
  if (events.length === 0) {
    return (
      <div
        className="rounded-[2rem] border border-white/54 bg-white/72 p-6 shadow-soft backdrop-blur-xl md:p-8"
        data-testid="relationship-evolution-empty"
      >
        <p className="type-micro uppercase text-primary/80">關係如何演進</p>
        <p className="mt-2 type-section-title text-card-foreground">還沒有已保存的演進紀錄</p>
        <p className="mt-3 max-w-[40rem] type-body-muted text-muted-foreground">
          當你們在 Identity 或 Heart 留下更新後，這裡會依時間整理成可以一起回看的脈絡——不取代各區塊的細節，只是幫你們看見最近一起發生了什麼。
        </p>
      </div>
    );
  }

  return (
    <div
      className="space-y-5 rounded-[2rem] border border-white/54 bg-white/72 p-6 shadow-soft backdrop-blur-xl md:p-8"
      data-testid="relationship-evolution-timeline"
    >
      <div className="space-y-2">
        <p className="type-micro uppercase text-primary/80">關係如何演進</p>
        <h2 className="type-h2 text-card-foreground">最近一起留下的變化</h2>
        <p className="max-w-[48rem] type-body-muted text-muted-foreground">
          只收錄你們已保存的 Identity 與 Heart 更新；點「查看來源」可回到該則歷史列的完整脈絡。
        </p>
      </div>

      <ul className="space-y-3">
        {events.map((event) => (
          <li
            key={event.id}
            className="scroll-mt-24 rounded-[1.35rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
            data-testid={event.testId}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="metadata" size="sm">
                    {event.domainLabel}
                  </Badge>
                  <Badge variant="status" size="sm">
                    {event.sourceLabel}
                  </Badge>
                </div>
                <p className="type-section-title text-card-foreground">{event.title}</p>
                <p className="type-caption text-muted-foreground">{event.summary}</p>
                <p className="type-caption text-muted-foreground">
                  {event.actorLabel}
                  {event.occurredAt ? ` · ${formatCompassChangedAt(event.occurredAt)}` : ''}
                </p>
                {event.revisionNote ? (
                  <p className="border-l-2 border-primary/20 pl-3 type-caption italic text-card-foreground/80">
                    {event.revisionNote}
                  </p>
                ) : null}
              </div>
            </div>
            <div className="mt-3">
              <a
                href={event.sourceHref}
                className="type-caption font-medium text-primary/85 underline-offset-2 transition-colors duration-haven ease-haven hover:text-primary hover:underline focus-ring-premium"
              >
                查看來源
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function LoveMapWeeklyReviewRitualPanel({
  model,
  myDraft,
  partnerAnswers,
  myUpdatedAtLabel,
  partnerUpdatedAtLabel,
  saving,
  error,
  onChange,
  onSave,
}: {
  model: RelationshipWeeklyReviewRitualModel;
  myDraft: Record<WeeklyReviewPromptKey, string>;
  partnerAnswers: LoveMapWeeklyReviewAnswersPublic;
  myUpdatedAtLabel: string | null;
  partnerUpdatedAtLabel: string | null;
  saving: boolean;
  error: string | null;
  onChange: (key: WeeklyReviewPromptKey, value: string) => void;
  onSave: () => void;
}) {
  return (
    <div
      className="rounded-[2rem] border border-white/54 bg-white/72 p-6 shadow-soft backdrop-blur-xl md:p-8"
      data-testid="relationship-weekly-review"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">Weekly Relationship Review</p>
          <h2 className="type-h2 text-card-foreground">{model.title}</h2>
          <p className="max-w-[52rem] type-body-muted text-muted-foreground">{model.subtitle}</p>
          <p className="max-w-[52rem] type-caption text-muted-foreground">{model.trustLine}</p>
        </div>
        <Badge variant="metadata" size="sm" className="border-white/54 bg-white/78 text-primary/78 shadow-soft">
          {model.weekLabel}
        </Badge>
      </div>

      {model.cues.length > 0 ? (
        <div className="mt-5 space-y-2">
          <p className="type-micro uppercase text-primary/80">回看線索</p>
          <div className="flex flex-wrap gap-2">
            {model.cues.map((cue) => (
              <a
                key={cue.key}
                href={cue.href}
                className="inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-white/88 hover:shadow-lift focus-ring-premium"
                data-testid={cue.testId}
              >
                <span className="text-primary/85">{cue.label}</span>
                <span className="text-muted-foreground/90">{cue.description}</span>
              </a>
            ))}
          </div>
          {model.emptyNudge ? (
            <p className="type-caption text-muted-foreground" data-testid="weekly-review-empty-nudge">
              {model.emptyNudge}
            </p>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <div className="mt-5 rounded-[1.35rem] border border-destructive/18 bg-[linear-gradient(180deg,rgba(255,251,249,0.96),rgba(248,240,236,0.94))] px-4 py-3 shadow-soft">
          <p className="type-caption text-card-foreground/90">{error}</p>
        </div>
      ) : null}

      <div className="mt-6 space-y-4">
        {model.prompts.map((prompt) => {
          const partnerValue =
            partnerAnswers[prompt.key] && partnerAnswers[prompt.key]?.trim()
              ? partnerAnswers[prompt.key]
              : null;
          return (
            <div
              key={prompt.key}
              className="rounded-[1.6rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
              data-testid={`weekly-review-prompt-${prompt.key}`}
            >
              <div className="space-y-1">
                <p className="type-section-title text-card-foreground">{prompt.title}</p>
                <p className="type-caption text-muted-foreground">{prompt.helperText}</p>
              </div>

              <div className="mt-4 space-y-3">
                <div className="rounded-[1.25rem] border border-primary/12 bg-primary/8 px-4 py-4">
                  <p className="type-micro uppercase text-primary/80">我留下的</p>
                  <Textarea
                    value={myDraft[prompt.key]}
                    onChange={(e) => onChange(prompt.key, e.target.value)}
                    placeholder={prompt.placeholder}
                    className="mt-3 min-h-[5.5rem] resize-y rounded-[1.1rem]"
                  />
                  {myUpdatedAtLabel ? (
                    <p className="mt-2 type-micro text-muted-foreground/80">上次更新：{myUpdatedAtLabel}</p>
                  ) : (
                    <p className="mt-2 type-micro text-muted-foreground/80">尚未保存</p>
                  )}
                </div>

                <div className="rounded-[1.25rem] border border-white/58 bg-white/78 px-4 py-4">
                  <p className="type-micro uppercase text-muted-foreground">伴侶留下的</p>
                  {partnerValue ? (
                    <>
                      <p className="mt-2 border-l-2 border-primary/18 pl-3 type-caption italic text-card-foreground/80">
                        {partnerValue}
                      </p>
                      {partnerUpdatedAtLabel ? (
                        <p className="mt-2 type-micro text-muted-foreground/80">
                          上次更新：{partnerUpdatedAtLabel}
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <p className="mt-2 type-caption text-muted-foreground">伴侶這週還沒有留下這一題。</p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <p className="type-caption text-muted-foreground">
          保存只會寫入你這一半的復盤文字；不會自動改寫 Compass / Heart / Future，也不會替你們做結論。
        </p>
        <Button
          loading={saving}
          disabled={saving}
          leftIcon={<Check className="h-4 w-4" aria-hidden />}
          onClick={onSave}
          data-testid="weekly-review-save"
        >
          {saving ? '正在保存本週復盤…' : '保存本週復盤'}
        </Button>
      </div>
    </div>
  );
}

interface LoveMapSystemSectionNavItem {
  key: string;
  label: string;
  description: string;
  href: string;
  statusLabel: string;
}

interface LoveMapSystemSectionNavProps {
  items: LoveMapSystemSectionNavItem[];
  nextAction: {
    label: string;
    description: string;
    href: string;
  };
}

function LoveMapNavLink({
  href,
  className,
  children,
  dataTestId,
}: {
  href: string;
  className: string;
  children: ReactNode;
  dataTestId?: string;
}) {
  if (href.startsWith('#')) {
    return (
      <a href={href} className={className} data-testid={dataTestId}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className} data-testid={dataTestId}>
      {children}
    </Link>
  );
}

export function LoveMapSystemSectionNav({
  items,
  nextAction,
}: LoveMapSystemSectionNavProps) {
  const itemClassName =
    'flex min-w-[12rem] flex-1 items-center justify-between gap-3 rounded-[1.35rem] border border-white/58 bg-white/72 px-4 py-3 text-left shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-white/84 hover:shadow-lift focus-ring-premium md:min-w-[13.5rem]';

  return (
    <section
      aria-label="Relationship System section navigation"
      className="rounded-[2rem] border border-white/54 bg-white/70 p-3 shadow-soft backdrop-blur-xl lg:sticky lg:top-4 lg:z-20"
      data-testid="relationship-system-section-nav"
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-stretch">
        <div className="flex flex-wrap gap-2 xl:flex-1">
          {items.map((item) => (
            <LoveMapNavLink
              key={item.key}
              href={item.href}
              className={itemClassName}
              dataTestId={`relationship-system-section-nav-${item.key}`}
            >
              <span className="min-w-0">
                <span className="block type-section-title text-card-foreground">{item.label}</span>
                <span className="mt-1 block type-caption text-muted-foreground">{item.description}</span>
              </span>
              <Badge variant={item.statusLabel === '待審核' ? 'status' : item.statusLabel === '已保存' ? 'success' : 'metadata'} size="sm">
                {item.statusLabel}
              </Badge>
            </LoveMapNavLink>
          ))}
        </div>

        <LoveMapNavLink
          href={nextAction.href}
          className="flex items-center justify-between gap-3 rounded-[1.35rem] border border-primary/18 bg-primary/10 px-4 py-3 shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium xl:w-[21rem]"
          dataTestId="relationship-system-next-action"
        >
          <span className="min-w-0">
            <span className="block type-micro uppercase text-primary/80">Next</span>
            <span className="mt-1 block type-section-title text-card-foreground">{nextAction.label}</span>
            <span className="mt-1 block type-caption text-muted-foreground">{nextAction.description}</span>
          </span>
          <ArrowRight className="h-4 w-4 shrink-0 text-primary" aria-hidden />
        </LoveMapNavLink>
      </div>
    </section>
  );
}

type LoveMapReviewFlowMode = 'pending' | 'complete' | 'continueNext';

interface LoveMapReviewFlowPanelProps {
  /**
   * - `pending`: there are pending Haven suggestions; show a CTA that jumps
   *   to the first pending card.
   * - `complete`: a paired couple has nothing to review; show a calm
   *   "you're all caught up" state with no CTA.
   * - `continueNext`: the user just handled a suggestion and another one
   *   remains; show a light inline CTA pointing to the next target.
   */
  mode: LoveMapReviewFlowMode;
  title: string;
  description: string;
  /**
   * CTA href. Typically an in-page anchor such as `#pending-review-compass`.
   * When omitted (or when the caller does not want a CTA on a given mode),
   * the panel renders as a calm copy-only surface.
   */
  ctaHref?: string;
  ctaLabel?: string;
  dataTestId?: string;
  /** Optional extra content rendered under the description (rare). */
  children?: ReactNode;
}

const reviewFlowModeClasses: Record<LoveMapReviewFlowMode, string> = {
  // Pending: warmer tone that subtly signals "something to do" without
  // feeling alarming. Mirrors the existing `pending` status card tone.
  pending: 'border-accent/18 bg-accent/10',
  // Complete: calm success tone, consistent with other "saved / done"
  // surfaces across Haven.
  complete: 'border-primary/12 bg-primary/8',
  // Continue next: lighter inline tone so it reads as "there's another one"
  // rather than dominating the recently-handled suggestion block.
  continueNext: 'border-white/58 bg-white/74',
};

const reviewFlowIconByMode: Record<LoveMapReviewFlowMode, ReactNode> = {
  pending: <Sparkles className="h-4 w-4 text-primary" aria-hidden />,
  complete: <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden />,
  continueNext: <ArrowRight className="h-4 w-4 text-primary" aria-hidden />,
};

export function LoveMapReviewFlowPanel({
  mode,
  title,
  description,
  ctaHref,
  ctaLabel,
  dataTestId,
  children,
}: LoveMapReviewFlowPanelProps) {
  const ctaClassName =
    'inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium';

  return (
    <div
      className={cn(
        'rounded-[1.85rem] border px-5 py-5 shadow-soft backdrop-blur-md md:px-6',
        reviewFlowModeClasses[mode],
      )}
      data-testid={dataTestId}
      data-review-flow-mode={mode}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/58 bg-white/72 shadow-soft">
            {reviewFlowIconByMode[mode]}
          </span>
          <div className="min-w-0 space-y-2">
            <p className="type-micro uppercase text-primary/80">Haven 建議 · 審核流</p>
            <p className="type-section-title text-card-foreground">{title}</p>
            <p className="type-caption text-muted-foreground">{description}</p>
            {children}
          </div>
        </div>

        {ctaHref && ctaLabel ? (
          <a
            href={ctaHref}
            className={ctaClassName}
            data-testid={dataTestId ? `${dataTestId}-cta` : undefined}
          >
            {ctaLabel}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </a>
        ) : null}
      </div>
    </div>
  );
}

interface LoveMapSnapshotCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}

export function LoveMapSnapshotCard({
  eyebrow,
  title,
  description,
  children,
}: LoveMapSnapshotCardProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.25rem] border-white/52 bg-white/80 p-5 md:p-6">
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

interface LoveMapSystemGuideProps {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}

export function LoveMapSystemGuide({
  eyebrow,
  title,
  description,
  children,
}: LoveMapSystemGuideProps) {
  return (
    <section aria-labelledby="relationship-system-guide-title" className="space-y-5">
      <div className="space-y-3">
        <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
        <div className="space-y-2">
          <h2 id="relationship-system-guide-title" className="type-h2 text-card-foreground">
            {title}
          </h2>
          <p className="max-w-[52rem] type-body-muted text-muted-foreground">{description}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">{children}</div>
    </section>
  );
}

type LoveMapGuideOwnershipTone = 'success' | 'metadata' | 'status';

interface LoveMapSystemGuideCardProps {
  eyebrow: string;
  title: string;
  ownershipLabel: string;
  ownershipTone?: LoveMapGuideOwnershipTone;
  metricLabel: string;
  metricValue: ReactNode;
  metricFootnote?: string;
  belongsHere: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref?: string;
  secondaryLabel?: string;
  dataTestId?: string;
}

export function LoveMapSystemGuideCard({
  eyebrow,
  title,
  ownershipLabel,
  ownershipTone = 'metadata',
  metricLabel,
  metricValue,
  metricFootnote,
  belongsHere,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
  dataTestId,
}: LoveMapSystemGuideCardProps) {
  const primaryActionClassName =
    'inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium';
  const secondaryActionClassName =
    'inline-flex items-center gap-2 rounded-full border border-white/58 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium';

  return (
    <GlassCard
      className="overflow-hidden rounded-[2.1rem] border-white/56 bg-white/80 p-5 shadow-lift backdrop-blur-md md:p-6"
      data-testid={dataTestId}
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
          </div>

          <Badge variant={ownershipTone} size="sm">
            {ownershipLabel}
          </Badge>
        </div>

        <div className="rounded-[1.55rem] border border-white/58 bg-white/74 px-4 py-4 shadow-soft">
          <p className="type-caption uppercase tracking-[0.18em] text-primary/72">{metricLabel}</p>
          <p className="mt-2 type-section-title text-card-foreground">{metricValue}</p>
          {metricFootnote ? <p className="mt-2 type-caption text-muted-foreground">{metricFootnote}</p> : null}
        </div>

        <div className="space-y-2">
          <p className="type-caption uppercase tracking-[0.18em] text-primary/72">這裡放什麼</p>
          <p className="type-body-muted text-muted-foreground">{belongsHere}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {primaryHref.startsWith('#') ? (
            <a
              href={primaryHref}
              className={primaryActionClassName}
              data-testid={dataTestId ? `${dataTestId}-primary-action` : undefined}
            >
              {primaryLabel}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </a>
          ) : (
            <Link
              href={primaryHref}
              className={primaryActionClassName}
              data-testid={dataTestId ? `${dataTestId}-primary-action` : undefined}
            >
              {primaryLabel}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          )}

          {secondaryHref && secondaryLabel ? (
            <Link
              href={secondaryHref}
              className={secondaryActionClassName}
              data-testid={dataTestId ? `${dataTestId}-secondary-action` : undefined}
            >
              {secondaryLabel}
            </Link>
          ) : null}
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapSectionProps {
  id?: string;
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
  children: ReactNode;
}

interface LoveMapKnowledgeBlockProps {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
  badge?: ReactNode;
  dataTestId?: string;
}

export function LoveMapKnowledgeBlock({
  eyebrow,
  title,
  description,
  children,
  footer,
  badge,
  dataTestId,
}: LoveMapKnowledgeBlockProps) {
  return (
    <GlassCard
      className="overflow-hidden rounded-[2.2rem] border-white/58 bg-white/82 p-5 shadow-lift backdrop-blur-md md:p-6"
      data-testid={dataTestId}
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
            <p className="max-w-2xl type-body-muted text-muted-foreground">{description}</p>
          </div>
          {badge}
        </div>

        {children}

        {footer}
      </div>
    </GlassCard>
  );
}

interface LoveMapEssentialFieldProps {
  label: string;
  value?: ReactNode;
  emptyLabel?: string;
  dataTestId?: string;
}

export function LoveMapEssentialField({
  label,
  value,
  emptyLabel = '尚未留下',
  dataTestId,
}: LoveMapEssentialFieldProps) {
  const hasValue =
    typeof value === 'string'
      ? value.trim().length > 0
      : value !== null && value !== undefined;

  return (
    <div
      className="rounded-[1.35rem] border border-white/60 bg-white/80 px-4 py-4 shadow-soft"
      data-testid={dataTestId}
    >
      <p className="type-micro uppercase text-primary/80">{label}</p>
      <p className="mt-2 type-body text-card-foreground">{hasValue ? value : emptyLabel}</p>
    </div>
  );
}

export function LoveMapSection({
  id,
  eyebrow,
  title,
  description,
  aside,
  children,
}: LoveMapSectionProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <GlassCard className="overflow-hidden rounded-[2.8rem] border-white/54 bg-[linear-gradient(180deg,rgba(255,253,249,0.94),rgba(245,238,229,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)] xl:gap-10">
          <div className="space-y-4 xl:sticky xl:top-24 xl:self-start">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h2 className="type-h2 text-card-foreground">{title}</h2>
              <p className="type-body-muted text-muted-foreground">{description}</p>
            </div>
            {aside}
          </div>
          <div className="space-y-5">{children}</div>
        </div>
      </GlassCard>
    </section>
  );
}

interface LoveMapStatePanelProps {
  eyebrow?: string;
  title: string;
  description: string;
  tone?: StateTone;
  actionLabel?: string;
  onAction?: () => void;
  dataTestId?: string;
}

export function LoveMapStatePanel({
  eyebrow,
  title,
  description,
  tone = 'default',
  actionLabel,
  onAction,
  dataTestId,
}: LoveMapStatePanelProps) {
  return (
    <GlassCard
      className={cn('overflow-hidden rounded-[2.2rem] p-6 shadow-soft backdrop-blur-md md:p-7', stateToneClasses[tone])}
      data-testid={dataTestId}
    >
      <div className="space-y-4">
        {eyebrow ? <p className="type-micro uppercase text-primary/80">{eyebrow}</p> : null}
        <div className="space-y-2">
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        {actionLabel && onAction ? (
          <Button variant="secondary" onClick={onAction} data-testid={dataTestId ? `${dataTestId}-action` : undefined}>
            {actionLabel}
          </Button>
        ) : null}
      </div>
    </GlassCard>
  );
}

interface LoveMapStoryMomentCardProps {
  kind: 'card' | 'appreciation' | 'journal';
  title: string;
  description: string;
  occurredAtLabel?: string | null;
  badges?: string[];
  whyText: string;
  href?: string | null;
}

export function LoveMapStoryMomentCard({
  kind,
  title,
  description,
  occurredAtLabel,
  badges = [],
  whyText,
  href,
}: LoveMapStoryMomentCardProps) {
  const card = (
    <GlassCard className={cn(
      "overflow-hidden rounded-[2.2rem] border-white/58 bg-white/82 p-5 shadow-lift backdrop-blur-md md:p-6",
      href && "transition-shadow duration-200 hover:shadow-card-hover",
    )}>
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/72 px-3 py-1.5 shadow-soft">
              <StoryKindIcon kind={kind} />
              <span className="type-micro uppercase text-primary/80">Story anchor</span>
            </div>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
            <p className="max-w-2xl type-body-muted text-muted-foreground">{description}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {occurredAtLabel ? <Badge variant="metadata" size="sm">{occurredAtLabel}</Badge> : null}
            {badges.map((badge) => (
              <Badge key={badge} variant="status" size="sm">
                {badge}
              </Badge>
            ))}
          </div>
        </div>

        <div className="rounded-[1.5rem] border border-primary/10 bg-primary/8 px-4 py-4">
          <p className="type-caption text-muted-foreground">Why this belongs in your story</p>
          <p className="mt-2 type-body text-card-foreground">{whyText}</p>
        </div>

        {href ? (
          <p className="type-caption text-primary/70">查看完整回憶 →</p>
        ) : null}
      </div>
    </GlassCard>
  );

  if (href) {
    return <Link href={href} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded-[2.2rem]">{card}</Link>;
  }
  return card;
}

interface LoveMapStoryCapsuleCardProps {
  summaryText: string;
  rangeLabel: string;
  journalsCount: number;
  cardsCount: number;
  appreciationsCount: number;
}

export function LoveMapStoryCapsuleCard({
  summaryText,
  rangeLabel,
  journalsCount,
  cardsCount,
  appreciationsCount,
}: LoveMapStoryCapsuleCardProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.35rem] border-white/58 bg-[linear-gradient(165deg,rgba(255,253,249,0.95),rgba(244,236,226,0.92))] p-5 shadow-lift backdrop-blur-md md:p-6">
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/72 px-3 py-1.5 shadow-soft">
              <Gift className="h-4 w-4 text-primary" aria-hidden />
              <span className="type-micro uppercase text-primary/80">Time Capsule echo</span>
            </div>
            <h3 className="type-h3 text-card-foreground">一年前，這些片段曾經真的發生過。</h3>
            <p className="max-w-2xl type-body-muted text-muted-foreground">{summaryText}</p>
          </div>

          <Badge variant="metadata" size="sm">{rangeLabel}</Badge>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-[1.45rem] border border-white/56 bg-white/74 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">Journals</p>
            <p className="mt-2 type-section-title text-card-foreground">{journalsCount}</p>
          </div>
          <div className="rounded-[1.45rem] border border-white/56 bg-white/74 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">Cards</p>
            <p className="mt-2 type-section-title text-card-foreground">{cardsCount}</p>
          </div>
          <div className="rounded-[1.45rem] border border-white/56 bg-white/74 px-4 py-4 shadow-soft">
            <p className="type-micro uppercase text-primary/80">Appreciations</p>
            <p className="mt-2 type-section-title text-card-foreground">{appreciationsCount}</p>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapReflectionStudioProps {
  eyebrow: string;
  title: string;
  description: string;
  textareaId: string;
  textareaLabel: string;
  value: string;
  onChange: (value: string) => void;
  onSave: () => void;
  saving: boolean;
  helperText: string;
  placeholder: string;
  lastUpdated?: string | null;
  badgeText?: string;
}

export function LoveMapReflectionStudio({
  eyebrow,
  title,
  description,
  textareaId,
  textareaLabel,
  value,
  onChange,
  onSave,
  saving,
  helperText,
  placeholder,
  lastUpdated,
  badgeText,
}: LoveMapReflectionStudioProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/58 bg-white/82 p-5 shadow-lift backdrop-blur-md md:p-6">
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
            <p className="max-w-2xl type-body-muted text-muted-foreground">{description}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {badgeText ? <Badge variant="status" size="sm">{badgeText}</Badge> : null}
            <Badge variant={lastUpdated ? 'success' : 'metadata'} size="sm">
              {lastUpdated ? `最近更新 ${lastUpdated}` : '尚未寫下'}
            </Badge>
          </div>
        </div>

        <Textarea
          id={textareaId}
          label={textareaLabel}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          helperText={helperText}
          maxLength={5000}
          className="min-h-[12rem] bg-white/74"
        />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="type-caption text-muted-foreground">
            這些筆記只代表你此刻願意留下的理解，不會被 Haven 當成自動共享的雙人真相。
          </p>
          <Button
            onClick={onSave}
            loading={saving}
            rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
          >
            保存這一層
          </Button>
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapPromptCardProps {
  index: number;
  title: string;
  description: string;
  question: string;
}

export function LoveMapPromptCard({
  index,
  title,
  description,
  question,
}: LoveMapPromptCardProps) {
  return (
    <div className="rounded-[1.9rem] border border-white/56 bg-white/78 p-5 shadow-soft backdrop-blur-md">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="metadata" size="sm">
            Prompt {String(index).padStart(2, '0')}
          </Badge>
          <span className="type-caption text-muted-foreground">Conversation support</span>
        </div>

        <div className="space-y-2">
          <h3 className="type-h3 text-card-foreground">{title}</h3>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>

        <div className="rounded-[1.5rem] border border-primary/10 bg-primary/8 px-4 py-4">
          <p className="type-body text-card-foreground">{question}</p>
        </div>
      </div>
    </div>
  );
}

interface LoveMapFutureComposerProps {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function LoveMapFutureComposer({
  eyebrow,
  title,
  description,
  children,
  footer,
}: LoveMapFutureComposerProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/58 bg-white/82 p-5 shadow-lift backdrop-blur-md md:p-6">
      <div className="space-y-5">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/72 px-3 py-1.5 shadow-soft">
            <Sparkles className="h-4 w-4 text-primary" aria-hidden />
            <span className="type-micro uppercase text-primary/80">{eyebrow}</span>
          </div>
          <h3 className="type-h3 text-card-foreground">{title}</h3>
          <p className="max-w-2xl type-body-muted text-muted-foreground">{description}</p>
        </div>

        {children}

        {footer}
      </div>
    </GlassCard>
  );
}

function LoveMapStructuredNoteGroup({
  label,
  entries,
}: {
  label: string;
  entries: string[];
}) {
  return (
    <div className="space-y-2.5">
      <p className="type-micro uppercase text-primary/80">{label}</p>
      <div className="space-y-2">
        {entries.map((entry, index) => (
          <div
            key={`${label}-${index}-${entry}`}
            className="rounded-[1.2rem] border border-white/58 bg-white/76 px-4 py-3 shadow-soft"
          >
            <p className="type-body text-card-foreground">{entry}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LoveMapSharedFutureNotesPanel({ notes }: { notes?: string | null }) {
  const readModel = parseSharedFutureNotes(notes);

  if (!notes) {
    return null;
  }

  if (!readModel.hasStructuredRefinements) {
    return (
      <div className="rounded-[1.4rem] border border-primary/10 bg-primary/8 px-4 py-4">
        <p className="type-body whitespace-pre-line text-card-foreground">{notes}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-[1.4rem] border border-primary/10 bg-primary/8 px-4 py-4">
      {readModel.baseNote ? (
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">補充</p>
          <p className="type-body whitespace-pre-line text-card-foreground">{readModel.baseNote}</p>
        </div>
      ) : null}

      {readModel.nextSteps.length > 0 ? (
        <LoveMapStructuredNoteGroup label="下一步" entries={readModel.nextSteps} />
      ) : null}

      {readModel.cadences.length > 0 ? (
        <LoveMapStructuredNoteGroup label="節奏" entries={readModel.cadences} />
      ) : null}
    </div>
  );
}

interface LoveMapSuggestedUpdateCardProps {
  savedItems?: Array<{ title: string; notes?: string | null }> | null;
  createdAtLabel?: string | null;
  title: string;
  notes: string;
  variant?: 'default' | 'story_ritual';
  evidence: Array<{
    source_kind: string;
    label: string;
    excerpt: string;
  }>;
  acceptDisabled?: boolean;
  noopReason?: string | null;
  mutationCopy?: { acceptingLabel: string; dismissingLabel: string };
  onAccept: () => void;
  onDismiss: () => void;
  accepting?: boolean;
  dismissing?: boolean;
}

export function LoveMapSuggestedUpdateCard({
  savedItems,
  createdAtLabel,
  title,
  notes,
  variant = 'default',
  evidence,
  acceptDisabled = false,
  noopReason,
  mutationCopy,
  onAccept,
  onDismiss,
  accepting = false,
  dismissing = false,
}: LoveMapSuggestedUpdateCardProps) {
  const badgeLabel = 'Haven 建議';
  const trustCopy =
    variant === 'story_ritual'
      ? '這是 Haven 根據你們已被留下的 Story 回聲提出的 ritual 提案。這是建議，不是已保存的共同未來；只有接受後，才會寫入你們的 Future。'
      : '這是 Haven 根據可共同看見的片段提出的提案。這是建議，不是已保存的共同未來；只有接受後，才會寫入你們的 Future。';
  const evidenceHeading = '根據可共同看見的片段';

  const filteredEvidence = filterSharedFutureEvidence(evidence);

  const savedPreview = buildSavedSharedFuturePreviewTitles(savedItems ?? null, 3);
  const savedPreviewTitles = savedPreview.titles;
  const savedMoreCount = savedPreview.moreCount;
  const acceptingLabel = mutationCopy?.acceptingLabel ?? '正在寫入 Future…';
  const dismissingLabel = mutationCopy?.dismissingLabel ?? '正在略過建議…';

  return (
    <GlassCard
      className="overflow-hidden rounded-[2.2rem] border-primary/14 bg-[linear-gradient(180deg,rgba(255,251,246,0.96),rgba(249,243,234,0.92))] p-5 shadow-lift backdrop-blur-md md:p-6"
      data-testid="shared-future-suggestion-card"
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/16 bg-primary/10 px-3 py-1.5 shadow-soft">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden />
              <span className="type-micro uppercase text-primary/80">{badgeLabel}</span>
            </div>
            <h3 className="type-h3 text-card-foreground">{title}</h3>
            {notes ? <p className="max-w-2xl type-body-muted text-muted-foreground">{notes}</p> : null}
          </div>

          <Badge variant="metadata" size="sm">
            僅你可見（待審核）
          </Badge>
        </div>

        {createdAtLabel ? (
          <p className="type-caption text-muted-foreground">生成時間：{createdAtLabel}</p>
        ) : null}

        <div className="rounded-[1.55rem] border border-white/58 bg-white/76 px-4 py-4 shadow-soft">
          <p className="type-caption text-muted-foreground">
            {trustCopy}
          </p>
        </div>

        {variant !== 'story_ritual' ? (
          <div className="space-y-3" data-testid="shared-future-suggestion-compare">
            <p className="type-caption text-card-foreground/88">
              接受後，這則提案會新增成一個 Shared Future 片段；略過則不會改動目前保存的共同未來。
            </p>
            {noopReason ? (
              <p className="type-caption text-muted-foreground" data-testid="shared-future-suggestion-noop">
                {noopReason}
              </p>
            ) : null}
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
                <p className="type-micro uppercase text-primary/80">目前保存</p>
                {savedPreviewTitles.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {savedPreviewTitles.map((t) => (
                      <p key={t} className="type-body text-card-foreground">
                        {t}
                      </p>
                    ))}
                    {savedMoreCount > 0 ? (
                      <p className="type-caption text-muted-foreground">以及其他 {savedMoreCount} 個片段…</p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-3 type-body text-muted-foreground">（你們的 Shared Future 目前還沒有片段）</p>
                )}
              </div>
              <div className="rounded-[1.45rem] border border-primary/14 bg-primary/8 px-4 py-4 shadow-soft">
                <p className="type-micro uppercase text-primary/80">建議新增</p>
                <div className="mt-3 space-y-2">
                  <Badge variant="status" size="sm">
                    新片段
                  </Badge>
                  <p className="type-body text-card-foreground">{title}</p>
                  {notes ? <p className="type-body-muted text-muted-foreground">{notes}</p> : null}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {filteredEvidence.length > 0 ? (
          <div className="space-y-3" data-testid="shared-future-suggestion-evidence">
            <p className="type-caption text-card-foreground/82">{evidenceHeading}</p>
            <div className="grid gap-3">
              {filteredEvidence.map((item, index) => (
                <div
                  key={`${item.source_kind}-${item.label}-${index}`}
                  className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="status" size="sm">
                      {sharedFutureEvidenceKindLabel(item.source_kind)}
                    </Badge>
                    <span className="type-caption text-card-foreground">{item.label}</span>
                  </div>
                  <p className="mt-2 type-body-muted text-muted-foreground">{item.excerpt}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
            <p className="type-caption text-muted-foreground">目前沒有足夠清楚的共同片段可作為支撐。</p>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="type-caption text-muted-foreground">
            接受後才會寫進 Shared Future；略過後它不會立刻又回來。
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              loading={dismissing}
              disabled={accepting || dismissing}
              leftIcon={<X className="h-4 w-4" aria-hidden />}
              data-testid="shared-future-suggestion-dismiss"
              onClick={onDismiss}
            >
              {dismissing ? dismissingLabel : '先略過'}
            </Button>
            <Button
              loading={accepting}
              disabled={accepting || dismissing || acceptDisabled}
              leftIcon={<Check className="h-4 w-4" aria-hidden />}
              data-testid="shared-future-suggestion-accept"
              onClick={onAccept}
            >
              {accepting ? acceptingLabel : acceptDisabled ? '已存在於 Shared Future' : '接受並寫入 Future'}
            </Button>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapCompassSuggestionCardProps {
  savedCompass: LoveMapRelationshipCompassPublic | null;
  candidate: {
    identity_statement: string | null;
    story_anchor: string | null;
    future_direction: string | null;
  };
  evidence: RelationshipKnowledgeSuggestionEvidencePublic[];
  mutationCopy?: { acceptingLabel: string; dismissingLabel: string };
  onAccept: () => void;
  onDismiss: () => void;
  accepting?: boolean;
  dismissing?: boolean;
}

const COMPASS_SUGGESTION_FIELDS = [
  { key: 'identity_statement', label: '我們現在是什麼樣的關係' },
  { key: 'story_anchor', label: '我們想一起記得哪段故事' },
  { key: 'future_direction', label: '接下來一起靠近什麼' },
] as const;

export function LoveMapCompassSuggestionCard({
  savedCompass,
  candidate,
  evidence,
  mutationCopy,
  onAccept,
  onDismiss,
  accepting = false,
  dismissing = false,
}: LoveMapCompassSuggestionCardProps) {
  const proposedFields = COMPASS_SUGGESTION_FIELDS.filter((field) => candidate[field.key]?.trim());
  const fieldChangeCount = proposedFields.filter(
    (field) => !compassFieldValuesEqual(savedCompass ? savedCompass[field.key] : null, candidate[field.key]),
  ).length;
  const allProposedMatchSaved = proposedFields.length > 0 && fieldChangeCount === 0;
  const acceptingLabel = mutationCopy?.acceptingLabel ?? '正在寫入 Compass…';
  const dismissingLabel = mutationCopy?.dismissingLabel ?? '正在略過建議…';

  return (
    <GlassCard
      className="overflow-hidden rounded-[2.1rem] border-primary/14 bg-[linear-gradient(180deg,rgba(255,251,246,0.96),rgba(248,242,233,0.92))] p-5 shadow-lift backdrop-blur-md md:p-6"
      data-testid="relationship-compass-suggestion-card"
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/16 bg-primary/10 px-3 py-1.5 shadow-soft">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden />
              <span className="type-micro uppercase text-primary/80">建議更新</span>
            </div>
            <h3 className="type-h3 text-card-foreground">Relationship Compass 可以被更新一版</h3>
            <p className="max-w-2xl type-body-muted text-muted-foreground">
              這是 Haven 根據最近留下的片段整理出的候選 wording，不是已保存的共同真相。
            </p>
          </div>

          <Badge variant="metadata" size="sm">
            僅你可見（待審核）
          </Badge>
        </div>

        <div className="rounded-[1.55rem] border border-white/58 bg-white/76 px-4 py-4 shadow-soft">
          <p className="type-caption text-muted-foreground">
            這是建議更新，不是已保存的共同真相；只有接受後才會寫入 Compass。略過不會改動現在的 Relationship Compass。
          </p>
        </div>

        {proposedFields.length > 0 ? (
          <div
            className="space-y-3"
            data-testid="relationship-compass-suggestion-compare"
          >
            <p className="type-caption text-card-foreground/88">
              接受前，先看每個欄位與目前保存的差別；接受後寫入的內容即為新的共同方向。
            </p>
            {allProposedMatchSaved ? (
              <p className="type-caption text-muted-foreground">這些欄位與目前保存相同；若你仍要接受，代表再次確認同一段文字。</p>
            ) : fieldChangeCount > 0 ? (
              <p className="type-caption text-muted-foreground">
                在有建議內容的 {proposedFields.length} 個欄位中，有 {fieldChangeCount} 個與目前保存不同。
              </p>
            ) : null}
            <div className="grid gap-3">
              {proposedFields.map((field) => {
                const savedText = savedCompass ? savedCompass[field.key] : null;
                const proposedText = candidate[field.key];
                const same = compassFieldValuesEqual(savedText, proposedText);
                const savedEmpty = !normalizeCompassFieldValue(savedText);
                return (
                  <div
                    key={field.key}
                    data-testid={`relationship-compass-suggestion-field-${field.key}`}
                    className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
                  >
                    <p className="type-micro uppercase text-primary/80">{field.label}</p>
                    {same ? (
                      <div className="mt-3 space-y-2">
                        <Badge variant="status" size="sm">
                          與目前保存相同
                        </Badge>
                        <p className="type-body text-card-foreground">{proposedText}</p>
                      </div>
                    ) : (
                      <div className="mt-3 grid gap-3 md:grid-cols-2">
                        <div>
                          <p className="type-caption text-muted-foreground">目前保存</p>
                          <p className="mt-1 type-body text-card-foreground">
                            {savedEmpty ? '（此欄位尚未填寫）' : savedText}
                          </p>
                        </div>
                        <div>
                          <p className="type-caption text-primary/78">建議</p>
                          <p className="mt-1 type-body text-card-foreground">{proposedText}</p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft">
            <p className="type-caption text-muted-foreground">
              Haven 這次沒有整理出足夠清楚、可寫入 Compass 的文字。
            </p>
          </div>
        )}

        {evidence.length > 0 ? (
          <div className="space-y-3">
            <p className="type-caption text-muted-foreground">
              證據只引用你們已留下、產品內可檢視的片段摘要，用來幫你對照「最近留下了什麼」；不宣稱模型內部推理或外部資訊。
            </p>
            <p className="type-caption text-card-foreground/82">這個建議主要根據</p>
            <div className="grid gap-3">
              {evidence.map((item, index) => {
                const href = buildCompassSuggestionEvidenceArtifactHref(item);
                return (
                  <div
                    key={`${item.source_kind}-${item.source_id}-${item.label}-${index}`}
                    className="rounded-[1.35rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
                    data-testid="relationship-compass-suggestion-evidence-item"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="status" size="sm">
                        {item.source_kind}
                      </Badge>
                      <span className="type-caption text-card-foreground">{item.label}</span>
                    </div>
                    <p className="mt-2 type-body-muted text-muted-foreground">{item.excerpt}</p>
                    {href ? (
                      <p className="mt-2">
                        <Link
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          className="type-caption font-medium text-primary underline-offset-2 hover:underline"
                          data-testid="relationship-compass-suggestion-evidence-link"
                        >
                          打開日記
                        </Link>
                      </p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="type-caption text-muted-foreground">
            接受後會像一般 Compass 更新一樣進入共享關係知識；不會自動改寫 Memory 或 Blueprint。
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              loading={dismissing}
              disabled={accepting || dismissing}
              leftIcon={<X className="h-4 w-4" aria-hidden />}
              data-testid="relationship-compass-suggestion-dismiss"
              onClick={onDismiss}
            >
              {dismissing ? dismissingLabel : '先略過'}
            </Button>
            <Button
              loading={accepting}
              disabled={accepting || dismissing || proposedFields.length === 0 || allProposedMatchSaved}
              leftIcon={<Check className="h-4 w-4" aria-hidden />}
              data-testid="relationship-compass-suggestion-accept"
              onClick={onAccept}
            >
              {accepting ? acceptingLabel : allProposedMatchSaved ? '已和目前保存一致' : '接受並寫入 Compass'}
            </Button>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapRefinementSuggestionCardProps {
  targetTitle: string;
  refinementKind?: 'next_step' | 'cadence';
  proposedNotes: string;
  evidence: Array<{
    source_kind: string;
    label: string;
    excerpt: string;
  }>;
  onAccept: () => void;
  onDismiss: () => void;
  accepting?: boolean;
  dismissing?: boolean;
}

export function LoveMapRefinementSuggestionCard({
  targetTitle,
  refinementKind = 'next_step',
  proposedNotes,
  evidence,
  onAccept,
  onDismiss,
  accepting = false,
  dismissing = false,
}: LoveMapRefinementSuggestionCardProps) {
  const suggestionLabel = refinementKind === 'cadence' ? '建議補上的節奏：' : '建議補上的下一步：';
  const acceptedNoteLabel = refinementKind === 'cadence' ? '節奏' : '下一步';
  return (
    <GlassCard className="overflow-hidden rounded-[1.9rem] border-primary/12 bg-[linear-gradient(180deg,rgba(255,251,246,0.94),rgba(247,242,234,0.9))] p-4 shadow-soft backdrop-blur-md md:p-5">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/16 bg-primary/10 px-3 py-1.5 shadow-soft">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden />
              <span className="type-micro uppercase text-primary/80">Haven 建議</span>
            </div>
            <p className="type-section-title text-card-foreground">{targetTitle}</p>
            <p className="type-body-muted text-muted-foreground">
              {suggestionLabel}
              {proposedNotes}
            </p>
          </div>

          <Badge variant="metadata" size="sm">
            僅你可見（待審核）
          </Badge>
        </div>

        <div className="rounded-[1.45rem] border border-white/58 bg-white/76 px-4 py-4 shadow-soft">
          <p className="type-caption text-muted-foreground">
            只有你看得到；接受前不會改動這個 Shared Future 片段。
          </p>
        </div>

        {evidence.length > 0 ? (
          <div className="space-y-3">
            <p className="type-caption text-card-foreground/82">這個建議根據</p>
            <div className="grid gap-3">
              {evidence.map((item, index) => (
                <div
                  key={`${item.source_kind}-${item.label}-${index}`}
                  className="rounded-[1.35rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="status" size="sm">
                      {item.source_kind}
                    </Badge>
                    <span className="type-caption text-card-foreground">{item.label}</span>
                  </div>
                  <p className="mt-2 type-body-muted text-muted-foreground">{item.excerpt}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="type-caption text-muted-foreground">
            接受後只會把這句{acceptedNoteLabel}補進這個片段的 notes；略過後它不會立刻又回來。
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              loading={dismissing}
              disabled={accepting || dismissing}
              leftIcon={<X className="h-4 w-4" aria-hidden />}
              onClick={onDismiss}
            >
              略過
            </Button>
            <Button
              loading={accepting}
              disabled={accepting || dismissing}
              leftIcon={<Check className="h-4 w-4" aria-hidden />}
              onClick={onAccept}
            >
              接受
            </Button>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
