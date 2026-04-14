'use client';

import { CalendarCheck } from 'lucide-react';
import { EditorialPaperCard } from '@/features/home/HomePrimitives';
import { cn } from '@/lib/utils';
import type { WeeklyReportPublic } from '@/services/api-client';

interface WeeklyPulseCardProps {
  report: WeeklyReportPublic;
  streakDays: number;
  hasPartnerContext: boolean;
  className?: string;
}

const DAY_LABELS = ['一', '二', '三', '四', '五', '六', '日'] as const;

export default function WeeklyPulseCard({
  report,
  streakDays,
  hasPartnerContext,
  className,
}: WeeklyPulseCardProps) {
  const isEmpty =
    report.daily_sync_days_filled === 0 && report.appreciation_count === 0;

  return (
    <EditorialPaperCard
      tone="paper"
      className={cn('rounded-[2rem]', className)}
    >
      <div className="space-y-5">
        {/* ── 7-segment progress bar ── */}
        <div>
          <p className="type-caption text-muted-foreground mb-2.5">
            {report.period_start} — {report.period_end}
          </p>
          <div className="flex gap-1.5" role="img" aria-label={`本週同步 ${report.daily_sync_days_filled} / 7 天`}>
            {DAY_LABELS.map((label, i) => (
              <div key={label} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className={cn(
                    'h-2 w-full rounded-full transition-colors duration-haven ease-haven',
                    i < report.daily_sync_days_filled
                      ? 'bg-primary/30'
                      : 'bg-border/30',
                  )}
                />
                <span className="text-[0.6rem] tabular-nums text-muted-foreground/60">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {isEmpty ? (
          /* ── Empty state ── */
          <p className="type-caption text-muted-foreground leading-relaxed">
            這週才剛開始，從一篇日記或一則同步開始吧。
          </p>
        ) : (
          <>
            {/* ── Metric row ── */}
            <div
              className={cn(
                'grid gap-3',
                hasPartnerContext ? 'grid-cols-3' : 'grid-cols-2',
              )}
            >
              <div className="stat-box">
                <p className="type-caption text-muted-foreground">同步天數</p>
                <p className="text-lg font-semibold text-foreground tabular-nums">
                  {report.daily_sync_days_filled}
                  <span className="text-sm font-normal text-muted-foreground">
                    /7 天
                  </span>
                </p>
              </div>
              <div className="stat-box">
                <p className="type-caption text-muted-foreground">感謝紀錄</p>
                <p className="text-lg font-semibold text-foreground tabular-nums">
                  {report.appreciation_count}
                  <span className="text-sm font-normal text-muted-foreground">
                    {' '}則
                  </span>
                </p>
              </div>
              {hasPartnerContext ? (
                <div className="stat-box">
                  <p className="type-caption text-muted-foreground">雙人同步</p>
                  <p className="text-lg font-semibold text-foreground tabular-nums">
                    {report.pair_sync_overlap_days}
                    <span className="text-sm font-normal text-muted-foreground">
                      {' '}天
                    </span>
                  </p>
                </div>
              ) : null}
            </div>

            {/* ── Streak callout ── */}
            {streakDays >= 7 ? (
              <div className="flex items-center gap-2 rounded-xl bg-primary/6 px-3.5 py-2.5 border border-primary/10">
                <CalendarCheck className="h-4 w-4 shrink-0 text-primary" aria-hidden />
                <p className="type-caption text-foreground">
                  已連續 <strong className="font-semibold tabular-nums">{streakDays}</strong> 天一起寫日記
                </p>
              </div>
            ) : null}

            {/* ── AI insight ── */}
            {report.insight ? (
              <blockquote className="border-l-[3px] border-primary/40 pl-4 text-sm italic leading-relaxed text-foreground/85">
                {report.insight}
              </blockquote>
            ) : null}
          </>
        )}
      </div>
    </EditorialPaperCard>
  );
}
