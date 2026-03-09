'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useDeckHistory } from '@/features/deck-history/useDeckHistory';
import DeckHistorySummaryCard from '@/features/deck-history/DeckHistorySummaryCard';
import DeckHistoryFiltersBar from '@/features/deck-history/DeckHistoryFiltersBar';
import DeckHistoryList from '@/features/deck-history/DeckHistoryList';

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

  return (
    <div className="min-h-screen bg-muted/40 pb-20">
      <header className="sticky top-0 z-10 bg-card/90 backdrop-blur-md border-b border-border px-4 py-4 flex items-center shadow-card relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
        <Link
          href={backToDecksHref}
          aria-label="返回牌組"
          className="p-2 -ml-2 hover:bg-muted rounded-button transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <ArrowLeft className="w-6 h-6 text-muted-foreground" aria-hidden />
        </Link>
        <h1 className="ml-2 text-xl font-art font-bold text-card-foreground tracking-tight">我們的對話時光</h1>
      </header>

      <main className="p-4 max-w-2xl mx-auto space-y-6 animate-page-enter">
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
      </main>
    </div>
  );
}
