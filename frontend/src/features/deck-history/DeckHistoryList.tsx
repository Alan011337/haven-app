'use client';

import Link from 'next/link';
import { LibraryBig, Search } from 'lucide-react';

import { DeckArchiveCard, DeckStatePanel } from '@/features/decks/ui/DeckPrimitives';
import type { DeckHistoryEntry } from '@/services/deckService';

interface DeckHistoryListProps {
  historyLength: number;
  visibleHistory: DeckHistoryEntry[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  backToDecksHref: string;
  onLoadMore: () => void;
}

export default function DeckHistoryList({
  historyLength,
  visibleHistory,
  loading,
  loadingMore,
  hasMore,
  backToDecksHref,
  onLoadMore,
}: DeckHistoryListProps) {
  if (loading) {
    return (
      <div className="space-y-4" aria-busy="true" aria-live="polite">
        {[1, 2, 3].map((item) => (
          <div
            key={item}
            className="h-56 animate-pulse rounded-[2rem] border border-white/55 bg-white/70 shadow-soft"
            aria-hidden
          />
        ))}
      </div>
    );
  }

  if (visibleHistory.length === 0) {
    if (historyLength === 0) {
      return (
        <DeckStatePanel
          eyebrow="檔案尚未建立"
          title="你們的對話檔案館還沒有任何檔案。"
          description="當第一輪牌卡完成雙向回應後，這裡就會開始留下屬於你們的對話回放。"
          actionHref={backToDecksHref}
          actionLabel="回到牌組圖書館"
          icon={LibraryBig}
          tone="paper"
        />
      );
    }

    return (
      <DeckStatePanel
        eyebrow="暫時沒有匹配"
        title="目前找不到符合條件的檔案。"
        description="這不是沒有資料，而是目前的篩選、時間或關鍵字暫時沒有對上。換個條件再看一次。"
        icon={Search}
        tone="mist"
      />
    );
  }

  return (
    <div className="space-y-4">
      {visibleHistory.map((entry, index) => {
        const staggerClass = index < 5 ? `animate-slide-up-fade${index > 0 ? `-${index}` : ''}` : '';
        return <DeckArchiveCard key={entry.session_id} entry={entry} className={staggerClass} />;
      })}

      {hasMore ? (
        <div className="flex justify-center pt-2">
          <button
            type="button"
            onClick={() => void onLoadMore()}
            disabled={loadingMore}
            className={`rounded-full px-5 py-3 text-sm font-medium transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
              loadingMore
                ? 'border border-white/55 bg-white/68 text-muted-foreground'
                : 'border border-primary/16 bg-primary/8 text-card-foreground shadow-soft hover:-translate-y-0.5 hover:shadow-lift'
            }`}
          >
            {loadingMore ? '正在整理更多檔案…' : '載入更多對話檔案'}
          </button>
        </div>
      ) : historyLength > 0 ? (
        <div className="flex justify-center pt-2">
          <Link
            href={backToDecksHref}
            className="rounded-full border border-white/55 bg-white/72 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            回到牌組圖書館
          </Link>
        </div>
      ) : null}
    </div>
  );
}
