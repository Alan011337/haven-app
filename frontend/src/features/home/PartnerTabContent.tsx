'use client';

import Link from 'next/link';
import { BookHeart, HeartHandshake, RefreshCw, Sparkles } from 'lucide-react';
import PartnerJournalCard from '@/components/features/PartnerJournalCard';
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
        eyebrow="伴侶來信"
        title="慢慢讀，不急著回。"
        description="這裡不是通知中心，是閱讀室。"
        pulse={
          <>
            今天共收進 <strong className="font-medium text-card-foreground">{partnerJournals.length} 則來信</strong>。
            不急，慢慢讀。
          </>
        }
        note={
          partnerSafetyBanner ? (
            <PartnerSafetyBanner
              severeCount={partnerSafetyBanner.severeCount}
              onDismiss={onDismissSafetyBanner}
              className="rounded-[2.25rem] border-destructive/15 bg-[linear-gradient(180deg,rgba(255,246,246,0.96),rgba(255,250,249,0.92))]"
            />
          ) : null
        }
      />

      <EditorialTimelineColumn
        eyebrow="來信書架"
        title="每一則來信，都值得有一段安靜的閱讀距離。"
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
              description="伴侶端的回應還在路上，你可以先回到自己的頁面。"
              actionLabel="重新整理"
              onAction={onRefresh}
            />
          </div>
        ) : partnerJournals.length === 0 ? (
          <div className="pl-12 space-y-6">
            <EditorialEmptyState
              icon={BookHeart}
              title="今天還沒有新的來信。"
              description="伴侶寫下日記後，這裡會安靜地亮起來。"
            />
            <div className="rounded-[2rem] border border-white/50 bg-white/68 px-5 py-4 shadow-soft backdrop-blur-xl">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <p className="text-sm leading-7 text-muted-foreground">
                  等待來信的同時，先一起回答今天的卡片吧。
                </p>
                <Link
                  href="/?tab=card"
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full border border-white/58 bg-white/82 px-5 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                >
                  <Sparkles className="h-4 w-4 text-primary" aria-hidden />
                  一起回答今天的卡片
                </Link>
              </div>
            </div>
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
                  eyebrow={`第 ${String(idx + 1).padStart(2, '0')} 封`}
                  title={letterDate.label}
                  meta={letterDate.meta}
                  lead={idx === 0}
                />
                <div className={idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : ''}>
                  {idx === 0 ? (
                    <p className="mb-3 type-micro uppercase text-primary/75">
                      最新來信
                    </p>
                  ) : null}
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
