'use client';

import { useEffect, useMemo } from 'react';
import { History, Sparkles } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { DECK_META_LIST } from '@/lib/deck-meta';
import { useDeckCardCounts } from '@/hooks/queries';
import Badge from '@/components/ui/Badge';
import { getDeckEditorialCopy } from '@/features/decks/deck-copy';
import {
  getSelectionChipStateClass,
  selectionChipBaseClass,
} from '@/features/decks/ui/routeStyleHelpers';
import { DeckStatePanel } from '@/features/decks/ui/DeckPrimitives';
import {
  DeckLibraryArchiveShortcut,
  DeckLibraryBrowseBand,
  DeckLibraryCompanionCard,
  DeckLibraryCover,
  DeckLibraryFallbackCard,
  DeckLibraryFeaturedCard,
  DeckLibraryRailCard,
  DeckLibrarySectionHeader,
  DeckLibraryShelfCard,
  DeckLibraryShell,
} from './DeckLibraryPrimitives';

const FILTER_MODES = ['all', 'in_progress', 'not_started', 'completed'] as const;
const SORT_MODES = ['recommended', 'progress_desc', 'progress_asc', 'title'] as const;

type FilterMode = (typeof FILTER_MODES)[number];
type SortMode = (typeof SORT_MODES)[number];
type DeckCardStatusVariant = 'metadata' | 'status' | 'filter';

const isFilterMode = (value: string): value is FilterMode =>
  (FILTER_MODES as readonly string[]).includes(value);

const isSortMode = (value: string): value is SortMode =>
  (SORT_MODES as readonly string[]).includes(value);

function getStatusMeta(
  countsLoading: boolean,
  isCompleted: boolean,
  isStarted: boolean,
): { label: string; variant: DeckCardStatusVariant } {
  if (countsLoading) {
    return { label: '整理中', variant: 'metadata' };
  }
  if (isCompleted) {
    return { label: '完整走過', variant: 'status' };
  }
  if (isStarted) {
    return { label: '正在探索', variant: 'filter' };
  }
  return { label: '尚未開始', variant: 'metadata' };
}

function getFeaturedCtaLabel(
  countsLoading: boolean,
  isCompleted: boolean,
  isStarted: boolean,
) {
  if (countsLoading) return '先看看這套';
  if (isCompleted) return '重新翻開這套';
  if (isStarted) return '繼續這段對話';
  return '今晚就從這套開始';
}

function getBrowseBandCopy(filterMode: FilterMode) {
  switch (filterMode) {
    case 'in_progress':
      return {
        title: '把還在延續中的題組放回今晚的前排。',
        description:
          '這裡只留下你們已經開始、但還沒說完的方向。篩選與排序會跟著你進出牌組，讓這趟瀏覽不被打斷。',
      };
    case 'not_started':
      return {
        title: '從尚未開始的館藏裡，挑一套更適合今晚的入口。',
        description:
          '有些牌組適合第一次翻開時就留足空氣。這一排保留了那些還沒被打開，但很值得慢慢開始的方向。',
      };
    case 'completed':
      return {
        title: '重新翻看走過的牌組，會讀到另一層答案。',
        description:
          '完整走過並不代表已經結束。你們現在的心境，可能會讓同一套牌組長出新的閱讀方式。',
      };
    default:
      return {
        title: '按狀態、進度或名稱，把今晚的館藏重新排成一條更優雅的瀏覽路徑。',
        description:
          '保留你現在的篩選與排序；進入某個牌組再返回時，圖書館仍然維持你剛剛挑好的節奏。',
      };
  }
}

function getCompanionSectionCopy(filterMode: FilterMode) {
  switch (filterMode) {
    case 'in_progress':
      return {
        title: '緊鄰封面的兩個延續方向',
        description:
          '如果今晚不只想接回一條線，這兩套是離你們現在的節奏最近、也最容易往下走的 companion picks。',
      };
    case 'not_started':
      return {
        title: '另外兩個值得先讀一眼的入口',
        description:
          '不一定非得只選封面那一套。這兩個方向也保留了足夠的空氣，適合慢慢開始。',
      };
    case 'completed':
      return {
        title: '另外兩套值得重新翻開的收藏',
        description:
          '走過一輪之後再讀，常常會發現以前略過的句子，現在反而最有份量。',
      };
    default:
      return {
        title: '緊鄰今晚封面的兩個方向',
        description:
          '如果封面那套還不是今晚最有感的入口，先看看旁邊這兩套。它們是同一個館藏裡，最接近現在情緒的 companion pieces。',
      };
  }
}

function getShelfSectionCopy(filterMode: FilterMode) {
  switch (filterMode) {
    case 'in_progress':
      return {
        title: '其餘正在探索的館藏',
        description:
          '剩下的題組仍然保留在館內，等你們下一次想把未說完的部分接回來。',
      };
    case 'not_started':
      return {
        title: '其餘尚未開始的館藏',
        description:
          '不必一次翻開太多。這些還在架上的題組會留在更安靜的層架裡，等你們真正想開始時再拿下來。',
      };
    case 'completed':
      return {
        title: '其餘已完整走過的收藏',
        description:
          '完整走過的牌組像一份已讀過的館藏，不會消失，只會在回讀時長出新的份量。',
      };
    default:
      return {
        title: '其餘館藏',
        description:
          '封面與旁架先幫你把注意力聚焦，其餘題組則留在更安靜的收藏層裡，等你慢慢挑。',
      };
  }
}

