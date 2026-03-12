'use client';

import { useEffect, useMemo, useState } from 'react';
import { Feather, Heart, RefreshCw, Sparkles } from 'lucide-react';
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
    if (relationshipPulse.hasNewPartnerContent) {
      return (
        <>
          伴侶今天也有新的內容，但它會先留在第二層。
          <strong className="font-medium text-card-foreground"> 你先把自己的頁面寫完整，首頁才算真正打開。</strong>
        </>
      );
    }
    if (myJournals.length === 0) {
      return (
        <>
          今天還沒有任何頁面。
          <strong className="font-medium text-card-foreground"> 第一篇寫下去之後，這個首頁的時間感才會真正亮起。</strong>
        </>
      );
    }
    return (
      <>
        先寫自己，再靠近彼此。
        <strong className="font-medium text-card-foreground"> 這一版首頁會刻意把你今天真正想留下的那句話放在最前景。</strong>
      </>
    );
  }, [myJournals.length, relationshipPulse.hasNewPartnerContent]);

  return (
    <div className="flex flex-col gap-[var(--space-section)]">
      <HomeCoverStage
        eyebrow="My Journal"
        title="把今天真正重要的那一句，放到封面最前景。"
        description="這一屏不再要你同時處理所有 flow。它先替你的文字留出最好的一塊稿紙，再把其餘提醒安靜排到後面。"
        pulse={pulseLine}
        note={
          <EditorialPaperCard
            eyebrow="Editorial Note"
            title={`${relationshipPulse.score} 分的關係脈搏，適合先留白一下。`}
            description={`已連續互動 ${relationshipPulse.streakDays} 天。這一版首頁故意先把你自己的頁面撐成前景，再讓彼此靠近。`}
            tone="mist"
            className="rounded-[2rem]"
          >
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">先寫自己</Badge>
              <Badge variant="success">
                {relationshipPulse.hasNewPartnerContent ? '有新來信待閱讀' : '低噪音模式'}
              </Badge>
            </div>
            <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Heart className="h-4 w-4 text-primary" aria-hidden />
              <span>把今天寫成一頁，比把所有提醒都處理完更重要。</span>
            </div>
          </EditorialPaperCard>
        }
      >
        <JournalInput
          onJournalCreated={onJournalCreated}
          variant="cover"
          className="border-white/55 bg-transparent shadow-none"
        />
      </HomeCoverStage>

      <HomeSectionFrame
        eyebrow="Second Layer"
        title="其餘 flow 還在，只是退到了更安靜的位置。"
        description="每日同步、約會提案、感恩便利貼與修復入口仍然存在，但不再搶走你首頁第一屏的注意力。"
        aside={<Badge variant="outline" className="border-primary/25 text-primary/70">Editorial Mosaic</Badge>}
        className="bg-[linear-gradient(180deg,rgba(255,252,248,0.74),rgba(248,244,238,0.64))]"
      >
        <HomeMosaicRail className="md:grid-cols-[1.18fr_0.82fr]">
          <div className="md:col-span-2 transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift">
            <MediationEntryBanner className="h-full border-white/45 bg-[linear-gradient(135deg,rgba(255,251,247,0.94),rgba(247,243,236,0.88))]" />
          </div>
          <div className="md:row-span-2 transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift">
            <DailySyncCard className="h-full border-[rgba(219,204,187,0.38)] bg-[linear-gradient(180deg,rgba(255,254,251,0.98),rgba(251,247,242,0.94))]" />
          </div>
          <DateSuggestionCard className="transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift border-white/45 bg-[linear-gradient(180deg,rgba(248,252,248,0.92),rgba(242,247,242,0.88))]" />
          <AppreciationCard className="transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift border-[rgba(219,204,187,0.38)] bg-[linear-gradient(180deg,rgba(255,254,251,0.98),rgba(251,247,242,0.94))]" />
          <div className="md:col-span-2 transition-all duration-[220ms] ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-1 hover:shadow-lift">
            <LoveLanguageWeeklyCard className="h-full border-white/45 bg-[linear-gradient(180deg,rgba(247,250,248,0.93),rgba(240,246,242,0.88))]" />
          </div>
        </HomeMosaicRail>
      </HomeSectionFrame>

      <EditorialTimelineColumn
        eyebrow="Memory Lane"
        title="時光迴廊"
        description="現在它更像被編排的欄目，而不是一串功能卡。每篇日記都被留出自己的段落、日期與閱讀空氣。"
        aside={<Badge variant="outline" className="border-primary/25 text-primary/70">{myJournals.length} 篇日記</Badge>}
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
              description="首頁主體已可使用。你可以先把今天寫下來，舊日記會在連線恢復後補上，不需要卡在這裡等待。"
              actionLabel="重新同步日記"
              onAction={onRetryTimeline}
            />
          </div>
        ) : myJournals.length === 0 ? (
          <div className="pl-12">
            <EditorialEmptyState
              icon={Feather}
              title="第一篇日記，會從這裡開始發光。"
              description="先寫下今天的一點心緒。當你開始留下內容，首頁就會從空白頁變成你們關係的編輯檯。"
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
                  eyebrow={`Chapter ${String(idx + 1).padStart(2, '0')}`}
                  title={timelineDate.label}
                  meta={timelineDate.meta}
                  lead={idx === 0}
                />
                <div className={cn(idx < 5 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : '', idx === 0 && 'xl:-mt-1')}>
                  {idx === 0 ? (
                    <p className="mb-3 text-[0.68rem] uppercase tracking-[0.28em] text-primary/75">
                      Lead Story
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
