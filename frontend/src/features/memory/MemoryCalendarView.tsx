'use client';

import { CalendarDay } from '@/services/memoryService';
import { GlassCard } from '@/components/haven/GlassCard';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

/** Mood dot colors: semantic chart tokens (ART-DIRECTION). */
const MOOD_COLOR_CLASS: Record<string, string> = {
  emerald: 'bg-chart-2',
  sky: 'bg-chart-3',
  amber: 'bg-chart-4',
  yellow: 'bg-chart-5',
  slate: 'bg-chart-1',
  orange: 'bg-chart-4',
  violet: 'bg-chart-1',
};

function DayCell({
  day,
  isCurrentMonth,
  isToday,
}: {
  day: { date: string; mood_color?: string | null; journal_count: number; card_count: number };
  isCurrentMonth: boolean;
  isToday: boolean;
}) {
  const d = new Date(day.date);
  const dateNum = d.getDate();
  const moodClass = day.mood_color ? MOOD_COLOR_CLASS[day.mood_color] ?? 'bg-muted' : undefined;
  const hasContent = day.journal_count > 0 || day.card_count > 0;
  return (
    <div
      className={`
        min-h-[44px] flex flex-col items-center justify-center rounded-button text-caption transition-colors duration-haven-fast ease-haven
        ${isCurrentMonth ? 'text-card-foreground' : 'text-muted-foreground/60'}
        ${isToday ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}
        ${hasContent ? 'bg-muted/50 hover:bg-primary/8 hover:scale-[1.05] cursor-pointer transition-transform' : ''}
      `}
    >
      <span className="tabular-nums">{dateNum}</span>
      {hasContent && (
        <span
          className={`w-2.5 h-2.5 rounded-full mt-0.5 transition-transform ${moodClass ?? 'bg-primary/60'}`}
          title={`日記 ${day.journal_count}、卡片 ${day.card_count}`}
          aria-hidden
        />
      )}
    </div>
  );
}

export default function MemoryCalendarView({
  calendar,
  year,
  month,
  loading,
  onPrevMonth,
  onNextMonth,
}: {
  calendar: { year: number; month: number; days: CalendarDay[] } | null;
  year: number;
  month: number;
  loading: boolean;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}) {
  const monthStart = new Date(year, month - 1, 1);
  const monthEnd = new Date(year, month, 0);
  const startPad = monthStart.getDay();
  const daysInMonth = monthEnd.getDate();
  const daysByDate = (calendar?.days ?? []).reduce(
    (acc, d) => {
      acc[d.date] = d;
      return acc;
    },
    {} as Record<string, CalendarDay>
  );

  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  const cells: Array<{ date: string; day: CalendarDay | null; isCurrentMonth: boolean }> = [];
  for (let i = 0; i < startPad; i++) {
    const d = new Date(year, month - 1, -startPad + i + 1);
    cells.push({
      date: d.toISOString().slice(0, 10),
      day: daysByDate[d.toISOString().slice(0, 10)] ?? null,
      isCurrentMonth: false,
    });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({
      date: dateStr,
      day: daysByDate[dateStr] ?? {
        date: dateStr,
        mood_color: null,
        journal_count: 0,
        card_count: 0,
        has_photo: false,
      },
      isCurrentMonth: true,
    });
  }
  const today = new Date().toISOString().slice(0, 10);

  if (loading) {
    return (
      <GlassCard variant="glass" className="p-4" aria-busy="true" aria-live="polite">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-9 w-9 rounded-button" aria-hidden />
          <Skeleton className="h-6 w-24 rounded-card" aria-hidden />
          <Skeleton className="h-9 w-9 rounded-button" aria-hidden />
        </div>
        <div className="grid grid-cols-7 gap-1 mb-2">
          {[...Array(7)].map((_, i) => (
            <Skeleton key={i} className="h-4 w-full rounded-card" aria-hidden />
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {[...Array(35)].map((_, i) => (
            <Skeleton key={i} className="min-h-[44px] w-full rounded-button" aria-hidden />
          ))}
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard variant="glass" className="p-4">
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          onClick={onPrevMonth}
          className="p-2 rounded-button hover:bg-primary/8 hover:text-primary text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven-fast ease-haven active:scale-95"
          aria-label="上個月"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="text-title text-card-foreground font-art font-semibold tracking-tight tabular-nums">
          {year} 年 {month} 月
        </span>
        <button
          type="button"
          onClick={onNextMonth}
          className="p-2 rounded-button hover:bg-primary/8 hover:text-primary text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-haven-fast ease-haven active:scale-95"
          aria-label="下個月"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 mb-2">
        {weekdays.map((w) => (
          <div key={w} className="text-center text-caption text-muted-foreground font-medium">
            {w}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((c) => (
          <DayCell
            key={c.date}
            day={c.day ?? { date: c.date, mood_color: null, journal_count: 0, card_count: 0, appreciation_count: 0, has_photo: false }}
            isCurrentMonth={c.isCurrentMonth}
            isToday={c.date === today}
          />
        ))}
      </div>
      <div className="section-divider mt-4" />
      <p className="text-caption text-muted-foreground mt-3 text-center px-2">
        點選有顏點的日期表示當天有日記或卡片回憶
      </p>
    </GlassCard>
  );
}
