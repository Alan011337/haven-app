'use client';

import type { DeckHistorySummary } from '@/services/deckService';
import { GlassCard } from '@/components/haven/GlassCard';

interface DeckHistorySummaryCardProps {
  summary: DeckHistorySummary;
  summaryLoading: boolean;
  summaryTopCategoryDisplay: string;
  historyLength: number;
}

export default function DeckHistorySummaryCard({
  summary,
  summaryLoading,
  summaryTopCategoryDisplay,
  historyLength,
}: DeckHistorySummaryCardProps) {
  return (
    <GlassCard role="region" aria-label="History Snapshot" className="p-5 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <p className="text-[11px] font-art font-semibold tracking-[0.16em] text-muted-foreground uppercase">
        History Snapshot
      </p>
      <div className="mt-3 grid grid-cols-3 gap-3">
        <div className="stat-box animate-slide-up-fade">
          <p className="text-[10px] text-muted-foreground">總回顧</p>
          <p className="text-lg font-bold text-card-foreground tabular-nums">
            {summaryLoading ? '...' : summary.total_records}
          </p>
        </div>
        <div className="stat-box animate-slide-up-fade-1">
          <p className="text-[10px] text-muted-foreground">本月新增</p>
          <p className="text-lg font-bold text-card-foreground tabular-nums">
            {summaryLoading ? '...' : summary.this_month_records}
          </p>
        </div>
        <div className="stat-box animate-slide-up-fade-2">
          <p className="text-[10px] text-muted-foreground">最常聊</p>
          <p className="text-sm font-bold text-card-foreground truncate">
            {summaryLoading ? '...' : summaryTopCategoryDisplay}
          </p>
        </div>
      </div>
      {!summaryLoading && summary.total_records > 0 && (
        <p className="mt-3 text-xs text-muted-foreground tabular-nums">
          目前已載入 {historyLength}/{summary.total_records} 筆紀錄。
        </p>
      )}
      {!summaryLoading && summary.top_category_count > 0 && (
        <p className="mt-3 text-xs text-muted-foreground tabular-nums">
          「{summaryTopCategoryDisplay}」已累積 {summary.top_category_count} 次對話解鎖。
        </p>
      )}
    </GlassCard>
  );
}
