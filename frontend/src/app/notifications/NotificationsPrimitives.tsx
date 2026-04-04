'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  BookOpen,
  Clock3,
  HandHeart,
  HeartHandshake,
  MailWarning,
  MessageCircleMore,
  PauseCircle,
  RefreshCw,
} from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import type { NotificationDailyStatsItem, NotificationEventItem } from '@/services/api-client';

type NotificationsStateTone = 'default' | 'quiet' | 'error';

const stateToneClasses: Record<NotificationsStateTone, string> = {
  default: 'border-white/56 bg-white/84',
  quiet: 'border-primary/12 bg-white/78',
  error:
    'border-destructive/16 bg-[linear-gradient(180deg,rgba(255,250,248,0.96),rgba(248,240,236,0.94))]',
};

const actionTypeLabelMap: Record<NotificationEventItem['action_type'], string> = {
  JOURNAL: '日記更新',
  CARD: '卡片回覆',
  COOLDOWN_STARTED: '冷卻提醒',
  MEDIATION_INVITE: '調解邀請',
};

const statusLabelMap: Record<NotificationEventItem['status'], string> = {
  QUEUED: '排程中',
  SENT: '已送達',
  FAILED: '需要補送',
  THROTTLED: '節奏放緩',
};

function NotificationIcon({
  actionType,
  className,
}: {
  actionType: NotificationEventItem['action_type'];
  className?: string;
}) {
  if (actionType === 'JOURNAL') return <BookOpen className={className} aria-hidden />;
  if (actionType === 'MEDIATION_INVITE') return <HandHeart className={className} aria-hidden />;
  if (actionType === 'COOLDOWN_STARTED') return <PauseCircle className={className} aria-hidden />;
  return <MessageCircleMore className={className} aria-hidden />;
}

function getStatusBadgeVariant(
  status: NotificationEventItem['status'],
): 'success' | 'warning' | 'destructive' | 'status' {
  if (status === 'FAILED') return 'destructive';
  if (status === 'THROTTLED' || status === 'QUEUED') return 'warning';
  if (status === 'SENT') return 'success';
  return 'status';
}

function getFeaturedTone(status: NotificationEventItem['status']) {
  if (status === 'FAILED') {
    return 'border-destructive/18 bg-[linear-gradient(165deg,rgba(255,249,247,0.97),rgba(248,236,231,0.94))]';
  }
  if (status === 'THROTTLED') {
    return 'border-primary/16 bg-[linear-gradient(165deg,rgba(255,251,246,0.97),rgba(246,237,226,0.94))]';
  }
  if (status === 'QUEUED') {
    return 'border-primary/18 bg-[linear-gradient(165deg,rgba(251,252,255,0.97),rgba(237,241,247,0.94))]';
  }
  return 'border-white/54 bg-[linear-gradient(165deg,rgba(255,253,250,0.97),rgba(242,238,231,0.94))]';
}

function getRowTone(status: NotificationEventItem['status'], unread: boolean) {
  if (status === 'FAILED') {
    return 'border-destructive/14 bg-[linear-gradient(165deg,rgba(255,249,247,0.95),rgba(249,241,236,0.93))]';
  }
  if (status === 'THROTTLED') {
    return 'border-primary/14 bg-[linear-gradient(165deg,rgba(255,252,247,0.95),rgba(247,240,231,0.93))]';
  }
  if (unread) {
    return 'border-primary/14 bg-[linear-gradient(165deg,rgba(255,253,250,0.95),rgba(244,238,230,0.93))]';
  }
  return 'border-white/52 bg-white/78';
}

interface NotificationsShellProps {
  children: ReactNode;
}

export function NotificationsShell({ children }: NotificationsShellProps) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fbf8f3_0%,#f5efe7_46%,#eee7dc_100%)]">
      <Sidebar />

      <main className="relative min-h-screen overflow-hidden pt-14 md:ml-64 md:pt-0">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_26%),radial-gradient(circle_at_82%_10%,rgba(226,234,237,0.52),transparent_26%),linear-gradient(180deg,rgba(255,255,255,0.24),transparent_32%)]"
          aria-hidden
        />
        <div className="pointer-events-none absolute inset-0 bg-ethereal-mesh opacity-28" aria-hidden />
        <div className="pointer-events-none absolute -left-12 top-20 h-72 w-72 rounded-full bg-primary/8 blur-hero-orb" aria-hidden />
        <div className="pointer-events-none absolute right-[-4rem] top-32 h-80 w-80 rounded-full bg-accent/10 blur-hero-orb" aria-hidden />
        <div className="pointer-events-none absolute bottom-[-5rem] right-8 h-80 w-80 rounded-full bg-primary/7 blur-hero-orb-sm" aria-hidden />

        <div className="relative z-10 mx-auto max-w-[1540px] space-y-[clamp(1.5rem,3vw,2.75rem)] px-4 pb-16 pt-6 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}

