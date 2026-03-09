// frontend/src/app/decks/history/page.tsx

'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, MessageCircle, Calendar } from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';
import { normalizeDeckCategory } from '@/lib/deck-category';
import { DECK_META_LIST, getDeckDisplayName, getDeckMeta } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
import { fetchDeckHistory, fetchDeckHistorySummary, DeckHistoryEntry, DeckHistorySummary } from '@/services/deckService';

type SortMode = 'newest' | 'oldest' | 'category';
type DateRangeMode = 'all' | '7d' | '30d';
type DeckLibraryFilterMode = 'all' | 'in_progress' | 'not_started' | 'completed';
type DeckLibrarySortMode = 'recommended' | 'progress_desc' | 'progress_asc' | 'title';
const PAGE_SIZE = 20;
const SEARCH_QUERY_MAX_LENGTH = 80;
const DECK_LIBRARY_FILTER_MODES: ReadonlyArray<DeckLibraryFilterMode> = [
  'all',
  'in_progress',
  'not_started',
  'completed',
];
const DECK_LIBRARY_SORT_MODES: ReadonlyArray<DeckLibrarySortMode> = [
  'recommended',
  'progress_desc',
  'progress_asc',
  'title',
];

const toIsoDate = (value: Date): string => value.toISOString().slice(0, 10);
const isDateRangeQueryValue = (value: string | null): value is Exclude<DateRangeMode, 'all'> =>
  value === '7d' || value === '30d';
const normalizeDateRangeMode = (value: string | null): DateRangeMode =>
  isDateRangeQueryValue(value) ? value : 'all';
const isSortQueryValue = (value: string | null): value is SortMode =>
  value === 'newest' || value === 'oldest' || value === 'category';
const isDeckLibraryFilterQueryValue = (value: string | null): value is DeckLibraryFilterMode =>
  value !== null && DECK_LIBRARY_FILTER_MODES.includes(value as DeckLibraryFilterMode);
const isDeckLibrarySortQueryValue = (value: string | null): value is DeckLibrarySortMode =>
  value !== null && DECK_LIBRARY_SORT_MODES.includes(value as DeckLibrarySortMode);
const normalizeSortMode = (value: string | null): SortMode =>
  isSortQueryValue(value) ? value : 'newest';
const normalizeSearchQuery = (value: string | null): string =>
  (value ?? '').trim().slice(0, SEARCH_QUERY_MAX_LENGTH);

function HistoryPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { showToast } = useToast();

  const rawCategoryFilter = searchParams.get('category');
  const rawDateRangeFilter = searchParams.get('range');
  const rawSortFilter = searchParams.get('sort');
  const rawKeywordFilter = searchParams.get('q');
  const rawLibraryFilter = searchParams.get('library_filter');
  const rawLibrarySort = searchParams.get('library_sort');
  const normalizedDateRangeFilter = useMemo(
    () => normalizeDateRangeMode(rawDateRangeFilter),
    [rawDateRangeFilter],
  );
  const normalizedSortFilter = useMemo(
    () => normalizeSortMode(rawSortFilter),
    [rawSortFilter],
  );
  const normalizedKeywordFilter = useMemo(
    () => normalizeSearchQuery(rawKeywordFilter),
    [rawKeywordFilter],
  );
  const normalizedCategoryFilter = useMemo(
    () => normalizeDeckCategory(rawCategoryFilter),
    [rawCategoryFilter],
  );
  const normalizedLibraryFilter = useMemo(
    () => (isDeckLibraryFilterQueryValue(rawLibraryFilter) ? rawLibraryFilter : null),
    [rawLibraryFilter],
  );
  const normalizedLibrarySort = useMemo(
    () => (isDeckLibrarySortQueryValue(rawLibrarySort) ? rawLibrarySort : null),
    [rawLibrarySort],
  );
  const searchParamsString = searchParams.toString();
  const backToDecksHref = useMemo(() => {
    const nextParams = new URLSearchParams();
    if (normalizedLibraryFilter && normalizedLibraryFilter !== 'all') {
      nextParams.set('filter', normalizedLibraryFilter);
    }
    if (normalizedLibrarySort && normalizedLibrarySort !== 'recommended') {
      nextParams.set('sort', normalizedLibrarySort);
    }
    const nextQuery = nextParams.toString();
    return nextQuery ? `/decks?${nextQuery}` : '/decks';
  }, [normalizedLibraryFilter, normalizedLibrarySort]);

  const [history, setHistory] = useState<DeckHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [sortMode, setSortMode] = useState<SortMode>(normalizedSortFilter);
  const [dateRangeMode, setDateRangeMode] = useState<DateRangeMode>(normalizedDateRangeFilter);
  const [searchKeyword, setSearchKeyword] = useState<string>(normalizedKeywordFilter);
  const [summary, setSummary] = useState<DeckHistorySummary>({
    total_records: 0,
    this_month_records: 0,
    top_category: null,
    top_category_count: 0,
  });
  const invalidFilterHandledRef = useRef(false);
  const invalidDateRangeHandledRef = useRef(false);
  const invalidSortHandledRef = useRef(false);
  const searchParamsStringRef = useRef(searchParamsString);

  useEffect(() => {
    searchParamsStringRef.current = searchParamsString;
  }, [searchParamsString]);

  const replaceQueryParams = useCallback(
    (updater: (params: URLSearchParams) => void) => {
      const current = new URLSearchParams(searchParamsStringRef.current);
      const before = current.toString();
      updater(current);
      const after = current.toString();
      if (after === before) {
        return;
      }
      router.replace(after ? `/decks/history?${after}` : '/decks/history');
    },
    [router],
  );

  const setCategoryQuery = (category?: string) => {
    replaceQueryParams((nextParams) => {
      if (!category) {
        nextParams.delete('category');
      } else {
        nextParams.set('category', category);
      }
    });
  };

  const setDateRangeQuery = (nextMode: DateRangeMode) => {
    setDateRangeMode(nextMode);
    replaceQueryParams((nextParams) => {
      if (nextMode === 'all') {
        nextParams.delete('range');
      } else {
        nextParams.set('range', nextMode);
      }
    });
  };

  const setSortQuery = (nextSortMode: SortMode) => {
    setSortMode(nextSortMode);
    replaceQueryParams((nextParams) => {
      if (nextSortMode === 'newest') {
        nextParams.delete('sort');
      } else {
        nextParams.set('sort', nextSortMode);
      }
    });
  };

  const dateFilter = useMemo(() => {
    if (dateRangeMode === 'all') {
      return { revealed_from: undefined, revealed_to: undefined };
    }

    const now = new Date();
    const start = new Date(now);
    if (dateRangeMode === '7d') {
      start.setDate(now.getDate() - 6);
    } else {
      start.setDate(now.getDate() - 29);
    }

    return {
      revealed_from: toIsoDate(start),
      revealed_to: toIsoDate(now),
    };
  }, [dateRangeMode]);

  useEffect(() => {
    setDateRangeMode(normalizedDateRangeFilter);
  }, [normalizedDateRangeFilter]);

  useEffect(() => {
    setSortMode(normalizedSortFilter);
  }, [normalizedSortFilter]);

  useEffect(() => {
    setSearchKeyword((prev) => (prev === normalizedKeywordFilter ? prev : normalizedKeywordFilter));
  }, [normalizedKeywordFilter]);

  useEffect(() => {
    if (!rawSortFilter || isSortQueryValue(rawSortFilter)) {
      invalidSortHandledRef.current = false;
      return;
    }
    if (!invalidSortHandledRef.current) {
      invalidSortHandledRef.current = true;
      showToast('無效的排序參數，已切回最新優先。', 'info');
    }
    replaceQueryParams((nextParams) => {
      nextParams.delete('sort');
    });
  }, [rawSortFilter, replaceQueryParams, showToast]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const normalizedKeyword = normalizeSearchQuery(searchKeyword);
      replaceQueryParams((nextParams) => {
        if (!normalizedKeyword) {
          nextParams.delete('q');
        } else {
          nextParams.set('q', normalizedKeyword);
        }
      });
    }, 300);

    return () => clearTimeout(timer);
  }, [replaceQueryParams, searchKeyword]);

  const visibleHistory = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    const filtered = history.filter((entry) => {
      if (!keyword) {
        return true;
      }
      const question = entry.card_question?.toLowerCase() ?? '';
      const myAnswer = entry.my_answer?.toLowerCase() ?? '';
      const partnerAnswer = entry.partner_answer?.toLowerCase() ?? '';
      const categoryName = getDeckDisplayName(entry.category).toLowerCase();
      return (
        question.includes(keyword) ||
        myAnswer.includes(keyword) ||
        partnerAnswer.includes(keyword) ||
        categoryName.includes(keyword)
      );
    });

    filtered.sort((a, b) => {
      if (sortMode === 'oldest') {
        return new Date(a.revealed_at).getTime() - new Date(b.revealed_at).getTime();
      }
      if (sortMode === 'category') {
        const categoryCompare = getDeckDisplayName(a.category).localeCompare(getDeckDisplayName(b.category), 'zh-Hant');
        if (categoryCompare !== 0) {
          return categoryCompare;
        }
        return new Date(b.revealed_at).getTime() - new Date(a.revealed_at).getTime();
      }
      return new Date(b.revealed_at).getTime() - new Date(a.revealed_at).getTime();
    });

    return filtered;
  }, [history, searchKeyword, sortMode]);

  const summaryTopCategoryDisplay = useMemo(
    () => (summary.top_category ? getDeckDisplayName(summary.top_category) : '—'),
    [summary.top_category],
  );

  useEffect(() => {
    let alive = true;
    const loadData = async () => {
      try {
        if (rawCategoryFilter && !normalizedCategoryFilter) {
          if (!invalidFilterHandledRef.current) {
            invalidFilterHandledRef.current = true;
            showToast('無效的牌組篩選，已切回全部歷史。', 'info');
          }
          replaceQueryParams((nextParams) => {
            nextParams.delete('category');
          });
          return;
        }

        if (rawDateRangeFilter && !isDateRangeQueryValue(rawDateRangeFilter)) {
          if (!invalidDateRangeHandledRef.current) {
            invalidDateRangeHandledRef.current = true;
            showToast('無效的日期篩選，已切回全部時間。', 'info');
          }
          replaceQueryParams((nextParams) => {
            nextParams.delete('range');
          });
          return;
        }

        invalidFilterHandledRef.current = false;
        invalidDateRangeHandledRef.current = false;
        const [data, summaryData] = await Promise.all([
          fetchDeckHistory({
            category: normalizedCategoryFilter ?? undefined,
            limit: PAGE_SIZE,
            offset: 0,
            ...dateFilter,
          }),
          fetchDeckHistorySummary({
            category: normalizedCategoryFilter ?? undefined,
            ...dateFilter,
          }),
        ]);
        if (!alive) {
          return;
        }
        setHistory(data);
        setSummary(summaryData);
        setHasMore(data.length < summaryData.total_records);
      } catch (error) {
        if (alive) {
          console.error('載入歷史失敗', error);
        }
      } finally {
        if (alive) {
          setLoading(false);
          setSummaryLoading(false);
          setLoadingMore(false);
        }
      }
    };
    setLoading(true);
    setSummaryLoading(true);
    setLoadingMore(false);
    setHasMore(true);
    void loadData();
    return () => {
      alive = false;
    };
  }, [
    dateFilter,
    normalizedCategoryFilter,
    rawDateRangeFilter,
    rawCategoryFilter,
    replaceQueryParams,
    showToast,
  ]);

  const handleLoadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) {
      return;
    }
    setLoadingMore(true);
    try {
      const nextBatch = await fetchDeckHistory({
        category: normalizedCategoryFilter ?? undefined,
        limit: PAGE_SIZE,
        offset: history.length,
        ...dateFilter,
      });

      const seen = new Set(history.map((entry) => entry.session_id));
      const deduped = nextBatch.filter((entry) => !seen.has(entry.session_id));
      const merged = [...history, ...deduped];
      setHistory(merged);
      setHasMore(merged.length < summary.total_records);
    } catch (error) {
      console.error('載入更多歷史失敗', error);
      showToast('載入更多紀錄失敗，請稍後再試。', 'error');
    } finally {
      setLoadingMore(false);
    }
  }, [dateFilter, hasMore, history, loading, loadingMore, normalizedCategoryFilter, showToast, summary.total_records]);

  const handleExportCsv = useCallback(() => {
    if (visibleHistory.length === 0) {
      showToast('目前沒有可匯出的資料。', 'info');
      return;
    }

    const escapeCsv = (value: unknown): string => {
      const text = String(value ?? '');
      const escaped = text.replace(/"/g, '""');
      return `"${escaped}"`;
    };

    const header = ['revealed_at', 'category', 'depth_level', 'depth_label', 'card_question', 'my_answer', 'partner_answer'];
    const lines = visibleHistory.map((entry) => {
      const depthLevel = resolveDepthLevel(entry.depth_level);
      const depth = getDepthPresentation(depthLevel);
      return [
        escapeCsv(entry.revealed_at),
        escapeCsv(getDeckDisplayName(entry.category)),
        escapeCsv(depthLevel),
        escapeCsv(depth.label),
        escapeCsv(entry.card_question),
        escapeCsv(entry.my_answer ?? ''),
        escapeCsv(entry.partner_answer ?? ''),
      ].join(',');
    });
    const csv = ['\uFEFF' + header.join(','), ...lines].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `haven_deck_history_${toIsoDate(new Date())}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showToast('CSV 匯出成功。', 'success');
  }, [showToast, visibleHistory]);

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-100 px-4 py-4 flex items-center">
        <Link href={backToDecksHref} className="p-2 -ml-2 hover:bg-gray-100 rounded-full transition-colors">
          <ArrowLeft className="w-6 h-6 text-gray-600" />
        </Link>
        <h1 className="ml-2 text-xl font-bold text-gray-800">我們的對話時光</h1>
      </header>

      {/* Content */}
      <main className="p-4 max-w-2xl mx-auto space-y-6">
        <section className="rounded-3xl border border-white/70 bg-gradient-to-br from-white to-slate-50 shadow-sm p-5">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-gray-400 uppercase">History Snapshot</p>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <div className="rounded-2xl bg-white border border-slate-100 p-3">
              <p className="text-[10px] text-slate-400">總回顧</p>
              <p className="text-lg font-bold text-slate-800">
                {summaryLoading ? '...' : summary.total_records}
              </p>
            </div>
            <div className="rounded-2xl bg-white border border-slate-100 p-3">
              <p className="text-[10px] text-slate-400">本月新增</p>
              <p className="text-lg font-bold text-slate-800">
                {summaryLoading ? '...' : summary.this_month_records}
              </p>
            </div>
            <div className="rounded-2xl bg-white border border-slate-100 p-3">
              <p className="text-[10px] text-slate-400">最常聊</p>
              <p className="text-sm font-bold text-slate-800 truncate">
                {summaryLoading ? '...' : summaryTopCategoryDisplay}
              </p>
            </div>
          </div>
          {!summaryLoading && summary.total_records > 0 && (
            <p className="mt-3 text-xs text-slate-500">
              目前已載入 {history.length}/{summary.total_records} 筆紀錄。
            </p>
          )}
          {!summaryLoading && summary.top_category_count > 0 && (
            <p className="mt-3 text-xs text-slate-500">
              「{summaryTopCategoryDisplay}」已累積 {summary.top_category_count} 次對話解鎖。
            </p>
          )}
        </section>

        <section className="rounded-2xl border border-slate-100 bg-white/80 p-4 space-y-3">
          <div className="flex gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setCategoryQuery(undefined)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors whitespace-nowrap ${
                !normalizedCategoryFilter
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              全部牌組
            </button>
            {DECK_META_LIST.map((deck) => {
              const active = normalizedCategoryFilter === deck.id;
              return (
                <button
                  key={deck.id}
                  onClick={() => setCategoryQuery(deck.id)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors whitespace-nowrap inline-flex items-center gap-1.5 ${
                    active
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
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
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                dateRangeMode === 'all'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              全部時間
            </button>
            <button
              onClick={() => setDateRangeQuery('7d')}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                dateRangeMode === '7d'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              近 7 天
            </button>
            <button
              onClick={() => setDateRangeQuery('30d')}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                dateRangeMode === '30d'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              近 30 天
            </button>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
            <input
              value={searchKeyword}
              onChange={(event) => setSearchKeyword(event.target.value)}
              placeholder="搜尋問題或回答內容..."
              className="w-full sm:max-w-sm rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
            />
            <div className="flex items-center gap-2">
              <label htmlFor="history-sort" className="text-xs text-slate-500 whitespace-nowrap">
                排序：
              </label>
              <select
                id="history-sort"
                value={sortMode}
                onChange={(event) => setSortQuery(event.target.value as SortMode)}
                className="text-xs rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-slate-700"
              >
                <option value="newest">最新優先</option>
                <option value="oldest">最舊優先</option>
                <option value="category">依牌組排序</option>
              </select>
              <button
                onClick={handleExportCsv}
                className="text-xs rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-slate-700 hover:bg-slate-50 transition-colors"
              >
                匯出 CSV
              </button>
            </div>
          </div>
        </section>
        
        {loading ? (
           // Loading Skeleton
           [1, 2, 3].map((i) => (
             <div key={i} className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm animate-pulse h-40" />
           ))
        ) : history.length === 0 ? (
           // Empty State
           <div className="text-center py-20">
             <div className="inline-block p-4 bg-gray-100 rounded-full mb-4">
                <MessageCircle className="w-8 h-8 text-gray-400" />
             </div>
             <h3 className="text-lg font-bold text-gray-700">還沒有紀錄喔</h3>
             <p className="text-gray-500 mt-2">去抽張卡片，開始你們的第一個話題吧！</p>
             <Link href={backToDecksHref} className="mt-6 inline-block px-6 py-2 bg-gray-900 text-white rounded-full text-sm font-bold">
                前往大廳
             </Link>
           </div>
        ) : visibleHistory.length === 0 ? (
          <div className="text-center py-14 bg-white rounded-2xl border border-gray-100">
            <p className="text-gray-600 font-medium">找不到符合條件的歷史紀錄</p>
            <p className="text-gray-400 text-sm mt-1">試試調整篩選、關鍵字或排序。</p>
          </div>
        ) : (
           // History List
           <>
             {visibleHistory.map((entry) => {
               const deckMeta = getDeckMeta(entry.category);
               const deckTitle = getDeckDisplayName(entry.category);
               const depthLevel = resolveDepthLevel(entry.depth_level);
               const depth = getDepthPresentation(depthLevel);

               return (
                 <div
                   key={entry.session_id}
                   className={`relative bg-white rounded-2xl border shadow-sm overflow-hidden hover:shadow-md transition-shadow ${depth.accentFrameClass}`}
                 >
                   <div className={`absolute inset-x-0 top-0 h-1 ${depth.topAccentClass}`} />
                   {/* 卡片標題區 */}
                   <div className="bg-gray-50/50 px-6 pt-5 pb-4 border-b border-gray-100 flex justify-between items-start gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wide px-2 py-1 rounded-md ${deckMeta?.badgeClass ?? 'bg-gray-100 text-gray-600'}`}>
                            {deckMeta && <deckMeta.Icon className={`w-3.5 h-3.5 ${deckMeta.iconColor}`} strokeWidth={2.2} />}
                            {deckTitle}
                          </span>
                          <span className={`inline-flex items-center text-[10px] font-bold tracking-wide px-2 py-1 rounded-md ${depth.badgeClass}`}>
                            Depth {depthLevel} · {depth.label}
                          </span>
                        </div>
                        <h3 className="font-bold text-gray-800 mt-2 leading-relaxed">
                            {entry.card_question}
                        </h3>
                      </div>
                      <div className="flex items-center text-xs text-gray-400 shrink-0 mt-1">
                         <Calendar className="w-3 h-3 mr-1" />
                         {new Date(entry.revealed_at).toLocaleDateString()}
                      </div>
                   </div>

                   {/* 對話內容 */}
                   <div className="p-6 space-y-4">
                      {/* 我 */}
                      <div className="flex flex-col items-end">
                          <div className="bg-gray-900 text-white px-4 py-2 rounded-2xl rounded-tr-sm text-sm">
                            {entry.my_answer}
                          </div>
                          <span className="text-[10px] text-gray-400 mt-1 mr-1">我</span>
                      </div>

                      {/* 伴侶 */}
                      <div className="flex flex-col items-start">
                          <div className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-2xl rounded-tl-sm text-sm">
                            {entry.partner_answer}
                          </div>
                          <span className="text-[10px] text-gray-400 mt-1 ml-1">伴侶</span>
                      </div>
                   </div>
                 </div>
               );
             })}
             {hasMore && (
               <div className="pt-1 flex justify-center">
                 <button
                   onClick={() => void handleLoadMore()}
                   disabled={loadingMore}
                   className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${
                     loadingMore
                       ? 'bg-slate-200 text-slate-500 cursor-not-allowed'
                       : 'bg-slate-900 text-white hover:bg-slate-800'
                   }`}
                 >
                   {loadingMore ? '載入中...' : '載入更多歷史'}
                 </button>
               </div>
             )}
           </>
        )}
      </main>
    </div>
  );
}

export default function HistoryPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 pb-20" />}>
      <HistoryPageContent />
    </Suspense>
  );
}
