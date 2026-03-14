'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { ArrowLeft, List, LayoutGrid, Gift, BarChart2 } from 'lucide-react';
import Button from '@/components/ui/Button';
import Skeleton from '@/components/ui/Skeleton';
import { useMemoryData } from '@/features/memory/useMemoryData';

/* ── Lazy sub-views ── */

function FeedSkeleton() {
  return (
    <div className="space-y-3" aria-hidden>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="h-24 animate-pulse rounded-[1.5rem] bg-white/50" />
      ))}
    </div>
  );
}

const MemoryFeedView = dynamic(
  () => import('@/features/memory/MemoryFeedView').then((m) => m.default),
  { ssr: false, loading: () => <FeedSkeleton /> },
);

const MemoryCalendarView = dynamic(
  () => import('@/features/memory/MemoryCalendarView').then((m) => m.default),
  { ssr: false, loading: () => <Skeleton className="h-[50vh] w-full rounded-[2rem]" /> },
);

/* ── Page content ── */

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
    <div className="space-y-8 md:space-y-10">
      {/* ── Page identity ── */}
      <div className="space-y-3 animate-slide-up-fade">
        <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
          回憶長廊
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          你們一起走過的每一天。
        </p>
      </div>

      {/* ── Time Capsule — emotional hero ── */}
      <section className="animate-slide-up-fade-1" aria-labelledby="time-capsule-heading">
        {timeCapsuleLoading ? (
          <Skeleton className="h-28 w-full rounded-[2rem]" />
        ) : timeCapsule?.available && timeCapsule.memory ? (
          <div className="rounded-[2rem] border border-primary/12 bg-[linear-gradient(180deg,rgba(255,250,247,0.92),rgba(250,243,234,0.84))] p-6 shadow-soft md:p-8">
            <div className="flex items-start gap-3">
              <Gift className="mt-0.5 h-5 w-5 shrink-0 text-primary/60" aria-hidden />
              <div className="min-w-0 flex-1">
                <h2
                  id="time-capsule-heading"
                  className="font-art text-lg font-medium text-card-foreground"
                >
                  時光膠囊
                </h2>
                <p className="mt-1 text-xs tabular-nums text-muted-foreground">
                  {timeCapsule.memory.date}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-card-foreground">
                  {timeCapsule.memory.summary_text}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-6 shadow-soft md:p-8">
            <div className="flex items-start gap-3">
              <Gift className="mt-0.5 h-5 w-5 shrink-0 text-primary/40" aria-hidden />
              <div>
                <h2
                  id="time-capsule-heading"
                  className="font-art text-lg font-medium text-card-foreground/80"
                >
                  時光膠囊
                </h2>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  一年前的今天尚無紀錄，寫下日記與抽卡後，明年此時會收到回憶推播。
                </p>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ── View toggle ── */}
      <div className="flex items-center gap-2 animate-slide-up-fade-2">
        <button
          type="button"
          onClick={() => setView('feed')}
          className={[
            'inline-flex items-center gap-1.5 rounded-button px-4 py-2 text-xs font-medium transition-all duration-haven ease-haven focus-ring-premium',
            view === 'feed'
              ? 'border border-primary/20 bg-primary/8 text-card-foreground shadow-soft'
              : 'border border-white/50 bg-white/60 text-muted-foreground hover:text-card-foreground hover:bg-white/80',
          ].join(' ')}
          aria-pressed={view === 'feed'}
        >
          <List className="h-3.5 w-3.5" aria-hidden />
          動態牆
        </button>
        <button
          type="button"
          onClick={() => setView('calendar')}
          className={[
            'inline-flex items-center gap-1.5 rounded-button px-4 py-2 text-xs font-medium transition-all duration-haven ease-haven focus-ring-premium',
            view === 'calendar'
              ? 'border border-primary/20 bg-primary/8 text-card-foreground shadow-soft'
              : 'border border-white/50 bg-white/60 text-muted-foreground hover:text-card-foreground hover:bg-white/80',
          ].join(' ')}
          aria-pressed={view === 'calendar'}
        >
          <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
          日曆
        </button>
      </div>

      {/* ── Feed / Calendar ── */}
      <section className="animate-slide-up-fade-3">
        {view === 'feed' && timelineError ? (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-10 text-center shadow-soft">
            <p className="text-sm text-muted-foreground">無法載入動態牆</p>
            <div className="mt-4">
              <Button variant="secondary" size="sm" onClick={() => refetchTimeline()}>
                重試
              </Button>
            </div>
          </div>
        ) : view === 'calendar' && calendarError ? (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-10 text-center shadow-soft">
            <p className="text-sm text-muted-foreground">無法載入日曆</p>
            <div className="mt-4">
              <Button variant="secondary" size="sm" onClick={() => refetchCalendar()}>
                重試
              </Button>
            </div>
          </div>
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

      {/* ── Report — supporting role ── */}
      <section className="animate-slide-up-fade-4" aria-labelledby="report-heading">
        {reportError ? (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-6 shadow-soft md:p-8">
            <div className="flex items-start gap-3">
              <BarChart2 className="mt-0.5 h-5 w-5 shrink-0 text-primary/40" aria-hidden />
              <div>
                <h2 id="report-heading" className="font-art text-lg font-medium text-card-foreground/80">
                  關係週報
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">無法載入週報</p>
                <div className="mt-3">
                  <Button variant="secondary" size="sm" onClick={() => refetchReport()}>
                    重試
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ) : reportLoading ? (
          <Skeleton className="h-28 w-full rounded-[2rem]" />
        ) : report ? (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(248,252,250,0.90),rgba(241,247,244,0.82))] p-6 shadow-soft md:p-8">
            <div className="flex items-start gap-3">
              <BarChart2 className="mt-0.5 h-5 w-5 shrink-0 text-primary/50" aria-hidden />
              <div className="min-w-0 flex-1 space-y-2">
                <h2 id="report-heading" className="font-art text-lg font-medium text-card-foreground">
                  關係{report.period === 'month' ? '月' : '週'}報
                </h2>
                <p className="text-xs tabular-nums text-muted-foreground">
                  {report.from_date} — {report.to_date}
                </p>
                {report.emotion_trend_summary && (
                  <p className="text-sm leading-relaxed text-card-foreground">
                    {report.emotion_trend_summary}
                  </p>
                )}
                {report.health_suggestion && (
                  <p className="border-t border-white/50 pt-2 text-sm leading-relaxed text-muted-foreground">
                    {report.health_suggestion}
                  </p>
                )}
                {!report.emotion_trend_summary && !report.health_suggestion && (
                  <p className="text-sm text-muted-foreground">
                    尚無足夠資料，持續寫日記後會產出建議。
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] p-6 shadow-soft md:p-8">
            <div className="flex items-start gap-3">
              <BarChart2 className="mt-0.5 h-5 w-5 shrink-0 text-primary/40" aria-hidden />
              <div>
                <h2 id="report-heading" className="font-art text-lg font-medium text-card-foreground/80">
                  關係週報
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  持續寫日記後會產出建議。
                </p>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

/* ── Page shell ── */

export default function MemoryPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]"
        aria-hidden
      />
      <div className="relative mx-auto max-w-3xl space-y-8 px-4 py-6 pb-24 sm:px-6 lg:px-8 md:space-y-10">
        <Link
          href="/"
          className="inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/60 bg-white/74 px-4 py-2.5 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          aria-label="返回首頁"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          回首頁
        </Link>

        <MemoryPageContent />
      </div>
    </div>
  );
}
