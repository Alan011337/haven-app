'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, BookOpen, Check, Gift, Heart, MessageCircle, Sparkles, X } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import { parseSharedFutureNotes } from '@/lib/shared-future-read-model';
import { cn } from '@/lib/utils';

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
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-full border border-white/54 bg-white/76 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            aria-label="返回首頁"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            回首頁
          </Link>

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
}: LoveMapSystemCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.94),rgba(246,239,230,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
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

interface LoveMapSectionProps {
  id?: string;
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
  children: ReactNode;
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
}

export function LoveMapStatePanel({
  eyebrow,
  title,
  description,
  tone = 'default',
  actionLabel,
  onAction,
}: LoveMapStatePanelProps) {
  return (
    <GlassCard
      className={cn('overflow-hidden rounded-[2.2rem] p-6 shadow-soft backdrop-blur-md md:p-7', stateToneClasses[tone])}
    >
      <div className="space-y-4">
        {eyebrow ? <p className="type-micro uppercase text-primary/80">{eyebrow}</p> : null}
        <div className="space-y-2">
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        {actionLabel && onAction ? (
          <Button variant="secondary" onClick={onAction}>
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
  title: string;
  notes: string;
  variant?: 'default' | 'story_ritual';
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

export function LoveMapSuggestedUpdateCard({
  title,
  notes,
  variant = 'default',
  evidence,
  onAccept,
  onDismiss,
  accepting = false,
  dismissing = false,
}: LoveMapSuggestedUpdateCardProps) {
  const badgeLabel = variant === 'story_ritual' ? 'Story-adjacent ritual suggestion' : 'AI suggestion';
  const trustCopy =
    variant === 'story_ritual'
      ? '這是 Haven 根據你們已經被留下的 Story memory 提出的 ritual 建議。只有你看得到，按下接受前不會變成 shared truth。'
      : '這是 Haven 根據已留下的活動提出的建議。只有你看得到，按下接受前不會變成 shared truth。';
  const evidenceHeading =
    variant === 'story_ritual' ? 'What in your story this builds on' : 'Why Haven suggested this';

  return (
    <GlassCard className="overflow-hidden rounded-[2.2rem] border-primary/14 bg-[linear-gradient(180deg,rgba(255,251,246,0.96),rgba(249,243,234,0.92))] p-5 shadow-lift backdrop-blur-md md:p-6">
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
            Personal review only
          </Badge>
        </div>

        <div className="rounded-[1.55rem] border border-white/58 bg-white/76 px-4 py-4 shadow-soft">
          <p className="type-caption text-muted-foreground">
            {trustCopy}
          </p>
        </div>

        <div className="space-y-3">
          <p className="type-caption text-card-foreground/82">{evidenceHeading}</p>
          <div className="grid gap-3">
            {evidence.map((item, index) => (
              <div
                key={`${item.source_kind}-${item.label}-${index}`}
                className="rounded-[1.45rem] border border-white/58 bg-white/78 px-4 py-4 shadow-soft"
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
              <span className="type-micro uppercase text-primary/80">Refinement suggestion</span>
            </div>
            <p className="type-section-title text-card-foreground">{targetTitle}</p>
            <p className="type-body-muted text-muted-foreground">
              {suggestionLabel}
              {proposedNotes}
            </p>
          </div>

          <Badge variant="metadata" size="sm">
            Personal review only
          </Badge>
        </div>

        <div className="rounded-[1.45rem] border border-white/58 bg-white/76 px-4 py-4 shadow-soft">
          <p className="type-caption text-muted-foreground">
            只有你看得到；接受前不會改動這個 Shared Future 片段。
          </p>
        </div>

        {evidence.length > 0 ? (
          <div className="space-y-3">
            <p className="type-caption text-card-foreground/82">What this builds on</p>
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
