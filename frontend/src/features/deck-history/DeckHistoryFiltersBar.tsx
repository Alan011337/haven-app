'use client';

import { DECK_META_LIST } from '@/lib/deck-meta';
import type { DateRangeMode, SortMode } from './useDeckHistory';

interface DeckHistoryFiltersBarProps {
  normalizedCategoryFilter: string | null;
  dateRangeMode: DateRangeMode;
  sortMode: SortMode;
  searchKeyword: string;
  setCategoryQuery: (category?: string) => void;
  setDateRangeQuery: (mode: DateRangeMode) => void;
  setSortQuery: (mode: SortMode) => void;
  setSearchKeyword: (value: string) => void;
  onExportCsv: () => void;
}

export default function DeckHistoryFiltersBar({
  normalizedCategoryFilter,
  dateRangeMode,
  sortMode,
  searchKeyword,
  setCategoryQuery,
  setDateRangeQuery,
  setSortQuery,
  setSearchKeyword,
  onExportCsv,
}: DeckHistoryFiltersBarProps) {
  const chipClass = (active: boolean) =>
    active
      ? 'border-primary/18 bg-primary/10 text-card-foreground shadow-soft'
      : 'border-white/55 bg-white/70 text-muted-foreground hover:border-primary/16 hover:text-card-foreground';

  return (
    <section className="rounded-[2rem] border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(248,244,238,0.78))] p-5 shadow-soft md:p-6">
      <div className="space-y-5">
        <div className="space-y-2">
          <p className="text-[0.72rem] uppercase tracking-[0.32em] text-primary/72">檔案整理</p>
          <h3 className="font-art text-[1.4rem] text-card-foreground">按時間、牌組與關鍵字整理這些對話。</h3>
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setCategoryQuery(undefined)}
              className={`rounded-full border px-4 py-2 text-xs font-medium transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${chipClass(!normalizedCategoryFilter)}`}
            >
              全部牌組
            </button>
            {DECK_META_LIST.map((deck) => {
              const active = normalizedCategoryFilter === deck.id;
              return (
                <button
                  key={deck.id}
                  type="button"
                  onClick={() => setCategoryQuery(deck.id)}
                  className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-medium transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${chipClass(active)}`}
                >
                  <deck.Icon className="h-3.5 w-3.5" strokeWidth={2.2} aria-hidden />
                  {deck.title}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap gap-2">
            {(['all', '7d', '30d'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setDateRangeQuery(mode)}
                className={`rounded-full border px-4 py-2 text-xs font-medium transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${chipClass(dateRangeMode === mode)}`}
              >
                {mode === 'all' ? '全部時間' : mode === '7d' ? '近 7 天' : '近 30 天'}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto] lg:items-center">
          <input
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            placeholder="搜尋主題、我的回應或伴侶回應"
            aria-label="搜尋主題、我的回應或伴侶回應"
            className="w-full rounded-[1.15rem] border border-white/55 bg-white/80 px-4 py-3 text-sm text-card-foreground placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <div className="inline-flex items-center gap-2 rounded-full border border-white/55 bg-white/74 px-3 py-2 shadow-soft">
            <label htmlFor="history-sort" className="text-xs uppercase tracking-[0.2em] text-primary/70">
              排序
            </label>
            <select
              id="history-sort"
              value={sortMode}
              onChange={(e) => setSortQuery(e.target.value as SortMode)}
              className="select-premium min-w-[6.5rem] border-0 bg-transparent text-xs shadow-none"
            >
              <option value="newest">最新優先</option>
              <option value="oldest">最舊優先</option>
              <option value="category">依牌組排序</option>
            </select>
          </div>
          <button
            type="button"
            onClick={onExportCsv}
            className="rounded-full border border-white/55 bg-white/74 px-4 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            匯出檔案
          </button>
        </div>
      </div>
    </section>
  );
}
