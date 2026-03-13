'use client';

import { useEffect, useMemo } from 'react';
import Link from 'next/link';
import { History, Sparkles } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { DECK_META_LIST } from '@/lib/deck-meta';
import { useDeckCardCounts } from '@/hooks/queries';
import { GlassCard } from '@/components/haven/GlassCard';
import { getDeckEditorialCopy } from '@/features/decks/deck-copy';
import {
  DeckCollectionTile,
  DeckHeroPanel,
  DeckShell,
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

  const heroAside = (
    <GlassCard className="overflow-hidden rounded-[2rem] border-white/55 bg-[linear-gradient(180deg,rgba(249,252,250,0.84),rgba(240,246,242,0.78))] p-5">
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="text-[0.7rem] uppercase tracking-[0.3em] text-primary/72">今晚焦點</p>
          <h3 className="font-art text-[1.5rem] leading-tight text-card-foreground">
            {countsLoading
              ? '正在整理最適合延續的牌組…'
              : nextFocusDeck
                ? `下一步繼續 ${nextFocusDeck.deck.title}`
                : '你們已經把目前的牌組走得很完整。'}
          </h3>
          <p className="text-sm leading-7 text-muted-foreground">
            {countsLoading
              ? '先把整體進度整理出來，再替今晚選一個最值得往下走的方向。'
              : nextFocusDeck
                ? getDeckEditorialCopy(nextFocusDeck.deck.id)?.shortHook ??
                  '從最接近完成的牌組繼續，會讓整條對話體驗更有延續感。'
                : '如果想換個方向，也可以直接從檔案館回看過去最常聊的主題。'}
          </p>
        </div>
        <div className="space-y-3">
          {nextFocusDeck ? (
            <Link
              href={buildDeckRoomHref(nextFocusDeck.deck.id)}
              className="inline-flex items-center gap-2 rounded-full border border-primary/16 bg-primary/8 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
            >
              繼續這個牌組
              <Sparkles className="h-4 w-4" aria-hidden />
            </Link>
          ) : null}
          <Link
            href="/decks/history"
            className="inline-flex items-center gap-2 rounded-full border border-white/55 bg-white/72 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
          >
            打開對話檔案館
            <History className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </div>
    </GlassCard>
  );

  return (
    <DeckShell
      eyebrow="牌組圖書館"
      title="牌組圖書館"
      subtitle="把今晚的對話選成一種方向，而不是只抽一張隨機卡。這裡是你們共同的主題收藏庫，從日常到深談，都可以找到剛剛好的入口。"
      backHref="/"
      backLabel="回首頁"
      actions={
        <Link
          href="/decks/history"
          className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/74 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <History className="h-4 w-4" aria-hidden />
          對話檔案館
        </Link>
      }
      containerClassName="max-w-7xl"
    >
      <DeckHeroPanel
        eyebrow="今日館藏"
        title="今晚想把關係往哪個方向打開？"
        description="每一套牌組都不是一堆題目的集合，而是一種對話場景。先選一個適合今天的方向，再讓問題替你們把節奏帶進去。"
        metrics={[
          {
            label: '已解鎖',
            value: countsLoading ? '...' : `${totals.answeredCards}/${totals.totalCards}`,
            note: '目前累積完成的題數',
          },
          {
            label: '整體進度',
            value: countsLoading ? '...' : `${overallCompletionRate}%`,
            note: '所有牌組的總體完成比例',
          },
          {
            label: '完整牌組',
            value: countsLoading ? '...' : `${completedDecks}/${DECK_META_LIST.length}`,
            note: '已經走完整輪探索的分類數量',
          },
        ]}
        aside={heroAside}
      />

      <GlassCard className="overflow-hidden rounded-[2rem] border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(247,243,236,0.76))] p-5 md:p-6">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
            <div className="space-y-2">
              <p className="text-[0.7rem] uppercase tracking-[0.3em] text-primary/72">館藏整理</p>
              <h2 className="font-art text-[1.55rem] text-card-foreground">按進度、狀態或名稱整理今晚的牌組。</h2>
              <p className="text-sm leading-7 text-muted-foreground">
                保留你現在的篩選與排序；進入某個牌組再返回時，瀏覽位置不會被打散。
              </p>
            </div>
            <div className="inline-flex items-center gap-3 rounded-full border border-white/55 bg-white/72 px-4 py-3 text-sm text-muted-foreground shadow-soft">
              <span className="uppercase tracking-[0.22em] text-primary/72">顯示中</span>
              <span className="tabular-nums text-card-foreground">{deckCards.length}/{DECK_META_LIST.length}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {FILTER_MODES.map((mode) => {
              const active = filterMode === mode;
              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => syncQueryParams(mode, sortMode)}
                  className={`rounded-full border px-4 py-2 text-xs font-medium transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                    active
                      ? 'border-primary/20 bg-primary/10 text-card-foreground shadow-soft'
                      : 'border-white/55 bg-white/66 text-muted-foreground hover:border-primary/16 hover:text-card-foreground'
                  }`}
                  aria-pressed={active}
                >
                  {mode === 'all'
                    ? '全部牌組'
                    : mode === 'in_progress'
                      ? '正在探索'
                      : mode === 'not_started'
                        ? '尚未開始'
                        : '已完整走過'}
                </button>
              );
            })}

            <div className="ml-auto flex items-center gap-2 rounded-full border border-white/55 bg-white/72 px-3 py-2 shadow-soft">
              <label htmlFor="deck-sort" className="text-xs uppercase tracking-[0.2em] text-primary/70">
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
                className="select-premium min-w-[7.5rem] border-0 bg-transparent text-xs shadow-none"
              >
                <option value="recommended">推薦排序</option>
                <option value="progress_desc">進度高到低</option>
                <option value="progress_asc">進度低到高</option>
                <option value="title">名稱排序</option>
              </select>
            </div>
          </div>
        </div>
      </GlassCard>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {deckCards.length === 0 && !countsLoading ? (
          <div className="lg:col-span-12">
            <DeckStatePanel
              eyebrow="暫無結果"
              title="目前沒有符合條件的牌組"
              description="這不是沒有內容，只是目前的篩選條件把它們暫時收起來了。換個條件再看一次，圖書館就會重新打開。"
              actionLabel="清除篩選"
              onAction={() => syncQueryParams('all', 'recommended')}
            />
          </div>
        ) : null}

        {deckCards.map(({ deck, totalCards, answeredCards, completionRate, isCompleted, isStarted }, index) => {
          const editorialCopy = getDeckEditorialCopy(deck.id);
          const isFeature = index === 0 || nextFocusDeck?.deck.id === deck.id;
          const gridClass = isFeature
            ? 'lg:col-span-7 xl:col-span-6'
            : index % 3 === 0
              ? 'lg:col-span-5 xl:col-span-3'
              : 'lg:col-span-5 xl:col-span-3';

          return (
            <div key={deck.id} className={gridClass}>
              <DeckCollectionTile
                deck={deck}
                href={buildDeckRoomHref(deck.id)}
                eyebrow={editorialCopy?.eyebrow ?? '主題收藏'}
                spotlight={editorialCopy?.spotlight ?? deck.description}
                shortHook={editorialCopy?.shortHook ?? deck.description}
                progressLabel={countsLoading ? '進度整理中' : `${answeredCards}/${totalCards} 已完成`}
                countLabel={countsLoading ? '題庫整理中' : `${totalCards} 題`}
                statusLabel={
                  countsLoading
                    ? '整理中'
                    : isCompleted
                      ? '完整走過'
                      : isStarted
                        ? '正在探索'
                        : '尚未開始'
                }
                progressWidth={countsLoading ? 0 : completionRate}
                emphasis={isFeature ? 'feature' : 'standard'}
                loading={countsLoading}
              />
            </div>
          );
        })}
      </section>
    </DeckShell>
  );
}
