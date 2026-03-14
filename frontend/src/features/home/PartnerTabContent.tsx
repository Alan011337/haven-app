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
    <div className="flex flex-col gap-10 md:gap-14">

      {/* ═══ 1. Context line + safety banner ═══ */}
      <section className="space-y-4">
        <div className="flex items-center gap-3 animate-slide-up-fade">
          <span className="h-2 w-2 shrink-0 rounded-full bg-accent/60 shadow-[0_0_0_6px_rgba(137,154,141,0.08)] animate-breathe" aria-hidden />
          <p className="text-sm text-muted-foreground">
            {partnerJournals.length > 0
              ? `${partnerJournals.length} 封來信，慢慢讀。`
              : '今天還沒有新的來信。'}
          </p>
        </div>

        {partnerSafetyBanner ? (
          <div className="animate-slide-up-fade-1">
            <PartnerSafetyBanner
              severeCount={partnerSafetyBanner.severeCount}
              onDismiss={onDismissSafetyBanner}
              className="rounded-[1.6rem] border-destructive/15 bg-[linear-gradient(180deg,rgba(255,246,246,0.96),rgba(255,250,249,0.92))]"
            />
          </div>
        ) : null}
      </section>

      {/* ═══ 2. Letter timeline ═══ */}
      <EditorialTimelineColumn
        eyebrow="Letter Shelf"
        title="伴侶來信"
        description=""
        aside={<Badge variant="outline" className="border-primary/20 text-primary/65 text-[0.64rem]">{partnerJournals.length} 封</Badge>}
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
              title="來信還在路上"
              description="稍後再回來讀。"
              actionLabel="重新整理"
              onAction={onRefresh}
            />
          </div>
        ) : partnerJournals.length === 0 ? (
          <div className="pl-12">
            <EditorialEmptyState
              icon={BookHeart}
              title="今天還沒有新的來信。"
              description="伴侶寫下日記後，這裡會安靜亮起來。"
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
                  lead={idx === 0}
                />
                <div className={idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : ''}>
                  {idx === 0 ? (
                    <p className="mb-3 text-[0.68rem] uppercase tracking-[0.28em] text-primary/75">
                      Reading Desk
                    </p>
                  ) : null}
                  <PartnerJournalCard journal={journal} variant="reading-room" />
                </div>
              </div>
            );
          })
        )}

        {timelineStage !== 'loading' && partnerJournals.length > 0 ? (
          <div className="flex justify-end pl-12">
            <button
              type="button"
              onClick={onRefresh}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-white/82 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
              aria-label="重新整理伴侶來信"
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              更新來信
            </button>
          </div>
        ) : null}
      </EditorialTimelineColumn>
    </div>
  );
}
