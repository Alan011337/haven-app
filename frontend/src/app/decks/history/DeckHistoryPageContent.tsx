'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { LibraryBig } from 'lucide-react';

import { DeckShell } from '@/features/decks/ui/DeckPrimitives';
import { getDeckEditorialCopy } from '@/features/decks/deck-copy';
import { useDeckHistory } from '@/features/deck-history/useDeckHistory';
import DeckHistorySummaryCard from '@/features/deck-history/DeckHistorySummaryCard';
import DeckHistoryFiltersBar from '@/features/deck-history/DeckHistoryFiltersBar';
import DeckHistoryList from '@/features/deck-history/DeckHistoryList';
import { routeLinkCtaClasses } from '@/features/decks/ui/routeStyleHelpers';

export default function DeckHistoryPageContent() {
  const {
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
  } = useDeckHistory();

  const archiveSubtitle = useMemo(() => {
    const categoryCopy = getDeckEditorialCopy(normalizedCategoryFilter);
    if (categoryCopy) {
      return `${categoryCopy.archivePrompt} 你可以依時間、關鍵字或牌組，把這些對話重新整理成一份可回讀的檔案。`;
    }
    return '把你們已經完成的牌卡回應整理成一座真正可回讀的檔案館，而不是一串普通列表。';
  }, [normalizedCategoryFilter]);

  return (
    <DeckShell
      eyebrow="對話檔案館"
      title="對話檔案館"
      subtitle={archiveSubtitle}
      backHref={backToDecksHref}
      backLabel="回牌組圖書館"
      actions={
        <Link
          href="/decks"
          className={routeLinkCtaClasses.neutral}
        >
          <LibraryBig className="h-4 w-4" aria-hidden />
          回到收藏
        </Link>
      }
      containerClassName="max-w-6xl"
    >
      <DeckHistorySummaryCard
        summary={summary}
        summaryLoading={summaryLoading}
        summaryTopCategoryDisplay={summaryTopCategoryDisplay}
        historyLength={history.length}
      />

      <DeckHistoryFiltersBar
        normalizedCategoryFilter={normalizedCategoryFilter}
        dateRangeMode={dateRangeMode}
        sortMode={sortMode}
        searchKeyword={searchKeyword}
        setCategoryQuery={setCategoryQuery}
        setDateRangeQuery={setDateRangeQuery}
        setSortQuery={setSortQuery}
        setSearchKeyword={setSearchKeyword}
        onExportCsv={handleExportCsv}
      />

      <DeckHistoryList
        historyLength={history.length}
        visibleHistory={visibleHistory}
        loading={loading}
        loadingMore={loadingMore}
        hasMore={hasMore}
        backToDecksHref={backToDecksHref}
        onLoadMore={handleLoadMore}
      />
    </DeckShell>
  );
}
