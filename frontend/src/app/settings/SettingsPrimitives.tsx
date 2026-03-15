'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { cn } from '@/lib/utils';

type SettingsTone = 'default' | 'quiet' | 'success' | 'error';

const toneClasses: Record<SettingsTone, string> = {
  default: 'border-white/56 bg-white/82',
  quiet: 'border-primary/12 bg-white/76',
  success:
    'border-accent/18 bg-[linear-gradient(180deg,rgba(250,253,250,0.96),rgba(240,246,239,0.93))]',
  error:
    'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,250,248,0.96),rgba(248,240,236,0.94))]',
};

function toneBadgeVariant(tone: SettingsTone) {
  if (tone === 'success') return 'success';
  if (tone === 'error') return 'destructive';
  return 'metadata';
}

function toneIcon(tone: SettingsTone) {
  if (tone === 'success') return <CheckCircle2 className="h-4 w-4" aria-hidden />;
  if (tone === 'error') return <ShieldAlert className="h-4 w-4" aria-hidden />;
  return <ShieldCheck className="h-4 w-4" aria-hidden />;
}

export interface SettingsShellProps {
  children: ReactNode;
}

export function SettingsShell({ children }: SettingsShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.16),transparent_26%),radial-gradient(circle_at_86%_10%,rgba(231,236,232,0.48),transparent_30%),linear-gradient(180deg,#fcfaf6_0%,#f5efe7_46%,#eee6db_100%)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-28" aria-hidden />
      <div className="pointer-events-none absolute -left-10 top-16 h-72 w-72 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute right-[-4rem] top-28 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-4rem] right-14 h-72 w-72 rounded-full bg-primary/7 blur-hero-orb-sm" aria-hidden />

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

          <Badge
            variant="metadata"
            size="md"
            className="border-white/54 bg-white/74 text-primary/78 shadow-soft"
          >
            Trust &amp; Customization Center
          </Badge>
        </div>

        {children}
      </div>
    </div>
  );
}

export interface SettingsCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  actions?: ReactNode;
  highlights?: ReactNode;
  featured: ReactNode;
  aside: ReactNode;
}

export function SettingsCover({
  eyebrow,
  title,
  description,
  pulse,
  actions,
  highlights,
  featured,
  aside,
}: SettingsCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.95),rgba(246,239,230,0.9))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.74),transparent_36%),radial-gradient(circle_at_84%_12%,rgba(255,255,255,0.34),transparent_22%)]"
        aria-hidden
      />
      <div className="pointer-events-none absolute right-[-4rem] top-[-2rem] h-72 w-72 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-3rem] left-[-1rem] h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] xl:gap-8">
        <div className="space-y-6">
          <div className="space-y-4">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-3">
              <h1 className="max-w-[56rem] type-h1 text-card-foreground">{title}</h1>
              <p className="max-w-[46rem] type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>

          <div className="inline-flex max-w-3xl items-start gap-3 rounded-[1.9rem] border border-white/56 bg-white/72 px-4 py-4 shadow-soft backdrop-blur-md">
            <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <ShieldCheck className="h-4 w-4" aria-hidden />
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

export interface SettingsSnapshotCardProps {
  eyebrow: string;
  title: string;
  description: string;
  tone?: SettingsTone;
  icon?: ReactNode;
  footer?: ReactNode;
}

export function SettingsSnapshotCard({
  eyebrow,
  title,
  description,
  tone = 'default',
  icon,
  footer,
}: SettingsSnapshotCardProps) {
  return (
    <GlassCard
      className={cn(
        'overflow-hidden rounded-[2.25rem] p-5 md:p-6',
        toneClasses[tone],
      )}
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
            <div className="space-y-1">
              <h2 className="type-h3 text-card-foreground">{title}</h2>
              <p className="type-body-muted text-muted-foreground">{description}</p>
            </div>
          </div>
          {icon ? (
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[1.1rem] border border-white/60 bg-white/74 text-primary shadow-soft">
              {icon}
            </span>
          ) : null}
        </div>
        {footer}
      </div>
    </GlassCard>
  );
}

export interface SettingsSectionRailItem {
  id: string;
  label: string;
  description: string;
}

export interface SettingsSectionRailProps {
  items: SettingsSectionRailItem[];
  onNavigate: (id: string) => void;
}

export function SettingsSectionRail({ items, onNavigate }: SettingsSectionRailProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.4rem] border-white/54 bg-white/80 p-4 md:p-5">
      <div className="grid gap-3 lg:grid-cols-4">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className="group flex min-h-[92px] flex-col items-start justify-between rounded-[1.65rem] border border-white/58 bg-white/74 p-4 text-left shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:border-primary/16 hover:shadow-lift focus-ring-premium"
          >
            <div className="space-y-2">
              <p className="type-section-title text-card-foreground">{item.label}</p>
              <p className="type-caption text-muted-foreground">{item.description}</p>
            </div>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-primary/86">
              前往
              <ChevronRight className="h-4 w-4 transition-transform duration-haven ease-haven group-hover:translate-x-0.5" aria-hidden />
            </span>
          </button>
        ))}
      </div>
    </GlassCard>
  );
}

export interface SettingsSectionProps {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  aside?: ReactNode;
}

