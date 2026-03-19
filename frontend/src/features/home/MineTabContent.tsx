'use client';

import { useEffect, useMemo, useState } from 'react';
import { Feather, RefreshCw, Sparkles } from 'lucide-react';
import JournalCard from '@/components/features/JournalCard';
import JournalInput from '@/components/features/JournalInput';
import DailySyncCard from '@/components/features/DailySyncCard';
import DateSuggestionCard from '@/components/features/DateSuggestionCard';
import MediationEntryBanner from '@/components/features/MediationEntryBanner';
import AppreciationCard from '@/components/features/AppreciationCard';
import LoveLanguageWeeklyCard from '@/components/features/LoveLanguageWeeklyCard';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import {
  EditorialDeferredState,
  EditorialEmptyState,
  EditorialPaperCard,
  EditorialTimelineColumn,
  HomeCoverStage,
  HomeMosaicRail,
  HomeSectionFrame,
  TimelineDateRail,
} from '@/features/home/HomePrimitives';
import { resolveHomeTimelineStage } from '@/lib/home-timeline-state';
import { cn } from '@/lib/utils';
import { Journal } from '@/types';

interface MineTabContentProps {
  myJournals: Journal[];
  loading: boolean;
  timelineUnavailable: boolean;
  relationshipPulse: {
    score: number;
    streakDays: number;
    hasNewPartnerContent: boolean;
  };
  onJournalCreated: () => void;
  onJournalDeleted?: () => void;
  onRetryTimeline: () => void;
}

function formatTimelineDate(value: string) {
  const date = new Date(value);
  return {
    label: date.toLocaleDateString('zh-TW', {
      month: 'long',
      day: 'numeric',
    }),
    meta: date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      weekday: 'long',
    }),
  };
}

export default function MineTabContent({
  myJournals,
  loading,
  timelineUnavailable,
  relationshipPulse,
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

  const pulseLine = useMemo(() => {
    const score = relationshipPulse.score;
    if (relationshipPulse.hasNewPartnerContent) {
      return <>關係脈搏 {score} 分。伴侶有新內容，寫完再看。</>;
    }
    if (myJournals.length === 0) {
      return <>關係脈搏 {score} 分。今天還沒寫，開始第一篇吧。</>;
    }
    return <>關係脈搏 {score} 分。先寫自己，再靠近彼此。</>;
  }, [myJournals.length, relationshipPulse.hasNewPartnerContent, relationshipPulse.score]);

  return (
    <div className="flex flex-col gap-[var(--space-section)]">
      <HomeCoverStage
        eyebrow="私人手記"
        title="今天這一頁，先只留給你自己。"
        description="先把今天的心情寫下來，其他的慢慢展開。"
        pulse={pulseLine}
      >
        <JournalInput
          onJournalCreated={onJournalCreated}
          variant="cover"
          className="border-white/55 bg-transparent shadow-none"
        />
      </HomeCoverStage>

      <HomeSectionFrame
        eyebrow="陪伴小卡"
        title="寫完了，其他內容慢慢展開。"
      >
        <HomeMosaicRail className="md:grid-cols-[1.18fr_0.82fr]">
          <div className="md:col-span-2 transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift">
            <MediationEntryBanner className="h-full border-white/45 bg-[linear-gradient(135deg,rgba(255,251,247,0.94),rgba(247,243,236,0.88))]" />
          </div>
          <div className="md:row-span-2 transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift">
            <DailySyncCard className="h-full border-[rgba(212,185,130,0.35)] bg-[linear-gradient(180deg,rgba(255,249,235,0.98),rgba(252,243,220,0.94))]" />
          </div>
          <DateSuggestionCard className="transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift border-[rgba(150,185,150,0.30)] bg-[linear-gradient(180deg,rgba(240,250,240,0.94),rgba(228,244,228,0.88))]" />
          <AppreciationCard className="transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift border-[rgba(200,170,195,0.32)] bg-[linear-gradient(180deg,rgba(252,245,250,0.95),rgba(247,238,248,0.90))]" />
          <div className="md:col-span-2 transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift">
            <LoveLanguageWeeklyCard className="h-full border-[rgba(170,195,220,0.30)] bg-[linear-gradient(180deg,rgba(243,248,255,0.94),rgba(234,243,255,0.88))]" />
          </div>
        </HomeMosaicRail>
      </HomeSectionFrame>

      <EditorialTimelineColumn
        eyebrow="回憶廊道"
        title="寫下的東西，在這裡慢慢長出重量。"
        aside={<Badge variant="metadata" size="md" className="bg-white/72 text-primary/72">{myJournals.length} 篇日記</Badge>}
        className="bg-[linear-gradient(180deg,rgba(255,254,251,0.96),rgba(249,245,239,0.9))]"
      >
        {timelineStage === 'loading' ? (
          <div className="space-y-8 pl-12">
            {[1, 2, 3].map((i) => (
              <EditorialPaperCard key={i} tone="paper" className="rounded-[2rem]">
                <div className="space-y-4">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-1/2" />
                  <Skeleton className="h-32 w-full rounded-[1.6rem]" />
                </div>
              </EditorialPaperCard>
            ))}
          </div>
        ) : timelineStage === 'deferred' ? (
          <div className="pl-12">
            <EditorialDeferredState
              icon={Sparkles}
              title="時光迴廊還在安靜同步"
              description="舊日記正在同步，先寫今天的吧。"
              actionLabel="重新同步日記"
              onAction={onRetryTimeline}
            />
          </div>
        ) : myJournals.length === 0 ? (
          <div className="pl-12">
            <EditorialEmptyState
              icon={Feather}
              title="第一篇日記，會從這裡開始發光。"
              description="寫下第一篇，這裡就會亮起來。"
            />
          </div>
        ) : (
          myJournals.map((journal, idx) => {
            const timelineDate = formatTimelineDate(journal.created_at);

            return (
              <div
                key={journal.id}
                className={cn(
                  'relative grid gap-4 pl-12 xl:grid-cols-[148px_minmax(0,1fr)] xl:gap-9 xl:pl-0',
                  idx === 0 && 'xl:gap-10'
                )}
              >
                <span
                  className={cn(
                    'absolute left-[18px] top-8 h-3 w-3 rounded-full border border-primary/25 shadow-soft xl:left-[214px]',
                    idx === 0 ? 'bg-primary/25 timeline-dot-active' : 'bg-white'
                  )}
                  aria-hidden
                />
                <TimelineDateRail
                  eyebrow={`第 ${String(idx + 1).padStart(2, '0')} 篇`}
                  title={timelineDate.label}
                  meta={timelineDate.meta}
                  lead={idx === 0}
                />
                <div className={cn(idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : '', idx === 0 && 'xl:-mt-1')}>
                  {idx === 0 ? (
                    <p className="mb-3 type-micro uppercase text-primary/75">
                      最新一篇
                    </p>
                  ) : null}
                  <JournalCard journal={journal} onDelete={onJournalDeleted} variant="timeline" />
                </div>
              </div>
            );
          })
        )}

        {timelineStage !== 'loading' && myJournals.length > 0 ? (
          <div className="flex justify-end pl-12">
            <button
              type="button"
              onClick={onRetryTimeline}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-white/82 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              更新這條時間線
            </button>
          </div>
        ) : null}
      </EditorialTimelineColumn>
    </div>
  );
}
