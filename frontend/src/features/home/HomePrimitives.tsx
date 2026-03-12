import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { ArrowRight, Sparkles } from 'lucide-react';
import Button from '@/components/ui/Button';
import { GlassCard } from '@/components/haven/GlassCard';
import { cn } from '@/lib/utils';

type MetricTone = 'warm' | 'sage' | 'neutral';
type StateTone = 'warm' | 'sage' | 'neutral';
type PaperTone = 'hero' | 'paper' | 'mist';

interface HomeSectionFrameProps {
  eyebrow?: string;
  title: string;
  description?: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

interface EditorialMetricPillProps {
  icon: LucideIcon;
  label: string;
  value: string;
  tone?: MetricTone;
  className?: string;
}

interface HomeHeroStageProps {
  eyebrow?: string;
  title: string;
  description?: string;
  aside?: ReactNode;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
}

interface HomeCoverStageProps {
  eyebrow?: string;
  title: string;
  description?: string;
  pulse?: ReactNode;
  note?: ReactNode;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
}

interface HomeMosaicRailProps {
  children: ReactNode;
  className?: string;
}

interface HomeComposerStageProps {
  eyebrow?: string;
  title: string;
  description?: string;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

interface EditorialPaperCardProps {
  eyebrow?: string;
  title?: string;
  description?: string;
  tone?: PaperTone;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

interface EditorialTimelineColumnProps {
  eyebrow?: string;
  title: string;
  description?: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}

interface EditorialEmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

interface EditorialDeferredStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

interface EditorialStateCardProps {
  icon?: LucideIcon;
  eyebrow?: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  tone?: StateTone;
  className?: string;
}

interface HomeRailNavProps {
  children: ReactNode;
  className?: string;
}

interface TimelineDateRailProps {
  eyebrow: string;
  title: string;
  meta: string;
  className?: string;
}

const metricToneClassName: Record<MetricTone, string> = {
  warm: 'border-primary/15 bg-primary/8 text-primary',
  sage: 'border-accent/20 bg-accent/10 text-accent',
  neutral: 'border-border/80 bg-white/55 text-foreground',
};

const stateToneClassName: Record<StateTone, string> = {
  warm: 'border-primary/12 bg-[linear-gradient(180deg,rgba(255,251,246,0.96),rgba(250,245,238,0.92))]',
  sage: 'border-accent/14 bg-[linear-gradient(180deg,rgba(248,251,248,0.96),rgba(241,247,242,0.92))]',
  neutral: 'border-border/80 bg-[linear-gradient(180deg,rgba(255,252,248,0.94),rgba(250,246,240,0.9))]',
};

const stateIconToneClassName: Record<StateTone, string> = {
  warm: 'border-primary/12 bg-primary/10 text-primary',
  sage: 'border-accent/15 bg-accent/10 text-accent',
  neutral: 'border-border/80 bg-white/78 text-card-foreground',
};

const paperToneClassName: Record<PaperTone, string> = {
  hero: 'border-white/52 bg-[linear-gradient(180deg,rgba(255,253,250,0.96),rgba(250,246,240,0.92))] shadow-lift',
  paper: 'border-[rgba(219,204,187,0.38)] bg-[linear-gradient(180deg,rgba(255,254,251,0.98),rgba(251,247,242,0.95))] shadow-soft',
  mist: 'border-white/46 bg-[linear-gradient(180deg,rgba(248,251,248,0.92),rgba(244,248,244,0.88))] shadow-soft',
};

export function HomeSectionFrame({
  eyebrow,
  title,
  description,
  aside,
  children,
  className,
  contentClassName,
}: HomeSectionFrameProps) {
  return (
    <GlassCard className={cn('overflow-hidden p-6 md:p-8', className)}>
      <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <div className="relative flex flex-col gap-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl space-y-2">
            {eyebrow ? (
              <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">
                {eyebrow}
              </p>
            ) : null}
            <div className="space-y-1.5">
              <h3 className="font-art text-[1.7rem] leading-tight text-card-foreground">
                {title}
              </h3>
              {description ? (
                <p className="max-w-2xl text-sm leading-7 text-muted-foreground md:text-[0.96rem]">
                  {description}
                </p>
              ) : null}
            </div>
          </div>
          {aside ? <div className="shrink-0">{aside}</div> : null}
        </div>
        <div className={cn('space-y-4', contentClassName)}>{children}</div>
      </div>
    </GlassCard>
  );
}

export function HomeHeroStage({
  eyebrow,
  title,
  description,
  aside,
  children,
  className,
  contentClassName,
}: HomeHeroStageProps) {
  return (
    <section
      className={cn(
        'relative overflow-hidden rounded-[2.4rem] border border-white/45 bg-[linear-gradient(135deg,rgba(255,253,250,0.94)_0%,rgba(250,245,238,0.92)_42%,rgba(238,245,240,0.82)_100%)] p-6 shadow-lift md:p-8 xl:p-10',
        className,
      )}
    >
      <div
        className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent"
        aria-hidden
      />
      <div className="absolute -right-16 top-0 h-72 w-72 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
      <div className="absolute bottom-0 left-0 h-56 w-56 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.58),transparent_42%)]" aria-hidden />

      <div className="relative z-10 grid gap-8 xl:grid-cols-[minmax(0,1.18fr)_320px] xl:items-start">
        <div className={cn('space-y-5', contentClassName)}>
          {eyebrow ? (
            <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">{eyebrow}</p>
          ) : null}
          <div className="space-y-3">
            <h2 className="max-w-4xl font-art text-[2rem] leading-[1.02] text-card-foreground md:text-[3rem]">
              {title}
            </h2>
            {description ? (
              <p className="max-w-2xl text-sm leading-7 text-muted-foreground md:text-[0.98rem]">
                {description}
              </p>
            ) : null}
          </div>
          {children ? <div className="space-y-5">{children}</div> : null}
        </div>

        {aside ? <div className="xl:pt-2">{aside}</div> : null}
      </div>
    </section>
  );
}

export function HomeCoverStage({
  eyebrow,
  title,
  description,
  pulse,
  note,
  children,
  className,
  contentClassName,
}: HomeCoverStageProps) {
  return (
    <section
      className={cn(
        'relative overflow-hidden rounded-[2.9rem] border border-white/48 bg-[linear-gradient(135deg,rgba(255,254,251,0.98)_0%,rgba(252,248,242,0.94)_36%,rgba(243,248,245,0.82)_100%)] p-6 shadow-lift md:p-8 xl:p-10',
        className,
      )}
    >
      <div className="absolute inset-x-12 top-0 h-px bg-gradient-to-r from-transparent via-primary/28 to-transparent" aria-hidden />
      <div className="absolute -right-12 top-0 h-80 w-80 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
      <div className="absolute bottom-0 left-0 h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.68),transparent_38%)]" aria-hidden />

      <div className="relative z-10 space-y-8">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-8">
          <div className={cn('space-y-4', contentClassName)}>
            {eyebrow ? (
              <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">{eyebrow}</p>
            ) : null}
            <div className="space-y-3">
              <h2 className="max-w-4xl font-art text-[2.25rem] leading-[0.98] text-card-foreground md:text-[3.45rem]">
                {title}
              </h2>
              {description ? (
                <p className="max-w-2xl text-sm leading-7 text-muted-foreground md:text-[1rem]">
                  {description}
                </p>
              ) : null}
            </div>
            {pulse ? (
              <div className="inline-flex max-w-2xl items-start gap-3 rounded-full border border-white/50 bg-white/68 px-4 py-3 shadow-soft backdrop-blur-md">
                <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary/75 shadow-[0_0_0_6px_rgba(201,163,100,0.12)]" aria-hidden />
                <div className="text-sm leading-7 text-card-foreground">{pulse}</div>
              </div>
            ) : null}
          </div>

          {note ? <div className="xl:pt-2">{note}</div> : null}
        </div>

        {children ? <div>{children}</div> : null}
      </div>
    </section>
  );
}

export function EditorialMetricPill({
  icon: Icon,
  label,
  value,
  tone = 'warm',
  className,
}: EditorialMetricPillProps) {
  return (
    <div
      className={cn(
        'inline-flex min-w-[150px] items-center gap-3 rounded-full border px-4 py-3 shadow-soft backdrop-blur-md transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift',
        metricToneClassName[tone],
        className,
      )}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-white/50 bg-white/70 shadow-glass-inset">
        <Icon className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-[0.64rem] uppercase tracking-[0.28em] opacity-75">{label}</p>
        <p className="font-art text-lg leading-none text-card-foreground">{value}</p>
      </div>
    </div>
  );
}

export function HomeComposerStage({
  eyebrow,
  title,
  description,
  footer,
  children,
  className,
}: HomeComposerStageProps) {
  return (
    <GlassCard
      className={cn(
        'overflow-hidden border-white/50 bg-[linear-gradient(180deg,rgba(255,252,248,0.9),rgba(250,246,240,0.86))] p-0 shadow-lift',
        className,
      )}
    >
      <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
      <div className="relative flex flex-col gap-6 p-6 md:p-8">
        <div className="space-y-2">
          {eyebrow ? (
            <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">{eyebrow}</p>
          ) : null}
          <div className="space-y-2">
            <h3 className="font-art text-[1.7rem] leading-tight text-card-foreground md:text-[2rem]">
              {title}
            </h3>
            {description ? (
              <p className="max-w-2xl text-sm leading-7 text-muted-foreground md:text-[0.96rem]">
                {description}
              </p>
            ) : null}
          </div>
        </div>

        {children}
        {footer ? <div className="pt-2">{footer}</div> : null}
      </div>
    </GlassCard>
  );
}

export function EditorialPaperCard({
  eyebrow,
  title,
  description,
  tone = 'paper',
  children,
  className,
  contentClassName,
}: EditorialPaperCardProps) {
  return (
    <GlassCard
      className={cn(
        'overflow-hidden p-0',
        paperToneClassName[tone],
        className,
      )}
    >
      <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/22 to-transparent" aria-hidden />
      <div className={cn('relative space-y-5 p-5 md:p-6', contentClassName)}>
        {eyebrow || title || description ? (
          <div className="space-y-2">
            {eyebrow ? (
              <p className="text-[0.66rem] uppercase tracking-[0.28em] text-primary/80">{eyebrow}</p>
            ) : null}
            {title ? (
              <h4 className="font-art text-[1.25rem] leading-tight text-card-foreground">{title}</h4>
            ) : null}
            {description ? (
              <p className="text-sm leading-7 text-muted-foreground">{description}</p>
            ) : null}
          </div>
        ) : null}
        {children}
      </div>
    </GlassCard>
  );
}

export function HomeMosaicRail({ children, className }: HomeMosaicRailProps) {
  return (
    <div
      className={cn(
        'grid auto-rows-[minmax(170px,auto)] gap-4 md:grid-cols-2 xl:auto-rows-[minmax(160px,auto)]',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function HomeRailNav({ children, className }: HomeRailNavProps) {
  return (
    <div
      className={cn(
        'rounded-full border border-white/45 bg-white/66 p-1.5 shadow-soft backdrop-blur-xl',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function EditorialActionStrip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'rounded-[1.6rem] border border-white/45 bg-white/70 p-2 shadow-soft backdrop-blur-xl',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function EditorialTimelineColumn({
  eyebrow,
  title,
  description,
  aside,
  children,
  className,
}: EditorialTimelineColumnProps) {
  return (
    <section
      className={cn(
        'relative overflow-hidden rounded-[2.1rem] border border-white/40 bg-[linear-gradient(180deg,rgba(255,253,249,0.94),rgba(248,244,238,0.9))] p-6 shadow-soft md:p-8',
        className,
      )}
    >
      <div
        className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/22 to-transparent"
        aria-hidden
      />
      <div className="relative grid gap-6 xl:grid-cols-[220px_minmax(0,1fr)] xl:gap-10">
        <div className="space-y-3 xl:sticky xl:top-24 xl:self-start">
          {eyebrow ? (
            <p className="text-[0.72rem] uppercase tracking-[0.34em] text-primary/80">{eyebrow}</p>
          ) : null}
          <h3 className="font-art text-[1.8rem] leading-tight text-card-foreground">{title}</h3>
          {description ? (
            <p className="text-sm leading-7 text-muted-foreground md:text-[0.96rem]">{description}</p>
          ) : null}
          {aside ? <div className="pt-2">{aside}</div> : null}
        </div>

        <div className="relative space-y-8 before:absolute before:bottom-6 before:left-6 before:top-6 before:w-px before:bg-gradient-to-b before:from-primary/28 before:via-primary/14 before:to-transparent">
          {children}
        </div>
      </div>
    </section>
  );
}

export function TimelineDateRail({
  eyebrow,
  title,
  meta,
  className,
}: TimelineDateRailProps) {
  return (
    <div className={cn('space-y-1 xl:pt-8', className)}>
      <p className="text-[0.66rem] uppercase tracking-[0.26em] text-primary/80">{eyebrow}</p>
      <p className="font-art text-[1.55rem] text-card-foreground">{title}</p>
      <p className="text-xs leading-6 text-muted-foreground">{meta}</p>
    </div>
  );
}

export function EditorialStateCard({
  icon: Icon = Sparkles,
  eyebrow,
  title,
  description,
  actionLabel,
  onAction,
  tone = 'neutral',
  className,
}: EditorialStateCardProps) {
  return (
    <GlassCard
      className={cn(
        'flex flex-col items-start gap-4 overflow-hidden border p-7 md:p-8',
        stateToneClassName[tone],
        className,
      )}
    >
      <div className={cn('flex h-14 w-14 items-center justify-center rounded-[1.4rem] border shadow-soft', stateIconToneClassName[tone])}>
        <Icon className="h-6 w-6" aria-hidden />
      </div>
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-[0.68rem] uppercase tracking-[0.28em] text-primary/80">{eyebrow}</p>
        ) : null}
        <p className="font-art text-xl text-card-foreground">{title}</p>
        <p className="max-w-xl text-sm leading-7 text-muted-foreground">{description}</p>
      </div>
      {actionLabel && onAction ? (
        <Button
          type="button"
          variant={tone === 'sage' ? 'secondary' : 'outline'}
          size="md"
          onClick={onAction}
          rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
        >
          {actionLabel}
        </Button>
      ) : null}
    </GlassCard>
  );
}

export function EditorialEmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EditorialEmptyStateProps) {
  return (
    <EditorialStateCard
      icon={Icon}
      eyebrow="Empty Page"
      title={title}
      description={description}
      actionLabel={actionLabel}
      onAction={onAction}
      tone="warm"
      className={className}
    />
  );
}

export function EditorialDeferredState({
  icon: Icon = Sparkles,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EditorialDeferredStateProps) {
  return (
    <EditorialStateCard
      icon={Icon}
      eyebrow="Deferred"
      title={title}
      description={description}
      actionLabel={actionLabel}
      onAction={onAction}
      tone="sage"
      className={className}
    />
  );
}
