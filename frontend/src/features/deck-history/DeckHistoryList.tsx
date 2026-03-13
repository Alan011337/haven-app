'use client';

import Link from 'next/link';
import { LibraryBig, Search } from 'lucide-react';

import Button from '@/components/ui/Button';
import { DeckArchiveCard, DeckStatePanel } from '@/features/decks/ui/DeckPrimitives';
import type { DeckHistoryEntry } from '@/services/deckService';

const historyBackLinkClass =
  'inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/55 bg-white/72 px-5 py-3 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium';

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
      <div className="stack-section" aria-busy="true" aria-live="polite">
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
    <div className="stack-section">
      {visibleHistory.map((entry, index) => {
        const staggerClass = index < 5 ? `animate-slide-up-fade${index > 0 ? `-${index}` : ''}` : '';
        return <DeckArchiveCard key={entry.session_id} entry={entry} className={staggerClass} />;
      })}

      {hasMore ? (
        <div className="flex justify-center pt-2">
          <Button
            type="button"
            variant={loadingMore ? 'secondary' : 'primary'}
            size="lg"
            loading={loadingMore}
            onClick={() => void onLoadMore()}
            disabled={loadingMore}
          >
            {loadingMore ? '正在整理更多檔案…' : '載入更多對話檔案'}
          </Button>
        </div>
      ) : historyLength > 0 ? (
        <div className="flex justify-center pt-2">
          <Link
            href={backToDecksHref}
            className={historyBackLinkClass}
          >
            回到牌組圖書館
          </Link>
        </div>
      ) : null}
    </div>
  );
}
