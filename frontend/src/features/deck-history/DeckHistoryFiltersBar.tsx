'use client';

import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { DECK_META_LIST } from '@/lib/deck-meta';
import { getSelectionChipStateClass, selectionChipBaseClass, selectionChipWithIconClass } from '@/features/decks/ui/routeStyleHelpers';
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
  return (
    <section className="rounded-[2rem] border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(248,244,238,0.78))] p-5 shadow-soft md:p-6">
      <div className="stack-section">
        <div className="stack-block">
          <p className="type-micro uppercase text-primary/72">檔案整理</p>
          <h3 className="type-h3 text-card-foreground">按時間、牌組與關鍵字整理這些對話。</h3>
        </div>

        <div className="stack-block">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setCategoryQuery(undefined)}
              className={`${selectionChipBaseClass} ${getSelectionChipStateClass(!normalizedCategoryFilter)}`}
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
                  className={`${selectionChipWithIconClass} ${getSelectionChipStateClass(active)}`}
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
                className={`${selectionChipBaseClass} ${getSelectionChipStateClass(dateRangeMode === mode)}`}
              >
                {mode === 'all' ? '全部時間' : mode === '7d' ? '近 7 天' : '近 30 天'}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto] lg:items-center">
          <Input
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            placeholder="搜尋主題、我的回應或伴侶回應"
            aria-label="搜尋主題、我的回應或伴侶回應"
            className="bg-white/80 shadow-none"
          />
          <div className="inline-flex items-center gap-2 rounded-full border border-white/55 bg-white/74 px-3 py-2 shadow-soft">
            <label htmlFor="history-sort" className="type-micro uppercase text-primary/70">
              排序
            </label>
            <select
              id="history-sort"
              value={sortMode}
              onChange={(e) => setSortQuery(e.target.value as SortMode)}
              className="select-premium min-w-[6.5rem] border-0 bg-transparent type-caption text-card-foreground shadow-none"
            >
              <option value="newest">最新優先</option>
              <option value="oldest">最舊優先</option>
              <option value="category">依牌組排序</option>
            </select>
          </div>
          <Button type="button" variant="secondary" onClick={onExportCsv}>
            匯出檔案
          </Button>
        </div>
      </div>
    </section>
  );
}