function getRailCopy(
  filterMode: FilterMode,
  countsLoading: boolean,
  heroDeckTitle?: string,
) {
  if (countsLoading) {
    return {
      title: '先替今晚整理一個更安靜的入口。',
      description:
        '把館藏的進度與狀態整理清楚之後，封面與旁架才會更像一間值得慢慢逛的圖書館。',
    };
  }

  if (!heroDeckTitle) {
    return {
      title: '圖書館暫時把這組條件下的館藏收起來了。',
      description:
        '換個條件再看一次，封面就會重新亮起。這裡仍然保留整體的閱讀節奏，不會忽然退化成空白頁。',
    };
  }

  switch (filterMode) {
    case 'in_progress':
      return {
        title: `今晚先把 ${heroDeckTitle} 放回封面。`,
        description:
          '從仍在進行中的牌組接回去，通常比重開另一套更有延續感，也更容易保住對話的溫度。',
      };
    case 'not_started':
      return {
        title: `${heroDeckTitle} 很適合成為今晚的新入口。`,
        description:
          '尚未開始並不代表陌生，反而代表你們還有一整段完整的第一輪對話可以慢慢展開。',
      };
    case 'completed':
      return {
        title: `重新翻開 ${heroDeckTitle}，會看見新的答案。`,
        description:
          '同一套題組在不同時間重讀，常常會長出另一種誠實。這是 completed shelf 最值得回來的原因。',
      };
    default:
      return {
        title: `${heroDeckTitle} 已經先替今晚佔好了封面位置。`,
        description:
          '圖書館不是把所有館藏同時推到你面前，而是先替你挑出一套最有機會被今晚真正打開的方向。',
      };
  }
}

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

  const heroDeck = deckCards[0] ?? null;
  const companionDecks = deckCards.slice(1, 3);
  const shelfDecks = deckCards.slice(3);
  const browseBandCopy = getBrowseBandCopy(filterMode);
  const companionSectionCopy = getCompanionSectionCopy(filterMode);
  const shelfSectionCopy = getShelfSectionCopy(filterMode);
  const railCopy = getRailCopy(filterMode, countsLoading, heroDeck?.deck.title);

  const sortControl = (
    <div className="flex items-center gap-2 rounded-full border border-white/55 bg-white/74 px-3 py-2 shadow-soft">
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
  );

  return (
    <DeckLibraryShell
      backHref="/"
      backLabel="回首頁"
      actions={<DeckLibraryArchiveShortcut />}
    >
      <DeckLibraryCover
        eyebrow="Curated Relationship Library"
        title="別把它當成一排題組；把它當成你們共同收藏的對話館藏。"
        description="Deck Library 不是一個平鋪直敘的 catalog。它更像一間被慢慢挑過的關係圖書館，讓每一套牌組都帶著不同的情緒承諾與敘事重量，等你們用今晚的節奏去翻開。"
        metrics={[
          {
            label: '已解鎖',
            value: countsLoading ? '...' : `${totals.answeredCards}/${totals.totalCards}`,
            note: '你們目前已經走過的總題數',
          },
          {
            label: '整體進度',
            value: countsLoading ? '...' : `${overallCompletionRate}%`,
            note: '所有館藏累積完成的比例',
          },
          {
            label: '完整收藏',
            value: countsLoading ? '...' : `${completedDecks}/${DECK_META_LIST.length}`,
            note: '已完整走過一輪的牌組數量',
          },
        ]}
        featured={
          heroDeck ? (
            <DeckLibraryFeaturedCard
              deck={heroDeck.deck}
              href={buildDeckRoomHref(heroDeck.deck.id)}
              eyebrow={(getDeckEditorialCopy(heroDeck.deck.id)?.eyebrow ?? '主題收藏').toUpperCase()}
              spotlight={getDeckEditorialCopy(heroDeck.deck.id)?.spotlight ?? heroDeck.deck.description}
              shortHook={getDeckEditorialCopy(heroDeck.deck.id)?.shortHook ?? heroDeck.deck.description}
              progressLabel={
                countsLoading
                  ? '進度整理中'
                  : `${heroDeck.answeredCards}/${heroDeck.totalCards} 已完成`
              }
              countLabel={countsLoading ? '題庫整理中' : `${heroDeck.totalCards} 題`}
              statusLabel={
                getStatusMeta(countsLoading, heroDeck.isCompleted, heroDeck.isStarted).label
              }
              statusVariant={
                getStatusMeta(countsLoading, heroDeck.isCompleted, heroDeck.isStarted).variant
              }
              progressWidth={countsLoading ? 0 : heroDeck.completionRate}
              ctaLabel={getFeaturedCtaLabel(countsLoading, heroDeck.isCompleted, heroDeck.isStarted)}
              loading={countsLoading}
            />
          ) : (
            <DeckLibraryFallbackCard
              title="這組條件下暫時沒有亮起來的封面。"
              description="圖書館沒有消失，只是目前的篩選把能放到封面的牌組都暫時收起來了。換個條件，它就會重新打開。"
            />
          )
        }
        rail={
          <>
            <DeckLibraryRailCard
              eyebrow="館長手記"
              title={railCopy.title}
              description={railCopy.description}
              actionHref={heroDeck ? buildDeckRoomHref(heroDeck.deck.id) : undefined}
              actionLabel={heroDeck ? '查看封面牌組' : undefined}
              icon={Sparkles}
            />
            <DeckLibraryRailCard
              eyebrow="Archive Access"
              title="如果想慢慢回讀，檔案館會比首頁更安靜。"
              description="把已經發生過的對話收成一份可回看的館藏，常常比繼續往前抽新題更能提醒你們曾經怎麼靠近彼此。"
              actionHref="/decks/history"
              actionLabel="前往對話檔案館"
              icon={History}
            />
          </>
        }
      />

      <DeckLibraryBrowseBand
        eyebrow="Browse the Collection"
        title={browseBandCopy.title}
        description={browseBandCopy.description}
        resultCount={deckCards.length}
        totalCount={DECK_META_LIST.length}
        controls={
          <>
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
          </>
        }
        sortControl={sortControl}
      />

      {deckCards.length === 0 && !countsLoading ? (
        <DeckStatePanel
          eyebrow="暫無結果"
          title="目前沒有符合條件的牌組"
          description="這不是沒有館藏，只是目前的篩選條件把它們暫時收起來了。換個條件再看一次，圖書館就會重新打開。"
          actionLabel="清除篩選"
          onAction={() => syncQueryParams('all', 'recommended')}
        />
      ) : null}

      {companionDecks.length > 0 ? (
        <section className="space-y-4">
          <DeckLibrarySectionHeader
            eyebrow="Companion Picks"
            title={companionSectionCopy.title}
            description={companionSectionCopy.description}
            aside={
              <Badge
                variant="metadata"
                size="md"
                className="bg-white/76 text-primary/72 shadow-soft"
              >
                {companionDecks.length} 套相鄰館藏
              </Badge>
            }
          />

          <div className="grid gap-4 lg:grid-cols-2">
            {companionDecks.map((item) => {
              const editorialCopy = getDeckEditorialCopy(item.deck.id);
              const status = getStatusMeta(countsLoading, item.isCompleted, item.isStarted);

              return (
                <DeckLibraryCompanionCard
                  key={item.deck.id}
                  deck={item.deck}
                  href={buildDeckRoomHref(item.deck.id)}
                  eyebrow={editorialCopy?.eyebrow ?? '主題收藏'}
                  spotlight={editorialCopy?.spotlight ?? item.deck.description}
                  shortHook={editorialCopy?.shortHook ?? item.deck.description}
                  progressLabel={
                    countsLoading ? '進度整理中' : `${item.answeredCards}/${item.totalCards} 已完成`
                  }
                  countLabel={countsLoading ? '題庫整理中' : `${item.totalCards} 題`}
                  statusLabel={status.label}
                  statusVariant={status.variant}
                  progressWidth={countsLoading ? 0 : item.completionRate}
                  loading={countsLoading}
                />
              );
            })}
          </div>
        </section>
      ) : null}

      {shelfDecks.length > 0 ? (
        <section className="space-y-4">
          <DeckLibrarySectionHeader
            eyebrow="Quiet Shelf"
            title={shelfSectionCopy.title}
            description={shelfSectionCopy.description}
            aside={
              <Badge
                variant="metadata"
                size="md"
                className="bg-white/76 text-primary/72 shadow-soft"
              >
                其餘 {shelfDecks.length} 套
              </Badge>
            }
          />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {shelfDecks.map((item) => {
              const editorialCopy = getDeckEditorialCopy(item.deck.id);
              const status = getStatusMeta(countsLoading, item.isCompleted, item.isStarted);

              return (
                <DeckLibraryShelfCard
                  key={item.deck.id}
                  deck={item.deck}
                  href={buildDeckRoomHref(item.deck.id)}
                  eyebrow={editorialCopy?.eyebrow ?? '主題收藏'}
                  spotlight={editorialCopy?.spotlight ?? item.deck.description}
                  shortHook={editorialCopy?.shortHook ?? item.deck.description}
                  progressLabel={
                    countsLoading ? '進度整理中' : `${item.answeredCards}/${item.totalCards} 已完成`
                  }
                  countLabel={countsLoading ? '題庫整理中' : `${item.totalCards} 題`}
                  statusLabel={status.label}
                  statusVariant={status.variant}
                  progressWidth={countsLoading ? 0 : item.completionRate}
                  loading={countsLoading}
                />
              );
            })}
          </div>
        </section>
      ) : null}
    </DeckLibraryShell>
  );
}
