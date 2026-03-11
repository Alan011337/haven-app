'use client';

import { useEffect, useState } from 'react';
import { Feather, RefreshCw } from 'lucide-react';
import JournalCard from '@/components/features/JournalCard';
import JournalInput from '@/components/features/JournalInput';
import DailySyncCard from '@/components/features/DailySyncCard';
import DateSuggestionCard from '@/components/features/DateSuggestionCard';
import MediationEntryBanner from '@/components/features/MediationEntryBanner';
import AppreciationCard from '@/components/features/AppreciationCard';
import LoveLanguageWeeklyCard from '@/components/features/LoveLanguageWeeklyCard';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import { resolveHomeTimelineStage } from '@/lib/home-timeline-state';
import { Journal } from '@/types';

interface MineTabContentProps {
  myJournals: Journal[];
  loading: boolean;
  timelineUnavailable: boolean;
  secondaryContentReady: boolean;
  onJournalCreated: () => void;
  onJournalDeleted?: () => void;
  onRetryTimeline: () => void;
}

export default function MineTabContent({
  myJournals,
  loading,
  timelineUnavailable,
  secondaryContentReady,
  onJournalCreated,
  onJournalDeleted,
  onRetryTimeline,
}: MineTabContentProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const timelineStage = resolveHomeTimelineStage({
    mounted,
    loading,
    unavailable: timelineUnavailable,
    itemCount: myJournals.length,
  });

  return (
    <div className="flex flex-col gap-[var(--space-section)]">
      <section className="animate-page-enter-delay-1">
        {secondaryContentReady ? (
          <>
            <MediationEntryBanner />
            <DailySyncCard />
            <DateSuggestionCard />
            <AppreciationCard />
            <LoveLanguageWeeklyCard />
          </>
        ) : (
          <GlassCard className="mb-6 p-6 md:p-8">
            <div className="flex items-start gap-4">
              <Skeleton className="h-11 w-11 shrink-0 rounded-2xl" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-full max-w-lg" />
                <Skeleton className="h-24 w-full rounded-card" />
              </div>
            </div>
          </GlassCard>
        )}
        <JournalInput onJournalCreated={onJournalCreated} />
      </section>

      <section className="animate-page-enter-delay-2">
        <div className="flex items-center justify-between mb-[var(--space-section)] px-2">
          <h3 className="font-art text-xl font-bold text-card-foreground flex items-center gap-2">
            <span className="icon-badge"><Feather className="w-4 h-4" aria-hidden /></span>
            時光迴廊
          </h3>
          <Badge variant="default" size="md">
            {myJournals.length} 篇日記
          </Badge>
        </div>

        {timelineStage === 'loading' ? (
          <div className="space-y-[var(--space-block)]">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-40 w-full rounded-card" />
            ))}
          </div>
        ) : timelineStage === 'deferred' ? (
          <GlassCard className="flex flex-col items-start gap-4 py-10 px-6 md:px-8 border border-dashed border-border animate-slide-up-fade">
            <div className="space-y-2">
              <p className="text-card-foreground font-art font-semibold text-lg">時光迴廊還在同步</p>
              <p className="text-muted-foreground text-sm leading-relaxed max-w-xl">
                首頁主體已可使用，你可以先寫日記；舊日記列表會在連線恢復後補上。
              </p>
            </div>
            <button
              type="button"
              onClick={onRetryTimeline}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              重新同步日記
            </button>
          </GlassCard>
        ) : myJournals.length === 0 ? (
          /* P2-A10+: Glass rollout — home empty state; GlassCard variant="solid" to revert. */
          <GlassCard className="flex flex-col items-center justify-center py-20 border border-dashed border-border animate-slide-up-fade">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/12 to-primary/4 border border-primary/8 flex items-center justify-center mb-4">
              <Feather className="w-8 h-8 text-primary" />
            </div>
            <p className="text-card-foreground font-art font-semibold text-lg">這裡還是一片空白</p>
            <p className="text-muted-foreground text-sm mt-1">寫下第一篇日記，種下回憶的種子吧！🌱</p>
          </GlassCard>
        ) : (
          <div className="grid gap-[var(--space-section)]">
            {myJournals.map((journal, idx) => (
              <div key={journal.id} className={idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : ''}>
                <JournalCard journal={journal} onDelete={onJournalDeleted} />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
