'use client';

import { useEffect, useMemo } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { DECK_META_LIST } from '@/lib/deck-meta';
import { useDeckCardCounts } from '@/hooks/queries';
import { GlassCard } from '@/components/haven/GlassCard';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { CardBackVariant } from '@/components/haven/CardBackVariant';

const FILTER_MODES = ['all', 'in_progress', 'not_started', 'completed'] as const;
const SORT_MODES = ['recommended', 'progress_desc', 'progress_asc', 'title'] as const;

type FilterMode = (typeof FILTER_MODES)[number];
type SortMode = (typeof SORT_MODES)[number];

const isFilterMode = (value: string): value is FilterMode =>
  (FILTER_MODES as readonly string[]).includes(value);

const isSortMode = (value: string): value is SortMode =>
  (SORT_MODES as readonly string[]).includes(value);

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
    <div className="min-h-screen bg-ethereal-mesh pb-20">
      <header className="sticky top-0 z-10 bg-card/90 backdrop-blur-md border-b border-border space-page flex items-center shadow-card py-4">
        <Link
          href="/"
          aria-label="返回首頁"
          className="p-2 -ml-2 hover:bg-muted rounded-button transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <ArrowLeft className="w-6 h-6 text-muted-foreground" aria-hidden />
        </Link>
        <h1 className="ml-2 text-title font-art font-bold text-card-foreground tracking-tight">牌組圖書館</h1>
      </header>

      <main className="space-page space-y-6 max-w-6xl mx-auto">
        <div className="text-center space-y-2 mb-6 mt-2">
          <h2 className="text-title font-art font-bold text-gradient-gold tracking-tight">今天想聊點什麼？</h2>
          <p className="text-caption text-foreground/80 tracking-wide">選擇一套牌組，開啟無限話題。</p>
        </div>

        <GlassCard className="p-5 md:p-6 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <p className="text-[11px] font-art font-semibold tracking-[0.18em] text-muted-foreground uppercase">學習進度</p>
              {countsLoading ? (
                <div className="space-y-2">
                  <div className="h-6 w-40 rounded-md bg-muted animate-pulse" aria-hidden />
                  <div className="h-4 w-56 rounded-md bg-muted animate-pulse" aria-hidden />
                </div>
              ) : (
                <>
                  <h3 className="text-xl md:text-2xl font-bold text-card-foreground tabular-nums">
                    已完成 {totals.answeredCards}/{totals.totalCards} 題
                  </h3>
                  <p className="text-body text-muted-foreground tabular-nums">
                    八大牌組進度 {overallCompletionRate}% · 已全破 {completedDecks}/{DECK_META_LIST.length} 套
                  </p>
                </>
              )}
            </div>
            {!countsLoading && nextFocusDeck && (
              <Link
                href={buildDeckRoomHref(nextFocusDeck.deck.id)}
                className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-colors duration-haven-fast ease-haven rounded-button inline-block"
              >
                <Button variant="primary" size="sm">
                  繼續 {nextFocusDeck.deck.title}
                </Button>
              </Link>
            )}
          </div>
          <div className="mt-4 h-2 w-full rounded-full bg-muted shadow-glass-inset overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary via-primary/80 to-primary/60 transition-all duration-haven ease-haven"
              style={{ width: `${countsLoading ? 0 : Math.max(0, Math.min(100, overallCompletionRate))}%` }}
            />
          </div>
        </GlassCard>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {(['all', 'in_progress', 'not_started', 'completed'] as const).map((mode) => (
              <Badge
                key={mode}
                variant={filterMode === mode ? 'default' : 'outline'}
                size="md"
                className={`cursor-pointer transition-colors duration-haven-fast ease-haven ${
                  filterMode === mode
                    ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-primary shadow-satin-button'
                    : 'hover:bg-muted'
                }`}
                onClick={() => syncQueryParams(mode, sortMode)}
                role="button"
                aria-pressed={filterMode === mode}
              >
                {mode === 'all' ? '全部' : mode === 'in_progress' ? '進行中' : mode === 'not_started' ? '未開始' : '已完成'}
              </Badge>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <select
              id="deck-sort"
              aria-label="排序方式"
              value={sortMode}
              onChange={(event) => {
                const nextSort = event.target.value;
                if (!isSortMode(nextSort)) {
                  return;
                }
                syncQueryParams(filterMode, nextSort);
              }}
              className="select-premium text-xs"
            >
              <option value="recommended">推薦排序</option>
              <option value="progress_desc">進度高到低</option>
              <option value="progress_asc">進度低到高</option>
              <option value="title">名稱排序</option>
            </select>
            <span className="text-caption text-muted-foreground tabular-nums whitespace-nowrap">
              {deckCards.length}/{DECK_META_LIST.length}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
          {deckCards.length === 0 && !countsLoading && (
            <GlassCard className="col-span-full p-10 text-center animate-slide-up-fade" role="status">
              <p className="text-body font-art font-semibold text-foreground">目前沒有符合條件的牌組</p>
              <p className="text-caption text-muted-foreground mt-1">換個篩選試試看。</p>
            </GlassCard>
          )}
          {deckCards.map(({ deck, totalCards, answeredCards, completionRate, isCompleted, isStarted }, idx) => {
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
            const staggerClass = idx < 6 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : '';
            return (
              <Link key={deck.id} href={buildDeckRoomHref(deck.id)} className={staggerClass}>
                <div
                  className={`
                    relative overflow-hidden rounded-2xl p-4 sm:p-6 min-h-[11rem] sm:h-44 flex flex-col justify-between
                    shadow-soft transition-all duration-haven ease-haven hover:scale-[1.02] hover:shadow-lift cursor-pointer
                    bg-gradient-to-br ${deck.color} group
                  `}
                >
                  <div className="absolute top-3 right-3 w-12 h-16 rounded-lg overflow-hidden shadow-soft ring-2 ring-foreground/10" aria-hidden>
                    <CardBackVariant deck={deck}>
                      <deck.Icon className="w-5 h-5 text-white/90" strokeWidth={2} aria-hidden />
                    </CardBackVariant>
                  </div>

                  <div className="absolute top-0 right-0 -mt-2 -mr-2 opacity-[0.08] select-none pointer-events-none group-hover:opacity-[0.15] transition-opacity duration-haven-fast ease-haven">
                    <deck.Icon className={`w-24 h-24 ${deck.iconColor}`} strokeWidth={1.7} />
                  </div>

                  <div>
                    <div className="mb-2">
                      <deck.Icon className={`w-7 h-7 ${deck.iconColor}`} strokeWidth={2.2} />
                    </div>
                    <h3 className={`text-xl font-art font-bold truncate ${deck.textColor}`}>{deck.title}</h3>
                    <p className={`text-sm mt-1 opacity-80 line-clamp-2 ${deck.textColor}`}>
                      {deck.description}
                    </p>
                  </div>

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
                        <div className="h-1.5 w-full rounded-full bg-white/30 shadow-glass-inset overflow-hidden">
                          <div
                            className="h-full rounded-full bg-white/85 transition-all duration-haven ease-haven"
                            style={{ width: `${progressWidth}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className={`text-xs font-medium tabular-nums ${deck.textColor} opacity-80`}>
                            {progressLabel} · {countLabel}
                          </span>
                          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full bg-white/40 backdrop-blur-sm ${deck.textColor}`}>
                            {statusLabel} →
                          </span>
                        </div>
                      </>
                    )}
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
