'use client';

import Link from 'next/link';
import { Calendar, MessageCircle } from 'lucide-react';
import { getDeckDisplayName, getDeckMeta } from '@/lib/deck-meta';
import { getDepthPresentation, resolveDepthLevel } from '@/lib/depth-level';
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
      <>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-card p-6 rounded-2xl border border-border shadow-soft animate-pulse h-40"
          />
        ))}
      </>
    );
  }

  if (visibleHistory.length === 0) {
    if (historyLength === 0) {
      return (
        <div className="text-center py-20 animate-slide-up-fade">
          <span className="icon-badge !w-16 !h-16 !rounded-2xl mx-auto mb-5" aria-hidden>
            <MessageCircle className="w-7 h-7" />
          </span>
          <h3 className="text-lg font-art font-bold text-foreground">還沒有紀錄喔</h3>
          <p className="text-muted-foreground mt-2">去抽張卡片，開始你們的第一個話題吧！</p>
          <Link
            href={backToDecksHref}
            className="mt-6 inline-block px-6 py-2.5 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 text-sm font-bold shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            前往大廳
          </Link>
        </div>
      );
    }
    return (
      <div className="text-center py-14 bg-card rounded-2xl border border-border space-section-y">
        <p className="text-foreground font-medium">找不到符合條件的歷史紀錄</p>
        <p className="text-muted-foreground text-sm mt-1">試試調整篩選、關鍵字或排序。</p>
      </div>
    );
  }

  return (
    <>
      {visibleHistory.map((entry, idx) => {
        const deckMeta = getDeckMeta(entry.category);
        const deckTitle = getDeckDisplayName(entry.category);
        const depthLevel = resolveDepthLevel(entry.depth_level);
        const depth = getDepthPresentation(depthLevel);
        const stagger = idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : '';
        return (
          <div
            key={entry.session_id}
            className={`relative bg-card rounded-2xl border shadow-soft overflow-hidden hover:shadow-lift transition-shadow duration-haven ease-haven ${depth.accentFrameClass} ${stagger}`}
          >
            <div className={`absolute inset-x-0 top-0 h-1 ${depth.topAccentClass}`} aria-hidden />
            <div className="bg-muted/50 px-6 pt-5 pb-4 border-b border-border flex justify-between items-start gap-4">
              <div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={`inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wide px-2 py-1 rounded-md ${deckMeta?.badgeClass ?? 'bg-muted text-muted-foreground'}`}
                  >
                    {deckMeta && (
                      <deckMeta.Icon
                        className={`w-3.5 h-3.5 ${deckMeta.iconColor}`}
                        strokeWidth={2.2}
                      />
                    )}
                    {deckTitle}
                  </span>
                  <span
                    className={`inline-flex items-center text-[10px] font-bold tracking-wide px-2 py-1 rounded-md ${depth.badgeClass}`}
                  >
                    Depth {depthLevel} · {depth.label}
                  </span>
                </div>
                <h3 className="font-art font-bold text-foreground mt-2 leading-relaxed">
                  {entry.card_question}
                </h3>
              </div>
              <div className="flex items-center text-xs text-muted-foreground shrink-0 mt-1 tabular-nums">
                <Calendar className="w-3 h-3 mr-1" />
                {new Date(entry.revealed_at).toLocaleDateString()}
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex flex-col items-end">
                <div className="bg-primary text-primary-foreground px-4 py-2 rounded-2xl rounded-tr-sm text-sm">
                  {entry.my_answer}
                </div>
                <span className="text-[10px] text-muted-foreground mt-1 mr-1">我</span>
              </div>
              <div className="flex flex-col items-start">
                <div className="bg-card border border-border text-foreground px-4 py-2 rounded-2xl rounded-tl-sm text-sm">
                  {entry.partner_answer}
                </div>
                <span className="text-[10px] text-muted-foreground mt-1 ml-1">伴侶</span>
              </div>
            </div>
          </div>
        );
      })}
      {hasMore && (
        <div className="pt-1 flex justify-center">
          <button
            onClick={() => void onLoadMore()}
            disabled={loadingMore}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              loadingMore
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97]'
            }`}
          >
            {loadingMore ? '載入中...' : '載入更多歷史'}
          </button>
        </div>
      )}
    </>
  );
}