export function SettingsSection({
  id,
  eyebrow,
  title,
  description,
  children,
  aside,
}: SettingsSectionProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <GlassCard className="overflow-hidden rounded-[2.8rem] border-white/54 bg-white/82 p-5 md:p-7 xl:p-8">
        <div className={cn('grid gap-6 xl:gap-8', aside ? 'xl:grid-cols-[minmax(0,1fr)_320px]' : '')}>
          <div className="space-y-6">
            <div className="space-y-3">
              <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
              <div className="space-y-2">
                <h2 className="type-h2 text-card-foreground">{title}</h2>
                <p className="max-w-3xl type-body-muted text-muted-foreground">{description}</p>
              </div>
            </div>
            {children}
          </div>
          {aside ? <div className="space-y-4">{aside}</div> : null}
        </div>
      </GlassCard>
    </section>
  );
}

export interface SettingsFieldRowProps {
  label: string;
  description: string;
  control: ReactNode;
  className?: string;
}

export function SettingsFieldRow({
  label,
  description,
  control,
  className,
}: SettingsFieldRowProps) {
  return (
    <div
      className={cn(
        'grid gap-4 rounded-[1.7rem] border border-white/56 bg-white/74 p-4 shadow-soft md:grid-cols-[minmax(0,1fr)_auto] md:items-center md:gap-5 md:p-5',
        className,
      )}
    >
      <div className="space-y-1.5">
        <p className="type-section-title text-card-foreground">{label}</p>
        <p className="type-caption text-muted-foreground">{description}</p>
      </div>
      <div className="md:justify-self-end">{control}</div>
    </div>
  );
}

export interface SettingsChoiceOption {
  value: string;
  label: string;
  description: string;
  eyebrow?: string;
}

export interface SettingsChoiceGridProps {
  legend: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: SettingsChoiceOption[];
  columns?: 2 | 3 | 4;
}

export function SettingsChoiceGrid({
  legend,
  name,
  value,
  onChange,
  options,
  columns = 2,
}: SettingsChoiceGridProps) {
  const columnClass =
    columns === 4 ? 'md:grid-cols-2 xl:grid-cols-4' : columns === 3 ? 'md:grid-cols-3' : 'md:grid-cols-2';

  return (
    <fieldset className="space-y-3">
      <legend className="type-section-title text-card-foreground">{legend}</legend>
      <div className={cn('grid gap-3', columnClass)}>
        {options.map((option) => {
          const checked = value === option.value;
          return (
            <label
              key={option.value}
              className={cn(
                'group block cursor-pointer rounded-[1.7rem] border p-4 shadow-soft transition-all duration-haven ease-haven focus-within:shadow-focus-glow',
                checked
                  ? 'border-primary/26 bg-[linear-gradient(165deg,rgba(255,252,247,0.96),rgba(246,239,229,0.93))] shadow-lift'
                  : 'border-white/58 bg-white/74 hover:-translate-y-0.5 hover:border-primary/14 hover:shadow-lift',
              )}
            >
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={checked}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />
              <div className="space-y-2">
                {option.eyebrow ? <p className="type-micro uppercase text-primary/76">{option.eyebrow}</p> : null}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="type-section-title text-card-foreground">{option.label}</p>
                    <p className="mt-1 type-caption text-muted-foreground">{option.description}</p>
                  </div>
                  <span
                    className={cn(
                      'mt-0.5 h-4 w-4 rounded-full border transition-colors duration-haven ease-haven',
                      checked ? 'border-primary bg-primary shadow-soft' : 'border-border bg-white/75',
                    )}
                    aria-hidden
                  />
                </div>
              </div>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export interface SettingsSwitchProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}

export function SettingsSwitch({ checked, onChange, label }: SettingsSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border-2 border-transparent transition-colors duration-haven ease-haven focus-ring-premium',
        checked ? 'bg-primary shadow-satin-button' : 'bg-muted-foreground/25',
      )}
    >
      <span
        className={cn(
          'pointer-events-none block h-[1.125rem] w-[1.125rem] rounded-full bg-white shadow-sm transition-transform duration-haven ease-haven-spring',
          checked ? 'translate-x-5' : 'translate-x-0.5',
        )}
      />
    </button>
  );
}

export interface SettingsStatePanelProps {
  tone?: SettingsTone;
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

export function SettingsStatePanel({
  tone = 'quiet',
  eyebrow,
  title,
  description,
  actions,
}: SettingsStatePanelProps) {
  return (
    <GlassCard className={cn('overflow-hidden rounded-[2.2rem] p-5 md:p-6', toneClasses[tone])}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={toneBadgeVariant(tone)} size="sm" className="border-white/56 bg-white/74">
            {eyebrow}
          </Badge>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/78 text-primary shadow-soft">
            {toneIcon(tone)}
          </span>
        </div>
        <div className="space-y-2">
          <h3 className="type-h3 text-card-foreground">{title}</h3>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </GlassCard>
  );
}

export interface SettingsFooterNoteProps {
  title: string;
  description: string;
  actions?: ReactNode;
}

export function SettingsFooterNote({
  title,
  description,
  actions,
}: SettingsFooterNoteProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.4rem] border-white/52 bg-white/78 p-5 md:p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="type-micro uppercase text-primary/78">Quiet Assurance</p>
          <h2 className="type-h3 text-card-foreground">{title}</h2>
          <p className="type-body-muted text-muted-foreground">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </GlassCard>
  );
}

export function SettingsSecondaryAction({
  label,
  onClick,
  disabled,
  icon,
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  icon?: ReactNode;
}) {
  return (
    <Button
      variant="secondary"
      size="md"
      onClick={onClick}
      disabled={disabled}
      leftIcon={icon}
      className="border-white/58 bg-white/78"
    >
      {label}
    </Button>
  );
}