interface NotificationsCoverProps {
  eyebrow: string;
  title: string;
  description: string;
  pulse: string;
  actions?: ReactNode;
  highlights?: ReactNode;
  featured: ReactNode;
  aside: ReactNode;
}

export function NotificationsCover({
  eyebrow,
  title,
  description,
  pulse,
  actions,
  highlights,
  featured,
  aside,
}: NotificationsCoverProps) {
  return (
    <section className="relative overflow-hidden rounded-[3.1rem] border border-white/56 bg-[linear-gradient(165deg,rgba(255,253,250,0.96),rgba(244,238,230,0.92))] p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.74),transparent_34%),radial-gradient(circle_at_82%_14%,rgba(255,255,255,0.36),transparent_22%)]"
        aria-hidden
      />
      <div className="pointer-events-none absolute right-[-3rem] top-[-3rem] h-72 w-72 rounded-full bg-primary/10 blur-hero-orb" aria-hidden />
      <div className="pointer-events-none absolute bottom-[-4rem] left-[-2rem] h-64 w-64 rounded-full bg-accent/10 blur-hero-orb-sm" aria-hidden />

      <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)] xl:gap-8">
        <div className="space-y-6">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="metadata" size="md" className="border-white/56 bg-white/76 text-primary/82 shadow-soft">
                Notifications
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

interface NotificationsOverviewCardProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}

export function NotificationsOverviewCard({
  eyebrow,
  title,
  description,
  children,
}: NotificationsOverviewCardProps) {
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

interface NotificationsFocusBarProps {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}

export function NotificationsFocusBar({
  eyebrow,
  title,
  description,
  children,
}: NotificationsFocusBarProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.65rem] border-white/54 bg-white/82 p-5 shadow-soft backdrop-blur-xl md:p-6 xl:p-7">
      <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)] xl:gap-8">
        <div className="space-y-3">
          <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
          <div className="space-y-2">
            <h2 className="type-h3 text-card-foreground">{title}</h2>
            <p className="type-body-muted text-muted-foreground">{description}</p>
          </div>
        </div>
        <div className="rounded-[2rem] border border-white/56 bg-white/72 p-4 shadow-soft backdrop-blur-md md:p-5">
          {children}
        </div>
      </div>
    </GlassCard>
  );
}

interface NotificationsSectionProps {
  eyebrow: string;
  title: string;
  description: string;
  count: number;
  children: ReactNode;
}

export function NotificationsSection({
  eyebrow,
  title,
  description,
  count,
  children,
}: NotificationsSectionProps) {
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
        <Badge variant={count > 0 ? 'count' : 'metadata'} size="md" className={count > 0 ? '' : 'border-white/54 bg-white/72'}>
          {count} 則
        </Badge>
      </div>
      {children}
    </section>
  );
}

interface NotificationFeaturedCardProps {
  actionType: NotificationEventItem['action_type'];
  status: NotificationEventItem['status'];
  eyebrow: string;
  title: string;
  description: string;
  timeLabel: string;
  badges?: string[];
  unread?: boolean;
  support?: string;
  errorMessage?: string | null;
  actions?: ReactNode;
}

