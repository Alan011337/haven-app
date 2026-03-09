// frontend/src/app/decks/page.tsx

'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { DECK_META_LIST } from '@/lib/deck-meta';
import { fetchDeckCardCounts, type DeckCardCount } from '@/services/deckService';

const FILTER_MODES = ['all', 'in_progress', 'not_started', 'completed'] as const;
const SORT_MODES = ['recommended', 'progress_desc', 'progress_asc', 'title'] as const;

type FilterMode = (typeof FILTER_MODES)[number];
type SortMode = (typeof SORT_MODES)[number];

const isFilterMode = (value: string): value is FilterMode =>
  (FILTER_MODES as readonly string[]).includes(value);

const isSortMode = (value: string): value is SortMode =>
  (SORT_MODES as readonly string[]).includes(value);

export default function DecksPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [deckStats, setDeckStats] = useState<Record<string, DeckCardCount>>({});
  const [countsLoading, setCountsLoading] = useState(true);

  const rawFilterMode = searchParams.get('filter');
  const rawSortMode = searchParams.get('sort');
  const filterMode: FilterMode =
    rawFilterMode && isFilterMode(rawFilterMode) ? rawFilterMode : 'all';
  const sortMode: SortMode =
    rawSortMode && isSortMode(rawSortMode) ? rawSortMode : 'recommended';

  const syncQueryParams = (nextFilter: FilterMode, nextSort: SortMode) => {
    const params = new URLSearchParams(searchParams.toString());
    if (nextFilter === 'all') {
      params.delete('filter');
    } else {
      params.set('filter', nextFilter);
    }
    if (nextSort === 'recommended') {
      params.delete('sort');
    } else {
      params.set('sort', nextSort);
    }

    const nextQuery = params.toString();
    const currentQuery = searchParams.toString();
    if (nextQuery === currentQuery) {
      return;
    }

    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, {
      scroll: false,
    });
  };

  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    let shouldReplace = false;

    if (rawFilterMode && !isFilterMode(rawFilterMode)) {
      params.delete('filter');
      shouldReplace = true;
    }
    if (rawSortMode && !isSortMode(rawSortMode)) {
      params.delete('sort');
      shouldReplace = true;
    }

    if (!shouldReplace) {
      return;
    }
    const nextQuery = params.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, {
      scroll: false,
    });
  }, [pathname, rawFilterMode, rawSortMode, router, searchParams]);

  useEffect(() => {
    let alive = true;
    const loadDeckCounts = async () => {
      try {
        const stats = await fetchDeckCardCounts();
        if (!alive) return;
        const next: Record<string, DeckCardCount> = {};
        for (const item of stats) {
          next[item.category] = item;
        }
        setDeckStats(next);
      } catch (error) {
        console.error('載入牌組題數失敗', error);
      } finally {
        if (alive) {
          setCountsLoading(false);
        }
      }
    };
    void loadDeckCounts();
    return () => {
      alive = false;
    };
  }, []);

  const totals = DECK_META_LIST.reduce(
    (acc, deck) => {
      const stats = deckStats[deck.id];
      acc.totalCards += stats?.total_cards ?? 0;
      acc.answeredCards += stats?.answered_cards ?? 0;
      return acc;
    },
    { totalCards: 0, answeredCards: 0 },
  );
  const overallCompletionRate =
    totals.totalCards > 0 ? Math.round((totals.answeredCards / totals.totalCards) * 1000) / 10 : 0;
  const completedDecks = DECK_META_LIST.filter((deck) => {
    const stats = deckStats[deck.id];
    return Boolean(stats && stats.total_cards > 0 && stats.completion_rate >= 100);
  }).length;

  const nextFocusDeck = DECK_META_LIST
    .map((deck) => {
      const stats = deckStats[deck.id];
      return {
        deck,
        completionRate: stats?.completion_rate ?? 0,
        totalCards: stats?.total_cards ?? 0,
      };
    })
    .filter((item) => item.totalCards > 0 && item.completionRate < 100)
    .sort((a, b) => b.completionRate - a.completionRate)[0];

  const deckCards = useMemo(() => {
    const mapped = DECK_META_LIST.map((deck) => {
      const stats = deckStats[deck.id];
      const totalCards = stats?.total_cards ?? 0;
      const answeredCards = stats?.answered_cards ?? 0;
      const completionRate = stats?.completion_rate ?? 0;
      const isCompleted = totalCards > 0 && completionRate >= 100;
      const isStarted = answeredCards > 0;
      const statusRank = isCompleted ? 2 : isStarted ? 0 : 1;
      return {
        deck,
        totalCards,
        answeredCards,
        completionRate,
        statusRank,
        isCompleted,
        isStarted,
      };
    });

    const filtered = mapped.filter((item) => {
      if (filterMode === 'all') {
        return true;
      }
      if (filterMode === 'in_progress') {
        return item.isStarted && !item.isCompleted;
      }
      if (filterMode === 'not_started') {
        return !item.isStarted;
      }
      return item.isCompleted;
    });

    filtered.sort((a, b) => {
      if (sortMode === 'progress_desc') {
        return b.completionRate - a.completionRate;
      }
      if (sortMode === 'progress_asc') {
        return a.completionRate - b.completionRate;
      }
      if (sortMode === 'title') {
        return a.deck.title.localeCompare(b.deck.title, 'zh-Hant');
      }

      // recommended: 進行中 -> 未開始 -> 已完成，再依進度排序
      if (a.statusRank !== b.statusRank) {
        return a.statusRank - b.statusRank;
      }
      return b.completionRate - a.completionRate;
    });

    return filtered;
  }, [deckStats, filterMode, sortMode]);

  const deckRoomQueryString = useMemo(() => {
    const params = new URLSearchParams();
    if (filterMode !== 'all') {
      params.set('filter', filterMode);
    }
    if (sortMode !== 'recommended') {
      params.set('sort', sortMode);
    }
    return params.toString();
  }, [filterMode, sortMode]);

  const buildDeckRoomHref = (deckId: string) =>
    deckRoomQueryString ? `/decks/${deckId}?${deckRoomQueryString}` : `/decks/${deckId}`;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* 頂部導航 */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-100 px-4 py-4 flex items-center shadow-sm">
        <Link href="/" className="p-2 -ml-2 hover:bg-gray-100 rounded-full transition-colors">
          <ArrowLeft className="w-6 h-6 text-gray-600" />
        </Link>
        <h1 className="ml-2 text-xl font-bold text-gray-800">牌組圖書館</h1>
      </header>

      {/* 內容區 */}
      <main className="p-4 space-y-6 max-w-2xl mx-auto">
        <div className="text-center space-y-2 mb-6 mt-2">
          <h2 className="text-2xl font-bold text-gray-900">今天想聊點什麼？</h2>
          <p className="text-gray-500">選擇一套牌組，開啟無限話題。</p>
        </div>

        <section className="rounded-3xl border border-white/70 bg-gradient-to-br from-white to-slate-50 shadow-sm p-5 md:p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <p className="text-[11px] font-semibold tracking-[0.18em] text-gray-400 uppercase">Progress Snapshot</p>
              {countsLoading ? (
                <div className="space-y-2">
                  <div className="h-6 w-40 rounded-md bg-slate-200/70 animate-pulse" />
                  <div className="h-4 w-56 rounded-md bg-slate-200/70 animate-pulse" />
                </div>
              ) : (
                <>
                  <h3 className="text-xl md:text-2xl font-bold text-slate-800">
                    已完成 {totals.answeredCards}/{totals.totalCards} 題
                  </h3>
                  <p className="text-sm text-slate-500">
                    八大牌組進度 {overallCompletionRate}% · 已全破 {completedDecks}/{DECK_META_LIST.length} 套
                  </p>
                </>
              )}
            </div>
            {!countsLoading && nextFocusDeck && (
              <Link
                href={buildDeckRoomHref(nextFocusDeck.deck.id)}
                className="shrink-0 text-xs font-semibold px-3 py-2 rounded-full bg-slate-900 text-white hover:bg-slate-800 transition-colors"
              >
                繼續 {nextFocusDeck.deck.title}
              </Link>
            )}
          </div>
          <div className="mt-4 h-2 w-full rounded-full bg-slate-200/70 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 transition-all duration-500"
              style={{ width: `${countsLoading ? 0 : Math.max(0, Math.min(100, overallCompletionRate))}%` }}
            />
          </div>
        </section>

        <section className="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-white/80 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => syncQueryParams('all', sortMode)}
              aria-pressed={filterMode === 'all'}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                filterMode === 'all'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              全部
            </button>
            <button
              onClick={() => syncQueryParams('in_progress', sortMode)}
              aria-pressed={filterMode === 'in_progress'}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                filterMode === 'in_progress'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              進行中
            </button>
            <button
              onClick={() => syncQueryParams('not_started', sortMode)}
              aria-pressed={filterMode === 'not_started'}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                filterMode === 'not_started'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              未開始
            </button>
            <button
              onClick={() => syncQueryParams('completed', sortMode)}
              aria-pressed={filterMode === 'completed'}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                filterMode === 'completed'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              已完成
            </button>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="deck-sort" className="text-xs text-slate-500 whitespace-nowrap">
              排序：
            </label>
            <select
              id="deck-sort"
              value={sortMode}
              onChange={(event) => {
                const nextSort = event.target.value;
                if (!isSortMode(nextSort)) {
                  return;
                }
                syncQueryParams(filterMode, nextSort);
              }}
              className="text-xs rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-slate-700"
            >
              <option value="recommended">推薦排序</option>
              <option value="progress_desc">進度高到低</option>
              <option value="progress_asc">進度低到高</option>
              <option value="title">名稱排序</option>
            </select>
          </div>
          <p className="text-xs text-slate-500">
            目前顯示 {deckCards.length}/{DECK_META_LIST.length} 套牌組
          </p>
        </section>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {deckCards.length === 0 && !countsLoading && (
            <div className="col-span-full rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">
              目前沒有符合條件的牌組，換個篩選試試看。
            </div>
          )}
          {deckCards.map(({ deck, totalCards, answeredCards, completionRate, isCompleted, isStarted }) => {
            const countLabel = countsLoading ? '讀取中...' : `${totalCards} 題`;
            const progressLabel = countsLoading ? '載入進度...' : `${answeredCards}/${totalCards} 完成`;
            const progressWidth = countsLoading ? 0 : Math.max(0, Math.min(100, completionRate));
            const statusLabel = countsLoading
              ? '準備中'
              : isCompleted
                ? '已完成'
                : isStarted
                  ? '進行中'
                  : '未開始';
            return (
            <Link key={deck.id} href={buildDeckRoomHref(deck.id)}>
              <div 
                className={`
                  relative overflow-hidden rounded-2xl p-6 h-44 flex flex-col justify-between 
                  transition-all duration-300 hover:scale-[1.02] hover:shadow-lg cursor-pointer
                  bg-gradient-to-br ${deck.color} group
                `}
              >
                {/* 背景裝飾 */}
                <div className="absolute top-0 right-0 -mt-2 -mr-2 opacity-15 select-none pointer-events-none group-hover:opacity-25 transition-opacity">
                  <deck.Icon className={`w-24 h-24 ${deck.iconColor}`} strokeWidth={1.7} />
                </div>

                {/* 文字內容 */}
                <div>
                  <div className="mb-2">
                    <deck.Icon className={`w-7 h-7 ${deck.iconColor}`} strokeWidth={2.2} />
                  </div>
                  <h3 className={`text-xl font-bold ${deck.textColor}`}>{deck.title}</h3>
                  <p className={`text-sm mt-1 opacity-80 ${deck.textColor}`}>
                    {deck.description}
                  </p>
                </div>
                
                {/* 按鈕樣式的小標籤 */}
                <div className="mt-3 space-y-2">
                  {countsLoading ? (
                    <div className="space-y-2">
                      <div className="h-1.5 w-full rounded-full bg-white/35 overflow-hidden">
                        <div className="h-full w-1/3 rounded-full bg-white/70 animate-pulse" />
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="h-6 w-24 rounded-full bg-white/40 animate-pulse" />
                        <span className="h-6 w-16 rounded-full bg-white/40 animate-pulse" />
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="h-1.5 w-full rounded-full bg-white/40 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-white/85 transition-all duration-500"
                          style={{ width: `${progressWidth}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full bg-white/40 backdrop-blur-sm ${deck.textColor}`}>
                          {progressLabel}
                        </span>
                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full bg-white/40 backdrop-blur-sm ${deck.textColor}`}>
                          {countLabel}
                        </span>
                      </div>
                    </>
                  )}
                </div>
                <div className="mt-2 flex items-center justify-end gap-3">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full bg-white/40 backdrop-blur-sm ${deck.textColor}`}>
                    {statusLabel} · 進入 →
                  </span>
                </div>
              </div>
            </Link>
            );
          })}
        </div>
      </main>
    </div>
  );
}
