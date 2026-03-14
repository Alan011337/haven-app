'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  BarChart2,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Gift,
  Image as ImageIcon,
  LayoutGrid,
  List,
  MessageCircle,
  Sparkles,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Skeleton from '@/components/ui/Skeleton';
import { useMemoryData } from '@/features/memory/useMemoryData';
import { getGradientForMood } from '@/lib/mood-background';
import type {
  CalendarDay,
  TimelineCardItem,
  TimelineItem,
  TimelineJournalItem,
  TimelinePhotoItem,
} from '@/services/memoryService';
import { memoryService } from '@/services/memoryService';

/* ── Date formatting ── */

function formatDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  if (
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear()
  )
    return '今天';
  const y = new Date(now);
  y.setDate(y.getDate() - 1);
  if (
    d.getDate() === y.getDate() &&
    d.getMonth() === y.getMonth() &&
    d.getFullYear() === y.getFullYear()
  )
    return '昨天';
  return d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateLong(iso: string) {
  return new Date(iso).toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  });
}

/* ── Feed item cards ── */

function JournalCard({ item }: { item: TimelineJournalItem }) {
  const gradient = getGradientForMood(item.mood_label ?? undefined);
  return (
    <div className="rounded-[1.5rem] border border-white/50 bg-white/70 shadow-soft backdrop-blur-sm transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift overflow-hidden">
      <div className={`h-1 w-full bg-gradient-to-r ${gradient} opacity-80`} aria-hidden />
      <div className={`border-l-[3px] px-5 py-4 ${item.is_own ? 'border-l-primary/35' : 'border-l-[rgba(214,181,136,0.45)]'}`}>
        <div className="flex items-start gap-3">
          <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-primary/50" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-xs tabular-nums text-muted-foreground">
              {formatDate(item.created_at)}
              {item.mood_label && <span className="ml-2 text-primary/60">{item.mood_label}</span>}
            </p>
            {item.content_preview && (
              <p className="mt-1.5 text-sm leading-relaxed text-card-foreground line-clamp-3">
                {item.content_preview}
              </p>
            )}
            <p className="mt-2 text-[11px] text-muted-foreground/60">
              {item.is_own ? '我' : '伴侶'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function CardEntry({ item }: { item: TimelineCardItem }) {
  return (
    <div className={`rounded-[1.5rem] border border-white/50 bg-white/70 shadow-soft backdrop-blur-sm transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift overflow-hidden border-l-[3px] px-5 py-4 ${item.is_own ? 'border-l-primary/35' : 'border-l-[rgba(214,181,136,0.45)]'}`}>
      <div className="flex items-start gap-3">
        <MessageCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/50" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-xs tabular-nums text-muted-foreground">{formatDate(item.revealed_at)}</p>
          <p className="mt-1 font-art text-sm font-medium text-card-foreground">{item.card_title}</p>
          {item.my_answer && (
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground line-clamp-2">
              我：{item.my_answer}
            </p>
          )}
          {item.partner_answer && (
            <p className="text-sm leading-relaxed text-muted-foreground line-clamp-2">
              伴侶：{item.partner_answer}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function PhotoCard({ item }: { item: TimelinePhotoItem }) {
  return (
    <div className={`rounded-[1.5rem] border border-white/50 bg-white/70 shadow-soft backdrop-blur-sm transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift overflow-hidden border-l-[3px] px-5 py-4 ${item.is_own ? 'border-l-primary/35' : 'border-l-[rgba(214,181,136,0.45)]'}`}>
      <div className="flex items-start gap-3">
        <ImageIcon className="mt-0.5 h-4 w-4 shrink-0 text-primary/50" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-xs tabular-nums text-muted-foreground">{formatDate(item.created_at)}</p>
          <p className="mt-1 text-sm leading-relaxed text-card-foreground">
            {item.caption?.trim() || '照片回憶'}
          </p>
          <p className="mt-2 text-[11px] text-muted-foreground/60">
            {item.is_own ? '我' : '伴侶'}
          </p>
        </div>
      </div>
    </div>
  );
}

function TimelineCard({ item }: { item: TimelineItem }) {
  if (item.type === 'journal') return <JournalCard item={item} />;
  if (item.type === 'card') return <CardEntry item={item} />;
  if (item.type === 'photo') return <PhotoCard item={item} />;
  return null;
}

function itemKey(item: TimelineItem) {
  if (item.type === 'card') return `c-${item.session_id}`;
  return `${item.type[0]}-${item.id}`;
}

/* ── Calendar ── */

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

const MOOD_DOT: Record<string, string> = {
  emerald: 'bg-chart-2',
  sky: 'bg-chart-3',
  amber: 'bg-chart-4',
  yellow: 'bg-chart-5',
  slate: 'bg-chart-1',
  orange: 'bg-chart-4',
  violet: 'bg-chart-1',
};

function CalendarGrid({
  calendar,
  year,
  month,
  loading,
  selectedDate,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
}: {
  calendar: { year: number; month: number; days: CalendarDay[] } | null;
  year: number;
  month: number;
  loading: boolean;
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}) {
  if (loading) {
    return (
      <div className="rounded-[2rem] border border-white/50 bg-white/70 p-5 shadow-soft md:p-6" aria-busy="true">
        <div className="flex items-center justify-between mb-4">
          <div className="h-9 w-9 animate-pulse rounded-full bg-muted/40" aria-hidden />
          <div className="h-6 w-28 animate-pulse rounded-full bg-muted/40" aria-hidden />
          <div className="h-9 w-9 animate-pulse rounded-full bg-muted/40" aria-hidden />
        </div>
        <div className="grid grid-cols-7 gap-1">
          {Array.from({ length: 35 }).map((_, i) => (
            <div key={i} className="min-h-[44px] animate-pulse rounded-button bg-muted/30" aria-hidden />
          ))}
        </div>
      </div>
    );
  }

  const monthStart = new Date(year, month - 1, 1);
  const monthEnd = new Date(year, month, 0);
  const startPad = monthStart.getDay();
  const daysByDate = (calendar?.days ?? []).reduce((acc, d) => {
    acc[d.date] = d;
    return acc;
  }, {} as Record<string, CalendarDay>);

  const cells: Array<{ date: string; day: CalendarDay | null; isCurrentMonth: boolean }> = [];
  for (let i = 0; i < startPad; i++) {
    const d = new Date(year, month - 1, -startPad + i + 1);
    cells.push({ date: d.toISOString().slice(0, 10), day: null, isCurrentMonth: false });
  }
  for (let d = 1; d <= monthEnd.getDate(); d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({
      date: dateStr,
      day: daysByDate[dateStr] ?? { date: dateStr, mood_color: null, journal_count: 0, card_count: 0, has_photo: false },
      isCurrentMonth: true,
    });
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="rounded-[2rem] border border-white/50 bg-white/70 p-5 shadow-soft md:p-6">
      {/* Month nav */}
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          onClick={onPrevMonth}
          className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/60 bg-white/70 text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          aria-label="上個月"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="font-art text-base font-medium tracking-tight tabular-nums text-card-foreground">
          {year} 年 {month} 月
        </span>
        <button
          type="button"
          onClick={onNextMonth}
          className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/60 bg-white/70 text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          aria-label="下個月"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {WEEKDAYS.map((w) => (
          <div key={w} className="pb-1 text-center text-[11px] font-medium text-muted-foreground">
            {w}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((c) => {
          const hasContent =
            c.day && (c.day.journal_count > 0 || c.day.card_count > 0 || c.day.has_photo);
          const moodClass = c.day?.mood_color ? MOOD_DOT[c.day.mood_color] ?? 'bg-primary/60' : undefined;
          const isToday = c.date === today;
          const isSelected = c.date === selectedDate;
          const dateNum = new Date(c.date).getDate();

          const baseClasses = [
            'min-h-[44px] flex flex-col items-center justify-center rounded-button text-xs transition-all duration-haven ease-haven',
            c.isCurrentMonth ? 'text-card-foreground' : 'text-muted-foreground/50',
            isToday ? 'ring-2 ring-primary/40 ring-offset-2 ring-offset-background' : '',
            isSelected ? 'bg-primary/10 ring-2 ring-primary/30 ring-offset-2 ring-offset-background' : '',
            hasContent && c.isCurrentMonth ? 'bg-primary/5 cursor-pointer hover:bg-primary/10 hover:scale-[1.04]' : '',
          ].join(' ');

          if (hasContent && c.isCurrentMonth) {
            return (
              <button
                key={c.date}
                type="button"
                onClick={() => onSelectDate(c.date)}
                aria-pressed={isSelected}
                aria-label={`${c.date}，日記 ${c.day!.journal_count}，卡片 ${c.day!.card_count}`}
                className={`${baseClasses} text-left focus-ring-premium`}
              >
                <span className="tabular-nums">{dateNum}</span>
                <span
                  className={`mt-0.5 h-2 w-2 rounded-full ${moodClass ?? 'bg-primary/50'}`}
                  aria-hidden
                />
              </button>
            );
          }

          return (
            <div key={c.date} className={baseClasses}>
              <span className="tabular-nums">{dateNum}</span>
            </div>
          );
        })}
      </div>

      {/* Mood dot legend */}
      <p className="mt-3 text-center text-[11px] text-muted-foreground/60">
        彩色圓點代表當天的情緒色彩，點亮的日子可展開
      </p>
    </div>
  );
}

/* ── Constants ── */

const DAY_TIMELINE_LIMIT = 100;
const DAY_STALE_TIME_MS = 60_000;

/* ── Main page content ── */

export default function MemoryPageContent() {
  const [selectedCalendarDate, setSelectedCalendarDate] = useState<string | null>(null);
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

  /* Calendar day spotlight */
  const activeCalendarDates = useMemo(
    () =>
      (calendar?.days ?? [])
        .filter((d) => d.journal_count > 0 || d.card_count > 0 || d.has_photo)
        .map((d) => d.date)
        .sort(),
    [calendar],
  );
  const latestActiveDate = activeCalendarDates.at(-1) ?? null;
  const resolvedDate =
    selectedCalendarDate && activeCalendarDates.includes(selectedCalendarDate)
      ? selectedCalendarDate
      : latestActiveDate;

  const dayQuery = useQuery({
    queryKey: ['memory', 'timeline', 'day-spotlight', resolvedDate],
    queryFn: () =>
      memoryService.getTimeline({
        limit: DAY_TIMELINE_LIMIT,
        from_date: resolvedDate ?? undefined,
        to_date: resolvedDate ?? undefined,
      }),
    enabled: view === 'calendar' && Boolean(resolvedDate),
    staleTime: DAY_STALE_TIME_MS,
  });

  const feedLoadingMore = timelineFetching && !timelineLoading;

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
                <h2 id="time-capsule-heading" className="font-art text-lg font-medium text-card-foreground">
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
                <h2 id="time-capsule-heading" className="font-art text-lg font-medium text-card-foreground/80">
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

      {/* ── Feed view ── */}
      {view === 'feed' && (
        <section className="space-y-3 animate-slide-up-fade-3">
          {timelineError ? (
            <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-10 text-center shadow-soft">
              <p className="text-sm text-muted-foreground">無法載入動態牆</p>
              <div className="mt-4">
                <Button variant="secondary" size="sm" onClick={() => refetchTimeline()}>
                  重試
                </Button>
              </div>
            </div>
          ) : timelineLoading && items.length === 0 ? (
            <div className="space-y-3" aria-busy="true">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-24 w-full rounded-[1.5rem]" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-12 text-center shadow-soft">
              <Sparkles className="mx-auto h-8 w-8 text-primary/40" aria-hidden />
              <p className="mt-4 font-art text-lg text-card-foreground/80">尚無回憶紀錄</p>
              <p className="mt-2 text-sm text-muted-foreground">
                寫日記或一起抽卡後，這裡會出現你們的時光軸。
              </p>
              <div className="mt-6">
                <Link
                  href="/"
                  className="inline-flex items-center justify-center rounded-button border border-border/70 bg-card/82 px-5 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
                >
                  返回首頁
                </Link>
              </div>
            </div>
          ) : (
            <>
              {items.map((item, idx) => (
                <div
                  key={itemKey(item)}
                  className={idx < 6 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : ''}
                >
                  <TimelineCard item={item} />
                </div>
              ))}
              {hasMore && (
                <div className="flex justify-center pt-4">
                  <Button
                    variant="secondary"
                    size="md"
                    loading={feedLoadingMore}
                    onClick={loadMore}
                    aria-label="載入更多回憶"
                  >
                    載入更多
                  </Button>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {/* ── Calendar view ── */}
      {view === 'calendar' && (
        <section className="space-y-6 animate-slide-up-fade-3">
          {calendarError ? (
            <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-10 text-center shadow-soft">
              <p className="text-sm text-muted-foreground">無法載入日曆</p>
              <div className="mt-4">
                <Button variant="secondary" size="sm" onClick={() => refetchCalendar()}>
                  重試
                </Button>
              </div>
            </div>
          ) : (
            <>
              <CalendarGrid
                calendar={calendar}
                year={calendarMonth.year}
                month={calendarMonth.month}
                loading={calendarLoading}
                selectedDate={resolvedDate}
                onSelectDate={setSelectedCalendarDate}
                onPrevMonth={prevMonth}
                onNextMonth={nextMonth}
              />

              {/* Day spotlight */}
              {resolvedDate && (
                <div className="space-y-3">
                  <p className="text-xs font-medium text-muted-foreground">
                    {formatDateLong(resolvedDate)}
                  </p>

                  {dayQuery.isLoading && (
                    <div className="space-y-3" aria-busy="true">
                      <Skeleton className="h-24 w-full rounded-[1.5rem]" />
                      <Skeleton className="h-20 w-full rounded-[1.5rem]" />
                    </div>
                  )}

                  {dayQuery.isError && (
                    <div className="rounded-[1.5rem] border border-white/50 bg-white/70 px-5 py-6 text-center shadow-soft">
                      <p className="text-sm text-muted-foreground">無法載入這一天的回憶</p>
                      <div className="mt-3">
                        <Button variant="secondary" size="sm" onClick={() => dayQuery.refetch()}>
                          重試
                        </Button>
                      </div>
                    </div>
                  )}

                  {!dayQuery.isLoading &&
                    !dayQuery.isError &&
                    (dayQuery.data?.items ?? []).length > 0 &&
                    (dayQuery.data?.items ?? []).map((item) => (
                      <TimelineCard key={itemKey(item)} item={item} />
                    ))}

                  {!dayQuery.isLoading &&
                    !dayQuery.isError &&
                    (dayQuery.data?.items ?? []).length === 0 && (
                      <div className="rounded-[1.5rem] border border-white/50 bg-white/70 px-5 py-6 text-center shadow-soft">
                        <p className="text-sm text-muted-foreground">這天沒有找到更多片段。</p>
                      </div>
                    )}
                </div>
              )}
            </>
          )}
        </section>
      )}

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
