'use client';

import { DECK_META_LIST } from '@/lib/deck-meta';
import type { SortMode } from './useDeckHistory';
import type { DateRangeMode } from './useDeckHistory';

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
  const deckMetaList = DECK_META_LIST;
  const btn = (active: boolean) =>
    active
      ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-primary shadow-satin-button'
      : 'bg-card text-muted-foreground border-border hover:bg-muted';
  const focusRing =
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

  return (
    <section className="rounded-card border border-border bg-card/80 p-4 space-y-3 relative overflow-hidden">
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <div className="flex gap-2 overflow-x-auto pb-1">
        <button
          onClick={() => setCategoryQuery(undefined)}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-haven-fast ease-haven whitespace-nowrap ${focusRing} ${btn(!normalizedCategoryFilter)}`}
        >
          全部牌組
        </button>
        {deckMetaList.map((deck) => {
          const active = normalizedCategoryFilter === deck.id;
          return (
            <button
              key={deck.id}
              onClick={() => setCategoryQuery(deck.id)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-haven-fast ease-haven whitespace-nowrap inline-flex items-center gap-1.5 ${focusRing} ${btn(active)}`}
            >
              <deck.Icon className="w-3.5 h-3.5" strokeWidth={2.2} />
              {deck.title}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setDateRangeQuery('all')}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-haven-fast ease-haven ${focusRing} ${btn(dateRangeMode === 'all')}`}
        >
          全部時間
        </button>
        <button
          onClick={() => setDateRangeQuery('7d')}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-haven-fast ease-haven ${focusRing} ${btn(dateRangeMode === '7d')}`}
        >
          近 7 天
        </button>
        <button
          onClick={() => setDateRangeQuery('30d')}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors duration-haven-fast ease-haven ${focusRing} ${btn(dateRangeMode === '30d')}`}
        >
          近 30 天
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
        <input
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          placeholder="搜尋問題或回答內容..."
          aria-label="搜尋問題或回答內容"
          className="w-full sm:max-w-sm rounded-input border border-input bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 placeholder:font-light hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary transition-all duration-haven ease-haven"
        />
        <div className="flex items-center gap-2">
          <label htmlFor="history-sort" className="text-xs text-muted-foreground whitespace-nowrap">
            排序：
          </label>
          <select
            id="history-sort"
            value={sortMode}
            onChange={(e) => setSortQuery(e.target.value as SortMode)}
            className="select-premium text-xs"
          >
            <option value="newest">最新優先</option>
            <option value="oldest">最舊優先</option>
            <option value="category">依牌組排序</option>
          </select>
          <button
            onClick={onExportCsv}
            className="text-xs rounded-input border border-input bg-card px-2.5 py-1.5 text-foreground hover:bg-muted hover:shadow-soft transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            匯出 CSV
          </button>
        </div>
      </div>
    </section>
  );
}
