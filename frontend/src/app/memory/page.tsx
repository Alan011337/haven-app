'use client';

import dynamic from 'next/dynamic';
import { Suspense } from 'react';
import Link from 'next/link';
import { ArrowLeft, LayoutGrid, List, Gift, BarChart2 } from 'lucide-react';
import { useMemoryData } from '@/features/memory/useMemoryData';
import { GlassCard } from '@/components/haven/GlassCard';
import Skeleton from '@/components/ui/Skeleton';
import MemoryLoading from './loading';

const MemoryFeedView = dynamic(
  () => import('@/features/memory/MemoryFeedView').then((m) => m.default),
  { ssr: false, loading: () => <Skeleton className="h-[40vh] w-full rounded-card" aria-hidden /> },
);

const MemoryCalendarView = dynamic(
  () => import('@/features/memory/MemoryCalendarView').then((m) => m.default),
  { ssr: false, loading: () => <Skeleton className="h-[40vh] w-full rounded-card" aria-hidden /> },
);

function MemoryPageContent() {
  const {
    view,
    setView,
    items,
    hasMore,
    loadMore,
    timelineLoading,
    timelineFetching,
    timelineError,
    refetchTimeline,
    calendar,
    calendarMonth,
    prevMonth,
    nextMonth,
    calendarLoading,
    calendarError,
    refetchCalendar,
    timeCapsule,
    timeCapsuleLoading,
    report,
    reportLoading,
    reportError,
    refetchReport,
  } = useMemoryData();

  return (
    <div className="min-h-screen bg-muted/40 pb-24">
      <header className="sticky top-0 z-10 bg-card/80 backdrop-blur-2xl border-b border-border/60 px-4 py-4 flex items-center gap-3 shadow-soft relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
        <Link
          href="/"
          aria-label="返回首頁"
          className="p-2 -ml-2 hover:bg-muted/60 rounded-full transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <ArrowLeft className="w-5 h-5 text-muted-foreground" />
        </Link>
        <h1 className="flex-1 text-title font-art font-bold text-card-foreground tracking-tight">回憶長廊</h1>
        <div className="flex rounded-full overflow-hidden border border-border/60 bg-muted/30 p-0.5">
          <button
            type="button"
            onClick={() => setView('feed')}
            className={`p-2 rounded-full transition-all duration-haven ease-haven active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${view === 'feed' ? 'bg-primary text-primary-foreground shadow-soft glow-ring-primary' : 'text-muted-foreground hover:text-card-foreground'}`}
            aria-label="動態牆"
            aria-pressed={view === 'feed'}
          >
            <List className="w-4.5 h-4.5" />
          </button>
          <button
            type="button"
            onClick={() => setView('calendar')}
            className={`p-2 rounded-full transition-all duration-haven ease-haven active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${view === 'calendar' ? 'bg-primary text-primary-foreground shadow-soft glow-ring-primary' : 'text-muted-foreground hover:text-card-foreground'}`}
            aria-label="日曆"
            aria-pressed={view === 'calendar'}
          >
            <LayoutGrid className="w-4.5 h-4.5" />
          </button>
        </div>
      </header>

      <main className="p-4 max-w-2xl mx-auto flex flex-col gap-[var(--space-section)]">
        {/* Time Capsule */}
        <section aria-labelledby="time-capsule-heading" className="animate-slide-up-fade">
          <h2 id="time-capsule-heading" className="text-body font-art font-semibold text-card-foreground mb-3 flex items-center gap-2.5">
            <span className="icon-badge" aria-hidden><Gift className="w-4 h-4" /></span>
            時光膠囊
          </h2>
          {timeCapsuleLoading ? (
            <Skeleton className="h-24 w-full rounded-card" aria-hidden />
          ) : timeCapsule?.available && timeCapsule.memory ? (
            <GlassCard variant="glass" className="p-6">
              <p className="text-caption text-muted-foreground tabular-nums">{timeCapsule.memory.date}</p>
              <p className="text-body text-card-foreground mt-1">{timeCapsule.memory.summary_text}</p>
            </GlassCard>
          ) : (
            <GlassCard variant="glass" className="p-6">
              <p className="text-body text-muted-foreground">一年前的今天尚無紀錄，寫下日記與抽卡後，明年此時會收到回憶推播。</p>
            </GlassCard>
          )}
        </section>

        {/* AI Report */}
        <section aria-labelledby="report-heading" className="animate-slide-up-fade-1">
          <h2 id="report-heading" className="text-body font-art font-semibold text-card-foreground mb-3 flex items-center gap-2.5">
            <span className="icon-badge" aria-hidden><BarChart2 className="w-4 h-4" /></span>
            關係週報／月報
          </h2>
          {reportError ? (
            <GlassCard variant="glass" className="p-6">
              <p className="text-body text-muted-foreground">無法載入週報</p>
              <button
                type="button"
                onClick={() => refetchReport()}
                className="mt-3 rounded-button bg-gradient-to-b from-primary to-primary/90 px-4 py-2 text-caption text-primary-foreground font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven ease-haven active:scale-95"
                aria-label="重試載入週報"
              >
                重試
              </button>
            </GlassCard>
          ) : reportLoading ? (
            <Skeleton className="h-28 w-full rounded-card" aria-hidden />
          ) : report ? (
            <GlassCard variant="glass" className="p-6">
              <p className="text-caption text-muted-foreground tabular-nums">
                {report.from_date}～{report.to_date}（{report.period === 'month' ? '月' : '週'}報）
              </p>
              {report.emotion_trend_summary && (
                <p className="text-body text-card-foreground mt-2">情緒趨勢：{report.emotion_trend_summary}</p>
              )}
              {report.health_suggestion && (
                <p className="text-body text-card-foreground mt-2 border-t border-border pt-2">
                  {report.health_suggestion}
                </p>
              )}
              {!report.emotion_trend_summary && !report.health_suggestion && (
                <p className="text-body text-muted-foreground mt-2">尚無足夠資料，持續寫日記後會產出建議。</p>
              )}
            </GlassCard>
          ) : (
            <GlassCard variant="glass" className="p-6">
              <p className="text-body text-muted-foreground">尚無週報／月報資料</p>
              <p className="text-caption text-muted-foreground mt-2">持續寫日記後會產出建議。</p>
            </GlassCard>
          )}
        </section>

        {/* Dual View: Feed | Calendar */}
        <section aria-labelledby="archive-heading" className="animate-slide-up-fade-2">
          <h2 id="archive-heading" className="text-body font-art font-semibold text-card-foreground mb-3 flex items-center gap-2.5">
            <span className="icon-badge" aria-hidden>{view === 'feed' ? <List className="w-4 h-4" /> : <LayoutGrid className="w-4 h-4" />}</span>
            {view === 'feed' ? '動態牆' : '日曆'}
          </h2>
          {view === 'feed' && timelineError ? (
            <GlassCard variant="glass" className="p-6">
              <p className="text-body text-muted-foreground">無法載入動態牆</p>
              <button
                type="button"
                onClick={() => refetchTimeline()}
                className="mt-3 rounded-button bg-gradient-to-b from-primary to-primary/90 px-4 py-2 text-caption text-primary-foreground font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven ease-haven active:scale-95"
                aria-label="重試載入動態牆"
              >
                重試
              </button>
            </GlassCard>
          ) : view === 'calendar' && calendarError ? (
            <GlassCard variant="glass" className="p-6">
              <p className="text-body text-muted-foreground">無法載入日曆</p>
              <button
                type="button"
                onClick={() => refetchCalendar()}
                className="mt-3 rounded-button bg-gradient-to-b from-primary to-primary/90 px-4 py-2 text-caption text-primary-foreground font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven ease-haven active:scale-95"
                aria-label="重試載入日曆"
              >
                重試
              </button>
            </GlassCard>
          ) : view === 'feed' ? (
            <MemoryFeedView
              items={items}
              loading={timelineLoading}
              loadingMore={timelineFetching}
              hasMore={hasMore}
              onLoadMore={loadMore}
            />
          ) : (
            <MemoryCalendarView
              calendar={calendar}
              year={calendarMonth.year}
              month={calendarMonth.month}
              loading={calendarLoading}
              onPrevMonth={prevMonth}
              onNextMonth={nextMonth}
            />
          )}
        </section>
      </main>
    </div>
  );
}

export default function MemoryPage() {
  return (
    <Suspense fallback={<MemoryLoading />}>
      <MemoryPageContent />
    </Suspense>
  );
}
