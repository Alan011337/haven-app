'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, HandHeart, PhoneCall, ShieldAlert } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import { CRISIS_HOTLINES } from '@/lib/safety-policy';
import { cn } from '@/lib/utils';

type RailState = 'complete' | 'active' | 'upcoming';
type MediationTone = 'default' | 'quiet' | 'success' | 'error';

type MediationSequenceItem = {
  label: string;
  description: string;
  state: RailState;
  meta?: string;
};

const railStateClasses: Record<RailState, string> = {
  complete: 'border-accent/18 bg-accent/10 text-card-foreground',
  active: 'border-primary/20 bg-primary/10 text-card-foreground shadow-soft',
  upcoming: 'border-white/48 bg-white/66 text-muted-foreground',
};

const panelToneClasses: Record<MediationTone, string> = {
  default: 'border-white/54 bg-white/84',
  quiet: 'border-primary/12 bg-white/76',
  success: 'border-accent/16 bg-[linear-gradient(180deg,rgba(250,253,250,0.96),rgba(241,248,242,0.94))]',
  error: 'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,251,249,0.96),rgba(248,240,236,0.94))]',
};

interface MediationShellProps {
  children: ReactNode;
}

export function MediationShell({ children }: MediationShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.14),transparent_24%),radial-gradient(circle_at_88%_10%,rgba(229,236,230,0.52),transparent_28%),linear-gradient(180deg,#fbf8f3_0%,#f4eee6_54%,#efe9e1_100%)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-28" aria-hidden />
      <div className="pointer-events-none absolute -left-10 top-16 h-72 w-72 rounded-full bg-primary/7 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />

      <div className="relative z-10 mx-auto max-w-[1540px] space-y-[clamp(1.5rem,3vw,2.75rem)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-full border border-white/54 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft backdrop-blur-xl transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            aria-label="返回首頁"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            回首頁
          </Link>

          <Badge variant="metadata" size="md" className="border-white/50 bg-white/72 text-primary/78 shadow-soft">
            Calm Repair Room
          </Badge>
        </div>

        {children}
      </div>
    </div>
  );
}

interface MediationCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  highlights?: ReactNode;
  primaryAction?: ReactNode;
  aside: ReactNode;
}

export function MediationCover({
  eyebrow,
  title,
  description,
  pulse,
  highlights,
  primaryAction,
  aside,
}: MediationCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,252,248,0.96),rgba(244,237,228,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.72),transparent_38%),radial-gradient(circle_at_84%_12%,rgba(255,255,255,0.3),transparent_22%)]" aria-hidden />
      <div className="pointer-events-none absolute right-[-4rem] top-[-2rem] h-72 w-72 rounded-full bg-primary/9 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-3rem] left-[-1rem] h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <div className="space-y-4">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h1 className="max-w-[56rem] type-h1 text-card-foreground">{title}</h1>
              <p className="max-w-[48rem] type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.85rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <HandHeart className="h-4 w-4" aria-hidden />
            </span>
            <p className="type-body-muted text-card-foreground">{pulse}</p>
          </div>

          {highlights}

          {primaryAction ? <div className="flex flex-wrap gap-3">{primaryAction}</div> : null}
        </div>

        <div className="space-y-4">{aside}</div>
      </div>
    </section>
  );
}

interface MediationOverviewCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}

