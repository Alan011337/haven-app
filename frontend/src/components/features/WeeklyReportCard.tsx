'use client';

import { useEffect, useState, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
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
      <div className="flex min-h-[120px] items-center justify-center rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </div>
    );
  }

  const pct = Math.round(report.daily_sync_completion_rate * 100);
  return (
    <section className="relative overflow-hidden rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8">
      <p className="font-art text-base font-medium text-card-foreground mb-1">本週概覽</p>
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
    </section>
  );
}