export function NotificationFeaturedCard({
  actionType,
  status,
  eyebrow,
  title,
  description,
  timeLabel,
  badges = [],
  unread = false,
  support,
  errorMessage,
  actions,
}: NotificationFeaturedCardProps) {
  return (
    <GlassCard className={cn('overflow-hidden rounded-[2.8rem] p-6 shadow-lift backdrop-blur-xl md:p-8', getFeaturedTone(status))}>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <Badge variant={getStatusBadgeVariant(status)} size="sm">
                {statusLabelMap[status]}
              </Badge>
              <Badge variant="metadata" size="sm" className="border-white/54 bg-white/72">
                {actionTypeLabelMap[actionType]}
              </Badge>
              {unread ? (
                <Badge variant="default" size="sm">
                  尚未閱讀
                </Badge>
              ) : null}
            </div>
            <div className="space-y-2">
              <p className="type-micro uppercase text-primary/80">{eyebrow}</p>
              <h3 className="type-h2 text-card-foreground">{title}</h3>
              <p className="max-w-4xl type-body-muted text-card-foreground/84">{description}</p>
            </div>
          </div>

          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[1.65rem] border border-white/60 bg-white/78 text-primary shadow-soft">
            <NotificationIcon actionType={actionType} className="h-5 w-5" />
          </span>
        </div>

        {support ? (
          <div className="rounded-[2rem] border border-white/58 bg-white/72 p-4 shadow-soft backdrop-blur-md">
            <p className="type-body-muted text-card-foreground">{support}</p>
          </div>
        ) : null}

        {badges.length ? (
          <div className="flex flex-wrap items-center gap-2">
            {badges.map((badge) => (
              <Badge key={badge} variant="outline" size="sm" className="border-white/54 bg-white/68">
                {badge}
              </Badge>
            ))}
          </div>
        ) : null}

        {errorMessage ? (
          <div className="inline-flex items-start gap-2 rounded-[1.2rem] border border-destructive/16 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <MailWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{errorMessage}</span>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Clock3 className="h-4 w-4" aria-hidden />
            <span className="tabular-nums">{timeLabel}</span>
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
        </div>
      </div>
    </GlassCard>
  );
}

interface NotificationPulseRowProps {
  actionType: NotificationEventItem['action_type'];
  status: NotificationEventItem['status'];
  title: string;
  description: string;
  timeLabel: string;
  unread?: boolean;
  support?: string;
  errorMessage?: string | null;
  actions?: ReactNode;
}

export function NotificationPulseRow({
  actionType,
  status,
  title,
  description,
  timeLabel,
  unread = false,
  support,
  errorMessage,
  actions,
}: NotificationPulseRowProps) {
  return (
    <GlassCard
      className={cn(
        'overflow-hidden rounded-[2rem] p-5 shadow-soft backdrop-blur-md transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift md:p-6',
        getRowTone(status, unread),
      )}
    >
      <div className="grid gap-4 md:grid-cols-[auto_minmax(0,1fr)] md:gap-5">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[1.3rem] border border-white/60 bg-white/78 text-primary shadow-soft">
          <NotificationIcon actionType={actionType} className="h-[18px] w-[18px]" />
        </span>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant={getStatusBadgeVariant(status)} size="sm">
              {statusLabelMap[status]}
            </Badge>
            <Badge variant="metadata" size="sm" className="border-white/54 bg-white/72">
              {actionTypeLabelMap[actionType]}
            </Badge>
            {unread ? (
              <span className="inline-flex h-2.5 w-2.5 rounded-full bg-primary" aria-hidden />
            ) : null}
          </div>

          <div className="space-y-2">
            <h3 className="type-section-title text-card-foreground">{title}</h3>
            <p className="type-body-muted text-muted-foreground">{description}</p>
            {support ? <p className="type-caption text-card-foreground/72">{support}</p> : null}
          </div>

          {errorMessage ? (
            <div className="inline-flex items-start gap-2 rounded-[1rem] border border-destructive/16 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <MailWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span>{errorMessage}</span>
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Clock3 className="h-4 w-4" aria-hidden />
              <span className="tabular-nums">{timeLabel}</span>
            </div>
            {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

interface NotificationsDiagnosticsRailProps {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}

export function NotificationsDiagnosticsRail({
  eyebrow,
  title,
  description,
  children,
}: NotificationsDiagnosticsRailProps) {
  return (
    <aside className="space-y-4">
      <NotificationsOverviewCard eyebrow={eyebrow} title={title} description={description}>
        <div className="grid gap-3">{children}</div>
      </NotificationsOverviewCard>
    </aside>
  );
}

interface NotificationsTrendCardProps {
  windowDays: 7 | 30;
  days: NotificationDailyStatsItem[];
  trendMax: number;
  focusedDay: NotificationDailyStatsItem | null;
  onWindowChange: (next: 7 | 30) => void;
  onHoverDay: (day: NotificationDailyStatsItem | null) => void;
}

export function NotificationsTrendCard({
  windowDays,
  days,
  trendMax,
  focusedDay,
  onWindowChange,
  onHoverDay,
}: NotificationsTrendCardProps) {
  return (
    <GlassCard className="overflow-hidden rounded-[2.25rem] border-white/52 bg-white/78 p-5 shadow-soft md:p-6">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-2">
            <p className="type-micro uppercase text-primary/80">Trend Window</p>
            <h3 className="type-section-title text-card-foreground">近期節奏</h3>
            <p className="type-body-muted text-muted-foreground">安靜地看見最近 {windowDays} 天的送達、延遲與補送需求。</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {[7, 30].map((window) => (
              <Button
                key={window}
                size="sm"
                variant={windowDays === window ? 'primary' : 'outline'}
                onClick={() => onWindowChange(window as 7 | 30)}
                aria-pressed={windowDays === window}
                aria-label={`切換為最近 ${window} 天`}
              >
                {window} 天
              </Button>
            ))}
          </div>
        </div>

        {days.length ? (
          <div className="space-y-4">
            <div className="flex h-36 items-end gap-2 overflow-x-auto pb-1">
              {days.map((day) => {
                const totalHeight = Math.max(10, Math.round((day.total_count / trendMax) * 100));
                const isFocused = focusedDay?.date === day.date;
                const label = `${day.date}，總計 ${day.total_count}，已送達 ${day.sent_count}，失敗 ${day.failed_count}，節流 ${day.throttled_count}，排程中 ${day.queued_count}`;
                return (
                  <button
                    key={day.date}
                    type="button"
                    onMouseEnter={() => onHoverDay(day)}
                    onMouseLeave={() => onHoverDay(null)}
                    onFocus={() => onHoverDay(day)}
                    onBlur={() => onHoverDay(null)}
                    aria-label={label}
                    className={cn(
                      'group flex min-w-[28px] flex-1 flex-col items-center gap-2 focus-ring-premium',
                      isFocused ? 'opacity-100' : 'opacity-82 hover:opacity-100',
                    )}
                  >
                    <div
                      className={cn(
                        'flex w-full flex-col-reverse overflow-hidden rounded-[1rem] border border-white/54 bg-muted/45 transition-all duration-haven ease-haven group-hover:shadow-soft',
                        isFocused ? 'shadow-soft ring-1 ring-primary/14' : '',
                      )}
                      style={{ height: `${totalHeight}%` }}
                    >
                      {day.total_count > 0 ? (
                        <>
                          {day.queued_count > 0 ? (
                            <div style={{ height: `${(day.queued_count / day.total_count) * 100}%` }} className="bg-primary/35" aria-hidden />
                          ) : null}
                          {day.throttled_count > 0 ? (
                            <div style={{ height: `${(day.throttled_count / day.total_count) * 100}%` }} className="bg-primary/55" aria-hidden />
                          ) : null}
                          {day.failed_count > 0 ? (
                            <div style={{ height: `${(day.failed_count / day.total_count) * 100}%` }} className="bg-destructive/82" aria-hidden />
                          ) : null}
                          {day.sent_count > 0 ? (
                            <div style={{ height: `${(day.sent_count / day.total_count) * 100}%` }} className="bg-accent/85" aria-hidden />
                          ) : null}
                        </>
                      ) : (
                        <div className="h-full w-full bg-white/48" aria-hidden />
                      )}
                    </div>
                    <span className="type-caption tabular-nums text-muted-foreground">{day.date.slice(5)}</span>
                  </button>
                );
              })}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-accent/85" aria-hidden />
                已送達
              </span>
              <span className="inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-destructive/82" aria-hidden />
                補送需求
              </span>
              <span className="inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-primary/55" aria-hidden />
                節流
              </span>
              <span className="inline-flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-primary/35" aria-hidden />
                排程中
              </span>
            </div>
          </div>
        ) : (
          <NotificationsStatePanel
            tone="quiet"
            eyebrow="Trend Window"
            title="目前還沒有足夠的趨勢資料"
            description="等通知累積起來後，這裡會顯示最近一段時間的送達節奏。"
          />
        )}

        <div className="rounded-[1.7rem] border border-white/56 bg-white/72 p-4 shadow-soft backdrop-blur-md">
          <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Focused Day</p>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-muted-foreground">
            <div>
              <p className="font-medium text-card-foreground">{focusedDay?.date ?? '尚無資料'}</p>
              <p className="mt-1 tabular-nums">總計 {focusedDay?.total_count ?? 0}</p>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 tabular-nums">
              <span>送達 {focusedDay?.sent_count ?? 0}</span>
              <span>失敗 {focusedDay?.failed_count ?? 0}</span>
              <span>節流 {focusedDay?.throttled_count ?? 0}</span>
              <span>排程 {focusedDay?.queued_count ?? 0}</span>
            </div>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

interface NotificationsStatePanelProps {
  tone?: NotificationsStateTone;
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

export function NotificationsStatePanel({
  tone = 'default',
  eyebrow,
  title,
  description,
  actions,
}: NotificationsStatePanelProps) {
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
              <AlertTriangle className="h-[18px] w-[18px]" aria-hidden />
            ) : (
              <Bell className="h-[18px] w-[18px]" aria-hidden />
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

interface NotificationLinkActionProps {
  href: string;
  label?: string;
}

export function NotificationLinkAction({
  href,
  label = '前往查看',
}: NotificationLinkActionProps) {
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

interface NotificationRetryActionProps {
  loading?: boolean;
  onClick: () => void;
}

export function NotificationRetryAction({
  loading = false,
  onClick,
}: NotificationRetryActionProps) {
  return (
    <Button
      size="sm"
      variant="outline"
      loading={loading}
      leftIcon={!loading ? <RefreshCw className="h-4 w-4" aria-hidden /> : undefined}
      onClick={onClick}
      aria-label="重新嘗試投遞通知"
    >
      重送通知
    </Button>
  );
}
