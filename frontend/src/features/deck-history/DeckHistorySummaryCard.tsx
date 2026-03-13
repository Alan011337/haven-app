'use client';

import { GlassCard } from '@/components/haven/GlassCard';
import type { DeckHistorySummary } from '@/services/deckService';

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
    <GlassCard className="overflow-hidden rounded-[2rem] border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(247,243,236,0.78))] p-6 md:p-7">
      <div className="space-y-5">
        <div className="space-y-2">
          <p className="text-[0.72rem] uppercase tracking-[0.32em] text-primary/72">檔案概覽</p>
          <h2 className="font-art text-[1.6rem] leading-tight text-card-foreground md:text-[2rem]">
            對話檔案館
          </h2>
          <p className="text-sm leading-7 text-muted-foreground">
            這裡不是普通列表，而是你們已經走過的牌卡對話檔案。可以回看主題、回應與彼此最常打開的方向。
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-[1.5rem] border border-white/55 bg-white/72 p-4 shadow-soft">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-primary/70">總檔案數</p>
            <p className="mt-3 text-2xl font-semibold text-card-foreground tabular-nums">
              {summaryLoading ? '...' : summary.total_records}
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-white/55 bg-white/72 p-4 shadow-soft">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-primary/70">本月新增</p>
            <p className="mt-3 text-2xl font-semibold text-card-foreground tabular-nums">
              {summaryLoading ? '...' : summary.this_month_records}
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-white/55 bg-white/72 p-4 shadow-soft">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-primary/70">最常打開</p>
            <p className="mt-3 text-base font-semibold text-card-foreground">
              {summaryLoading ? '...' : summaryTopCategoryDisplay}
            </p>
          </div>
        </div>

        {!summaryLoading && summary.total_records > 0 ? (
          <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
            <span className="rounded-full border border-white/55 bg-white/70 px-4 py-2 tabular-nums">
              目前已載入 {historyLength}/{summary.total_records} 筆
            </span>
            {summary.top_category_count > 0 ? (
              <span className="rounded-full border border-white/55 bg-white/70 px-4 py-2 tabular-nums">
                「{summaryTopCategoryDisplay}」累積 {summary.top_category_count} 次對話
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </GlassCard>
  );
}
