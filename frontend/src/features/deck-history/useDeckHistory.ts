'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useToast } from '@/hooks/useToast';
import {
  useDeckHistoryInfiniteQuery,
  useDeckHistorySummaryQuery,
} from '@/hooks/queries';
import { normalizeDeckCategory } from '@/lib/deck-category';
import { getDeckDisplayName } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
import { logClientError } from '@/lib/safe-error-log';
import type { DeckHistorySummary } from '@/services/deckService';

export type SortMode = 'newest' | 'oldest' | 'category';
export type DateRangeMode = 'all' | '7d' | '30d';
type DeckLibraryFilterMode = 'all' | 'in_progress' | 'not_started' | 'completed';
type DeckLibrarySortMode = 'recommended' | 'progress_desc' | 'progress_asc' | 'title';

export const PAGE_SIZE = 20;
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

export const toIsoDate = (value: Date): string => value.toISOString().slice(0, 10);
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

export function useDeckHistory() {
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

  const [sortMode, setSortMode] = useState<SortMode>(normalizedSortFilter);
  const [dateRangeMode, setDateRangeMode] = useState<DateRangeMode>(normalizedDateRangeFilter);
  const [searchKeyword, setSearchKeyword] = useState<string>(normalizedKeywordFilter);

  const dateFilter = useMemo(() => {
    if (dateRangeMode === 'all') return { revealed_from: undefined, revealed_to: undefined };
    const now = new Date();
    const start = new Date(now);
    if (dateRangeMode === '7d') start.setDate(now.getDate() - 6);
    else start.setDate(now.getDate() - 29);
    return { revealed_from: toIsoDate(start), revealed_to: toIsoDate(now) };
  }, [dateRangeMode]);

  const historyInfinite = useDeckHistoryInfiniteQuery(
    normalizedCategoryFilter ?? undefined,
    dateFilter,
  );
  const summaryQuery = useDeckHistorySummaryQuery(
    normalizedCategoryFilter ?? undefined,
    dateFilter,
  );

  const history = useMemo(
    () => historyInfinite.data?.pages.flat() ?? [],
    [historyInfinite.data?.pages],
  );
  const loading = historyInfinite.isLoading;
  const summaryLoading = summaryQuery.isLoading;
  const loadingMore = historyInfinite.isFetchingNextPage;
  const hasMore = historyInfinite.hasNextPage ?? false;
  const summary: DeckHistorySummary = useMemo(
    () =>
      summaryQuery.data ?? {
        total_records: 0,
        this_month_records: 0,
        top_category: null,
        top_category_count: 0,
      },
    [summaryQuery.data],
  );
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
      if (after === before) return;
      router.replace(after ? `/decks/history?${after}` : '/decks/history');
    },
    [router],
  );

  const setCategoryQuery = useCallback(
    (category?: string) => {
      replaceQueryParams((nextParams) => {
        if (!category) nextParams.delete('category');
        else nextParams.set('category', category);
      });
    },
    [replaceQueryParams],
  );

  const setDateRangeQuery = useCallback(
    (nextMode: DateRangeMode) => {
      setDateRangeMode(nextMode);
      replaceQueryParams((nextParams) => {
        if (nextMode === 'all') nextParams.delete('range');
        else nextParams.set('range', nextMode);
      });
    },
    [replaceQueryParams],
  );

  const setSortQuery = useCallback(
    (nextSortMode: SortMode) => {
      setSortMode(nextSortMode);
      replaceQueryParams((nextParams) => {
        if (nextSortMode === 'newest') nextParams.delete('sort');
        else nextParams.set('sort', nextSortMode);
      });
    },
    [replaceQueryParams],
  );

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
    replaceQueryParams((nextParams) => nextParams.delete('sort'));
  }, [rawSortFilter, replaceQueryParams, showToast]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const normalizedKeyword = normalizeSearchQuery(searchKeyword);
      replaceQueryParams((nextParams) => {
        if (!normalizedKeyword) nextParams.delete('q');
        else nextParams.set('q', normalizedKeyword);
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [replaceQueryParams, searchKeyword]);

  const visibleHistory = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    const filtered = history.filter((entry) => {
      if (!keyword) return true;
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
      if (sortMode === 'oldest')
        return new Date(a.revealed_at).getTime() - new Date(b.revealed_at).getTime();
      if (sortMode === 'category') {
        const categoryCompare = getDeckDisplayName(a.category).localeCompare(
          getDeckDisplayName(b.category),
          'zh-Hant',
        );
        if (categoryCompare !== 0) return categoryCompare;
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
    if (!rawCategoryFilter || normalizedCategoryFilter) return;
    if (!invalidFilterHandledRef.current) {
      invalidFilterHandledRef.current = true;
      showToast('無效的牌組篩選，已切回全部歷史。', 'info');
    }
    replaceQueryParams((nextParams) => nextParams.delete('category'));
  }, [normalizedCategoryFilter, rawCategoryFilter, replaceQueryParams, showToast]);

  useEffect(() => {
    if (!rawDateRangeFilter || isDateRangeQueryValue(rawDateRangeFilter)) return;
    if (!invalidDateRangeHandledRef.current) {
      invalidDateRangeHandledRef.current = true;
      showToast('無效的日期篩選，已切回全部時間。', 'info');
    }
    replaceQueryParams((nextParams) => nextParams.delete('range'));
  }, [rawDateRangeFilter, replaceQueryParams, showToast]);

  const handleLoadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return;
    historyInfinite.fetchNextPage().catch((error) => {
      logClientError('deck-history-load-more-failed', error);
      showToast('載入更多紀錄失敗，請稍後再試。', 'error');
    });
  }, [loading, loadingMore, hasMore, historyInfinite, showToast]);

  const handleExportCsv = useCallback(() => {
    if (visibleHistory.length === 0) {
      showToast('目前沒有可匯出的資料。', 'info');
      return;
    }
    const escapeCsv = (value: unknown): string => {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    };
    const header = [
      'revealed_at',
      'category',
      'depth_level',
      'depth_label',
      'card_question',
      'my_answer',
      'partner_answer',
    ];
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

  return {
    history,
    loading,
    summaryLoading,
    loadingMore,
    hasMore,
    sortMode,
    dateRangeMode,
    searchKeyword,
    setSearchKeyword,
    summary,
    summaryTopCategoryDisplay,
    visibleHistory,
    backToDecksHref,
    normalizedCategoryFilter,
    setCategoryQuery,
    setDateRangeQuery,
    setSortQuery,
    handleLoadMore,
    handleExportCsv,
  };
}
