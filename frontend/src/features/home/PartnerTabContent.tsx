'use client';

import { BookHeart, HeartHandshake, RefreshCw } from 'lucide-react';
import PartnerJournalCard from '@/components/features/PartnerJournalCard';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import PartnerSafetyBanner from '@/components/features/PartnerSafetyBanner';
import {
  EditorialDeferredState,
  EditorialEmptyState,
  EditorialPaperCard,
  EditorialTimelineColumn,
  HomeCoverStage,
  TimelineDateRail,
} from '@/features/home/HomePrimitives';
import { resolveHomeTimelineStage } from '@/lib/home-timeline-state';
import { Journal } from '@/types';

interface PartnerTabContentProps {
  partnerJournals: Journal[];
  loading: boolean;
  timelineUnavailable: boolean;
  partnerSafetyBanner: { latestSevereId: string; severeCount: number } | null;
  onRefresh: () => void;
  onDismissSafetyBanner: () => void;
}

function formatLetterDate(value: string) {
  const date = new Date(value);
  return {
    label: date.toLocaleDateString('zh-TW', {
      month: 'long',
      day: 'numeric',
    }),
    meta: date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      weekday: 'long',
      hour: '2-digit',
      minute: '2-digit',
    }),
  };
}

export default function PartnerTabContent({
  partnerJournals,
  loading,
  timelineUnavailable,
  partnerSafetyBanner,
  onRefresh,
  onDismissSafetyBanner,
}: PartnerTabContentProps) {
  const timelineStage = resolveHomeTimelineStage({
    mounted: true,
    loading,
    unavailable: timelineUnavailable,
    itemCount: partnerJournals.length,
  });

  return (
    <div className="space-y-[var(--space-section)]">
      <HomeCoverStage
        eyebrow="Partner Letters"
        title="把對方今天留下的內容，當成一封安靜展開的來信。"
        description="這一頁刻意減少通知感與效率感。你不需要快速處理它，只需要在夠平穩的節奏裡慢慢讀。"
        pulse={
          <>
            今天共收進 <strong className="font-medium text-card-foreground">{partnerJournals.length} 則來信</strong>。
            首頁會先給它閱讀空氣，而不是叫你立刻把 badge 清掉。
          </>
        }
        note={
          <div className="space-y-4">
            <EditorialPaperCard
              eyebrow="Reading Rule"
              title="先理解，再回應；先慢下來，再靠近。"
              description="伴侶來信被放進閱讀室，而不是通知中心。首頁會把它變成一種閱讀經驗，而不是待處理事項。"
              tone="paper"
              className="rounded-[2rem]"
            >
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">Reading Room</Badge>
                <Badge variant="success">{partnerJournals.length} 則來信</Badge>
                {partnerSafetyBanner ? <Badge variant="warning">安全提示已啟用</Badge> : null}
              </div>
            </EditorialPaperCard>

            {partnerSafetyBanner ? (
              <PartnerSafetyBanner
                severeCount={partnerSafetyBanner.severeCount}
                onDismiss={onDismissSafetyBanner}
                className="rounded-[2rem] border-destructive/15 bg-[linear-gradient(180deg,rgba(255,246,246,0.96),rgba(255,250,249,0.92))]"
              />
            ) : (
              <EditorialPaperCard
                eyebrow="Editorial Note"
                title="今天沒有安全提醒，閱讀節奏可以更安穩。"
                description="當 partner tab 沒有高風險信號時，首頁只保留最安靜的閱讀提示，不再額外加壓。"
                tone="mist"
                className="rounded-[2rem]"
              >
                <div className="flex items-center gap-2 text-sm text-card-foreground">
                  <HeartHandshake className="h-4 w-4 text-primary" aria-hidden />
                  <span>把它讀成稿頁，而不是待處理的訊息。</span>
                </div>
              </EditorialPaperCard>
            )}
          </div>
        }
      />

      <EditorialTimelineColumn
        eyebrow="Letter Shelf"
        title="伴侶來信"
        description="每一篇內容都像展開的稿頁，被放進更安靜的閱讀節奏裡。"
        aside={
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-white/82 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
            aria-label="重新整理伴侶來信"
          >
            <RefreshCw className="h-4 w-4" aria-hidden />
            更新來信
          </button>
        }
        className="bg-[linear-gradient(180deg,rgba(255,254,251,0.96),rgba(249,245,239,0.9))]"
      >
        {timelineStage === 'loading' ? (
          <div className="space-y-8 pl-12">
            {[1, 2].map((item) => (
              <EditorialPaperCard key={item} tone="paper" className="rounded-[2rem]">
                <div className="space-y-4">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-1/2" />
                  <Skeleton className="h-36 w-full rounded-[1.6rem]" />
                </div>
              </EditorialPaperCard>
            ))}
          </div>
        ) : timelineStage === 'deferred' ? (
          <div className="pl-12">
            <EditorialDeferredState
              icon={HeartHandshake}
              title="伴侶來信還在路上"
              description="這通常是 upstream 回應偏慢。首頁其他部分不受影響，你可以先回到自己的頁面，稍後再回來讀。"
              actionLabel="重新整理"
              onAction={onRefresh}
            />
          </div>
        ) : partnerJournals.length === 0 ? (
          <div className="pl-12">
            <EditorialEmptyState
              icon={BookHeart}
              title="今天還沒有新的來信。"
              description="當伴侶寫下日記，這裡會出現經過隱私保護與溫柔整理後的內容。首頁會先替它留下安靜的空位。"
            />
          </div>
        ) : (
          partnerJournals.map((journal, idx) => {
            const letterDate = formatLetterDate(journal.created_at);

            return (
              <div key={journal.id} className="relative grid gap-4 pl-12 xl:grid-cols-[148px_minmax(0,1fr)] xl:gap-9 xl:pl-0">
                <span
                  className="absolute left-[18px] top-8 h-3 w-3 rounded-full border border-primary/25 bg-white shadow-soft xl:left-[214px]"
                  aria-hidden
                />
                <TimelineDateRail
                  eyebrow={`Letter ${String(idx + 1).padStart(2, '0')}`}
                  title={letterDate.label}
                  meta={letterDate.meta}
                />
                <div className={idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : ''}>
                  <PartnerJournalCard journal={journal} variant="reading-room" />
                </div>
              </div>
            );
          })
        )}
      </EditorialTimelineColumn>
    </div>
  );
}
