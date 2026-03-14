'use client';

import { useEffect, useMemo } from 'react';
import Link from 'next/link';
import { ArrowLeft, History } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { DECK_META_LIST } from '@/lib/deck-meta';
import { useDeckCardCounts } from '@/hooks/queries';
import { getDeckEditorialCopy } from '@/features/decks/deck-copy';
import { getSelectionChipStateClass, routeLinkCtaClasses, selectionChipBaseClass } from '@/features/decks/ui/routeStyleHelpers';
import {
  DeckCollectionTile,
  DeckStatePanel,
} from '@/features/decks/ui/DeckPrimitives';

const FILTER_MODES = ['all', 'in_progress', 'not_started', 'completed'] as const;
const SORT_MODES = ['recommended', 'progress_desc', 'progress_asc', 'title'] as const;

type FilterMode = (typeof FILTER_MODES)[number];
type SortMode = (typeof SORT_MODES)[number];

const isFilterMode = (value: string): value is FilterMode =>
  (FILTER_MODES as readonly string[]).includes(value);

const isSortMode = (value: string): value is SortMode =>
  (SORT_MODES as readonly string[]).includes(value);

const FILTER_LABELS: Record<FilterMode, string> = {
  all: '全部',
  in_progress: '探索中',
  not_started: '尚未開始',
  completed: '已完成',
};

export default function DecksPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { data: deckStats = {}, isLoading: countsLoading } = useDeckCardCounts();

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
    if (nextQuery === currentQuery) return;

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

    if (!shouldReplace) return;
    const nextQuery = params.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, {
      scroll: false,
    });
  }, [pathname, rawFilterMode, rawSortMode, router, searchParams]);

  const totals = DECK_META_LIST.reduce(
    (acc, deck) => {
      const stats = deckStats[deck.id];
      acc.totalCards += stats?.total_cards ?? 0;
      acc.answeredCards += stats?.answered_cards ?? 0;
      return acc;
    },
    { totalCards: 0, answeredCards: 0 },
  );
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
      if (filterMode === 'all') return true;
      if (filterMode === 'in_progress') return item.isStarted && !item.isCompleted;
      if (filterMode === 'not_started') return !item.isStarted;
      return item.isCompleted;
    });

    filtered.sort((a, b) => {
      if (sortMode === 'progress_desc') return b.completionRate - a.completionRate;
      if (sortMode === 'progress_asc') return a.completionRate - b.completionRate;
      if (sortMode === 'title') return a.deck.title.localeCompare(b.deck.title, 'zh-Hant');
      if (a.statusRank !== b.statusRank) return a.statusRank - b.statusRank;
      return b.completionRate - a.completionRate;
    });

    return filtered;
  }, [deckStats, filterMode, sortMode]);

  const deckRoomQueryString = useMemo(() => {
    const params = new URLSearchParams();
    if (filterMode !== 'all') params.set('filter', filterMode);
    if (sortMode !== 'recommended') params.set('sort', sortMode);
    return params.toString();
  }, [filterMode, sortMode]);

  const buildDeckRoomHref = (deckId: string) =>
    deckRoomQueryString ? `/decks/${deckId}?${deckRoomQueryString}` : `/decks/${deckId}`;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]" aria-hidden />

      <div className="relative mx-auto max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8 md:space-y-10">

        {/* ── Top bar ── */}
        <div className="flex items-center justify-between">
          <Link href="/" className={routeLinkCtaClasses.neutral}>
            <ArrowLeft className="h-4 w-4" aria-hidden />
            回首頁
          </Link>
          <Link href="/decks/history" className={routeLinkCtaClasses.neutral}>
            <History className="h-4 w-4" aria-hidden />
            對話檔案館
          </Link>
        </div>

        {/* ── Page identity — bare typography on gradient ── */}
        <div className="space-y-3 animate-slide-up-fade">
          <h1 className="font-art text-[2rem] leading-[1.05] text-gradient-gold md:text-[2.8rem] xl:text-[3.2rem]">
            牌組收藏
          </h1>
          <p className="text-sm text-muted-foreground">
            {countsLoading
              ? '正在整理收藏…'
              : `${totals.answeredCards}/${totals.totalCards} 題已完成 · ${completedDecks} 套走完整輪`}
          </p>
        </div>

        {/* ── Inline filters — no wrapper card ── */}
        <div className="flex flex-wrap items-center gap-2 animate-slide-up-fade-1">
          {FILTER_MODES.map((mode) => {
            const active = filterMode === mode;
            return (
              <button
                key={mode}
                type="button"
                onClick={() => syncQueryParams(mode, sortMode)}
                className={`${selectionChipBaseClass} ${getSelectionChipStateClass(active)}`}
                aria-pressed={active}
              >
                {FILTER_LABELS[mode]}
              </button>
            );
          })}

          <div className="ml-auto flex items-center gap-2 rounded-full border border-white/55 bg-white/72 px-3 py-2 shadow-soft">
            <label htmlFor="deck-sort" className="type-micro uppercase text-primary/70">
              排序
            </label>
            <select
              id="deck-sort"
              aria-label="排序方式"
              value={sortMode}
              onChange={(event) => {
                const nextSort = event.target.value;
                if (!isSortMode(nextSort)) return;
                syncQueryParams(filterMode, nextSort);
              }}
              className="select-premium min-w-[7.5rem] border-0 bg-transparent type-caption text-card-foreground shadow-none"
            >
              <option value="recommended">推薦排序</option>
              <option value="progress_desc">進度高到低</option>
              <option value="progress_asc">進度低到高</option>
              <option value="title">名稱排序</option>
            </select>
          </div>
        </div>

        {/* ── Collection grid ── */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 animate-slide-up-fade-2">
          {deckCards.length === 0 && !countsLoading ? (
            <div className="sm:col-span-2 lg:col-span-3 xl:col-span-4">
              <DeckStatePanel
                eyebrow="暫無結果"
                title="目前沒有符合條件的牌組"
                description="換個條件再看一次。"
                actionLabel="清除篩選"
                onAction={() => syncQueryParams('all', 'recommended')}
              />
            </div>
          ) : null}

          {deckCards.map(({ deck, totalCards, answeredCards, completionRate }) => {
            const editorialCopy = getDeckEditorialCopy(deck.id);
            const isFeatured = nextFocusDeck?.deck.id === deck.id;

            return (
              <div
                key={deck.id}
                className={isFeatured ? 'sm:col-span-2' : ''}
              >
                <DeckCollectionTile
                  deck={deck}
                  href={buildDeckRoomHref(deck.id)}
                  shortHook={editorialCopy?.shortHook ?? deck.description}
                  progressLabel={countsLoading ? '整理中…' : `${answeredCards}/${totalCards}`}
                  progressWidth={countsLoading ? 0 : completionRate}
                  emphasis={isFeatured ? 'feature' : 'standard'}
                  loading={countsLoading}
                />
              </div>
            );
          })}
        </section>

      </div>
    </div>
  );
}
