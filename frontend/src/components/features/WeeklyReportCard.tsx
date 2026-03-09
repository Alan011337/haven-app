'use client';

import { useEffect, useState, useCallback } from 'react';
import { BarChart2, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import { fetchWeeklyReport, type WeeklyReportPublic } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';

export default function WeeklyReportCard() {
  const [report, setReport] = useState<WeeklyReportPublic | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await fetchWeeklyReport();
      setReport(r);
    } catch (e) {
      logClientError('weekly-report-fetch-failed', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading || !report) {
    return (
      <GlassCard className="mb-6 p-6 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  const pct = Math.round(report.daily_sync_completion_rate * 100);
  return (
    <GlassCard className="mb-6 p-6 md:p-8 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <BarChart2 className="w-5 h-5 text-primary" aria-hidden />
        </span>
        本週週報
      </h3>
      <p className="text-caption text-muted-foreground mb-4 tabular-nums">
        {report.period_start} ~ {report.period_end}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 animate-slide-up-fade">
        <div className="stat-box">
          <p className="text-caption text-muted-foreground">每日同步完成率</p>
          <p className="text-title font-semibold text-gradient-gold tabular-nums">{pct}%</p>
          <p className="text-caption text-muted-foreground tabular-nums">（{report.daily_sync_days_filled}/7 天）</p>
        </div>
        <div className="stat-box">
          <p className="text-caption text-muted-foreground">感謝與被感謝</p>
          <p className="text-title font-semibold text-gradient-gold tabular-nums">{report.appreciation_count} 則</p>
        </div>
      </div>
      {report.insight && (
        <blockquote className="mt-4 pl-4 border-l-[3px] border-primary/40 text-body text-foreground italic animate-slide-up-fade-1">
          {report.insight}
        </blockquote>
      )}
    </GlassCard>
  );
}
