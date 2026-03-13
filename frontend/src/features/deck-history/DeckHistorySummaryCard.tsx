'use client';

import Badge from '@/components/ui/Badge';
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
      <div className="stack-section">
        <div className="stack-block">
          <p className="type-micro uppercase text-primary/72">檔案概覽</p>
          <h2 className="type-h3 text-card-foreground">
            對話檔案館
          </h2>
          <p className="type-body-muted text-muted-foreground">
            這裡不是普通列表，而是你們已經走過的牌卡對話檔案。可以回看主題、回應與彼此最常打開的方向。
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-[1.5rem] border border-white/55 bg-white/72 p-4 shadow-soft">
            <p className="type-micro uppercase text-primary/70">總檔案數</p>
            <p className="mt-3 text-2xl font-semibold text-card-foreground tabular-nums">
              {summaryLoading ? '...' : summary.total_records}
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-white/55 bg-white/72 p-4 shadow-soft">
            <p className="type-micro uppercase text-primary/70">本月新增</p>
            <p className="mt-3 text-2xl font-semibold text-card-foreground tabular-nums">
              {summaryLoading ? '...' : summary.this_month_records}
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-white/55 bg-white/72 p-4 shadow-soft">
            <p className="type-micro uppercase text-primary/70">最常打開</p>
            <p className="mt-3 text-base font-semibold text-card-foreground">
              {summaryLoading ? '...' : summaryTopCategoryDisplay}
            </p>
          </div>
        </div>

        {!summaryLoading && summary.total_records > 0 ? (
          <div className="flex flex-wrap gap-3">
            <Badge variant="metadata" size="md" className="bg-white/70 tabular-nums text-muted-foreground">
              目前已載入 {historyLength}/{summary.total_records} 筆
            </Badge>
            {summary.top_category_count > 0 ? (
              <Badge variant="metadata" size="md" className="bg-white/70 tabular-nums text-muted-foreground">
                「{summaryTopCategoryDisplay}」累積 {summary.top_category_count} 次對話
              </Badge>
            ) : null}
          </div>
        ) : null}
      </div>
    </GlassCard>
  );
}
