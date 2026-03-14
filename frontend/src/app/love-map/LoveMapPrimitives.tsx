'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Heart } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import { cn } from '@/lib/utils';

type ChapterNavItem = {
  href: string;
  label: string;
  description: string;
  complete: boolean;
};

type LoveMapLayerTone = 'safe' | 'medium' | 'deep';
type LoveMapStateTone = 'default' | 'quiet' | 'error';

const layerToneClasses: Record<LoveMapLayerTone, string> = {
  safe:
    'border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.96),rgba(247,241,232,0.9))]',
  medium:
    'border-white/52 bg-[linear-gradient(165deg,rgba(255,252,248,0.96),rgba(243,235,228,0.92))]',
  deep:
    'border-white/50 bg-[linear-gradient(165deg,rgba(252,248,243,0.97),rgba(238,229,221,0.94))]',
};

const stateToneClasses: Record<LoveMapStateTone, string> = {
  default: 'border-white/54 bg-white/84',
  quiet: 'border-primary/12 bg-white/76',
  error: 'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,251,249,0.96),rgba(248,240,236,0.94))]',
};

interface LoveMapShellProps {
  children: ReactNode;
}

export function LoveMapShell({ children }: LoveMapShellProps) {
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
            Shared Emotional Landscape
          </Badge>
        </div>

        {children}
      </div>
    </div>
  );
}

interface LoveMapCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  ctaHref: string;
  ctaLabel: string;
  highlights?: ReactNode;
  aside: ReactNode;
}

export function LoveMapCover({
  eyebrow,
  title,
  description,
  pulse,
  ctaHref,
  ctaLabel,
  highlights,
  aside,
}: LoveMapCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.94),rgba(246,239,230,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.72),transparent_36%),radial-gradient(circle_at_86%_12%,rgba(255,255,255,0.34),transparent_22%)]" aria-hidden />
      <div className="pointer-events-none absolute right-[-4rem] top-[-2rem] h-72 w-72 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
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

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.85rem] border border-white/56 bg-white/70 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Heart className="h-4 w-4" aria-hidden />
            </span>
            <p className="type-body-muted text-card-foreground">{pulse}</p>
          </div>

          {highlights}

          <a
            href={ctaHref}
            className="inline-flex items-center gap-2 rounded-full border border-primary/18 bg-primary/10 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:bg-primary/14 hover:shadow-lift focus-ring-premium"
          >
            {ctaLabel}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </a>
        </div>

        <div className="space-y-4">{aside}</div>
      </div>
    </section>
  );
}

interface LoveMapOverviewCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}

export function LoveMapOverviewCard({
  eyebrow,
  title,
  description,
  children,
}: LoveMapOverviewCardProps) {
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

interface LoveMapChapterNavProps {
  items: ChapterNavItem[];
}

export function LoveMapChapterNav({ items }: LoveMapChapterNavProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.3rem] border-white/52 bg-white/80 p-5 md:p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/80">Chapter Rail</p>
          <h2 className="type-h3 text-card-foreground">沿著這張地圖慢慢往內走。</h2>
          <p className="type-body-muted text-muted-foreground">
            三層不是難度切換，而是理解彼此時，願意走到多深的三段距離。
          </p>
        </div>

        <div className="grid gap-2.5">
          {items.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="group flex items-start gap-3 rounded-[1.6rem] border border-white/50 bg-white/72 px-4 py-4 shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:border-primary/14 hover:shadow-lift focus-ring-premium"
            >
              <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary/70 shadow-[0_0_0_8px_rgba(201,163,100,0.12)]" aria-hidden />
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="type-section-title text-card-foreground">{item.label}</span>
                  <Badge variant={item.complete ? 'success' : 'metadata'} size="sm">
                    {item.complete ? '已寫下筆記' : '尚未寫下'}
                  </Badge>
                </div>
                <p className="type-caption text-muted-foreground">{item.description}</p>
              </div>
            </a>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapLayerStageProps {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  tone: LoveMapLayerTone;
  aside?: ReactNode;
  children: ReactNode;
}

export function LoveMapLayerStage({
  id,
  eyebrow,
  title,
  description,
  tone,
  aside,
  children,
}: LoveMapLayerStageProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <GlassCard
        className={cn(
          'overflow-hidden rounded-[2.8rem] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10',
          layerToneClasses[tone],
        )}
      >
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
    <div className="rounded-[2rem] border border-white/56 bg-white/78 p-5 shadow-soft backdrop-blur-md">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="metadata" size="sm">
            Prompt {String(index).padStart(2, '0')}
          </Badge>
          <span className="type-caption text-muted-foreground">Love Map</span>
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
  lastUpdated?: string | null;
  helperText: string;
  placeholder: string;
  promptCount: number;
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
  lastUpdated,
  helperText,
  placeholder,
  promptCount,
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
            <Badge variant="status" size="sm">
              {promptCount} 個 prompts
            </Badge>
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
          className="min-h-[14rem] bg-white/74"
        />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="type-caption text-muted-foreground">
            每一層會保存成一段完整筆記，之後仍可以一起回來補寫或重讀。
          </p>
          <Button
            onClick={onSave}
            loading={saving}
            rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
          >
            儲存這一層的筆記
          </Button>
        </div>
      </div>
    </GlassCard>
  );
}

interface LoveMapStatePanelProps {
  eyebrow?: string;
  title: string;
  description: string;
  tone?: LoveMapStateTone;
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
    <GlassCard className={cn('overflow-hidden rounded-[2.2rem] p-6 shadow-soft backdrop-blur-md md:p-7', stateToneClasses[tone])}>
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