export function MediationOverviewCard({
  eyebrow,
  title,
  description,
  children,
}: MediationOverviewCardProps) {
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

interface MediationSequenceRailProps {
  items: MediationSequenceItem[];
}

export function MediationSequenceRail({ items }: MediationSequenceRailProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.45rem] border-white/52 bg-white/82 p-5 md:p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">Guided Sequence</p>
          <h2 className="type-h3 text-card-foreground">一次只處理這一個房間裡現在該發生的事。</h2>
          <p className="type-body-muted text-muted-foreground">
            這條序列不是催促你們，而是把修復拆成足夠溫和、足夠清楚的幾個階段。
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {items.map((item) => (
            <div
              key={item.label}
              className={cn(
                'rounded-[1.7rem] border px-4 py-4 backdrop-blur-md transition-all duration-haven ease-haven',
                railStateClasses[item.state],
              )}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="type-section-title">{item.label}</span>
                  <Badge variant={item.state === 'complete' ? 'success' : item.state === 'active' ? 'status' : 'metadata'} size="sm">
                    {item.state === 'complete' ? '已完成' : item.state === 'active' ? '當前階段' : '接下來'}
                  </Badge>
                </div>
                <p className="type-caption text-muted-foreground">{item.description}</p>
                {item.meta ? <p className="type-caption text-card-foreground">{item.meta}</p> : null}
              </div>
            </div>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

interface MediationStageFrameProps {
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
  children: ReactNode;
}

export function MediationStageFrame({
  eyebrow,
  title,
  description,
  aside,
  children,
}: MediationStageFrameProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.85rem] border-white/52 bg-[linear-gradient(165deg,rgba(255,252,248,0.95),rgba(243,235,227,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
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
  );
}

interface MediationStudioCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function MediationStudioCard({
  eyebrow,
  title,
  description,
  children,
  footer,
}: MediationStudioCardProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.2rem] border-white/58 bg-white/82 p-5 shadow-lift backdrop-blur-md md:p-6">
      <div className="space-y-5">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
          <h3 className="type-h3 text-card-foreground">{title}</h3>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>

        {children}

        {footer ? <div className="flex flex-wrap items-center justify-between gap-3">{footer}</div> : null}
      </div>
    </GlassCard>
  );
}

interface MediationQuestionCardProps {
  eyebrow: string;
  title: string;
  description?: string;
  textareaId: string;
  textareaLabel: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  helperText?: string;
  maxLength?: number;
}

export function MediationQuestionCard({
  eyebrow,
  title,
  description,
  textareaId,
  textareaLabel,
  value,
  onChange,
  placeholder,
  helperText,
  maxLength,
}: MediationQuestionCardProps) {
  return (
    <div className="rounded-[2rem] border border-white/56 bg-white/78 p-5 shadow-soft backdrop-blur-md">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
          <h3 className="type-section-title text-card-foreground">{title}</h3>
          {description ? <p className="type-caption text-muted-foreground">{description}</p> : null}
        </div>

        <Textarea
          id={textareaId}
          label={textareaLabel}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          helperText={helperText}
          maxLength={maxLength}
          className="min-h-[9.5rem] bg-white/74"
        />
      </div>
    </div>
  );
}

interface MediationResponseCardProps {
  eyebrow: string;
  question: string;
  answer: string;
}

export function MediationResponseCard({
  eyebrow,
  question,
  answer,
}: MediationResponseCardProps) {
  return (
    <div className="rounded-[2rem] border border-white/56 bg-white/78 p-5 shadow-soft backdrop-blur-md">
      <div className="space-y-3">
        <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
        <p className="type-caption text-muted-foreground">{question}</p>
        <p className="type-body text-card-foreground">{answer || '—'}</p>
      </div>
    </div>
  );
}

interface MediationStatePanelProps {
  eyebrow?: string;
  title: string;
  description: string;
  tone?: MediationTone;
  action?: ReactNode;
}

export function MediationStatePanel({
  eyebrow,
  title,
  description,
  tone = 'default',
  action,
}: MediationStatePanelProps) {
  return (
    <GlassCard className={cn('overflow-hidden rounded-[2.2rem] p-6 shadow-soft backdrop-blur-md md:p-7', panelToneClasses[tone])}>
      <div className="space-y-4">
        {eyebrow ? <p className="type-micro uppercase text-primary/80">{eyebrow}</p> : null}
        <div className="space-y-2">
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        {action ? <div className="flex flex-wrap gap-3">{action}</div> : null}
      </div>
    </GlassCard>
  );
}

interface MediationSafetyPanelProps {
  onReset: () => void;
}

export function MediationSafetyPanel({ onReset }: MediationSafetyPanelProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.3rem] border-destructive/18 bg-[linear-gradient(180deg,rgba(255,251,249,0.97),rgba(248,240,236,0.95))] p-6 shadow-soft backdrop-blur-md md:p-7">
      <div className="space-y-5">
        <div className="flex items-start gap-3">
          <span className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <ShieldAlert className="h-4 w-4" aria-hidden />
          </span>
          <div className="space-y-2">
            <p className="type-micro uppercase text-destructive">Safety Mode</p>
            <h3 className="type-h3 text-card-foreground">系統先把這個房間安靜下來了。</h3>
            <p className="type-body-muted text-muted-foreground">
              偵測到高風險語句後，修復流程會暫停。現在優先確認雙方安全，而不是把對話繼續推下去。
            </p>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {CRISIS_HOTLINES.map((hotline) => (
            <a
              key={hotline.number}
              href={hotline.href}
              className="inline-flex items-center gap-2 rounded-[1.25rem] border border-white/56 bg-white/82 px-4 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              <PhoneCall className="h-4 w-4 text-destructive" aria-hidden />
              {hotline.name} {hotline.number}
            </a>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={onReset}>
            關閉流程並返回
          </Button>
          <Link
            href="/settings"
            className="inline-flex h-11 items-center justify-center rounded-button border border-primary/18 bg-primary/10 px-5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium"
          >
            前往設定頁
          </Link>
        </div>
      </div>
    </GlassCard>
  );
}
