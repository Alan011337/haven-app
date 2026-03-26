'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  memoryService,
  TimelineItem,
} from '@/services/memoryService';
import { capturePosthogEvent } from '@/lib/posthog';

const TIMELINE_PAGE_SIZE = 30;
/** First-page limit for faster initial paint. */
const TIMELINE_INITIAL_LIMIT = 20;
const STALE_TIME_TIME_CAPSULE_AND_REPORT_MS = 5 * 60 * 1000;
const STALE_TIME_TIMELINE_AND_CALENDAR_MS = 60_000;
const LOAD_MORE_MIN_INTERVAL_MS = 350;

function getTimelineItemKey(item: TimelineItem): string {
  if (item.type === 'journal') {
    return `journal:${item.id}`;
  }
  if (item.type === 'card') {
    return `card:${item.session_id}`;
  }
  if (item.type === 'appreciation') {
    return `appreciation:${item.id}`;
  }
  return `photo:${item.id}`;
}

/** Browser timezone offset (minutes UTC is ahead of local). Stable for session lifetime. */
const TZ_OFFSET_MINUTES = new Date().getTimezoneOffset();

export function useMemoryData() {
  const [view, setView] = useState<'feed' | 'calendar'>('feed');
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const d = new Date();
    return { year: d.getFullYear(), month: d.getMonth() + 1 };
  });
  /** Cursor for next page: opaque string from API; null = first page. */
  const [timelineCursor, setTimelineCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [accumulatedItems, setAccumulatedItems] = useState<TimelineItem[]>([]);
  const loadMoreLockedRef = useRef(false);
  const lastLoadMoreAtRef = useRef(0);

  const timelineQuery = useQuery({
    queryKey: ['memory', 'timeline', timelineCursor],
    queryFn: () =>
      memoryService.getTimeline({
        limit: timelineCursor === null ? TIMELINE_INITIAL_LIMIT : TIMELINE_PAGE_SIZE,
        cursor: timelineCursor ?? undefined,
      }),
    enabled: view === 'feed',
    staleTime: STALE_TIME_TIMELINE_AND_CALENDAR_MS,
  });

  useEffect(() => {
    if (view !== 'feed') {
      return;
    }
    capturePosthogEvent('timeline_viewed', {
      pagination_mode: 'cursor',
    });
  }, [view]);

  useEffect(() => {
    const data = timelineQuery.data;
    if (!data) return;
    capturePosthogEvent('timeline_page_loaded', {
      pagination_mode: 'cursor',
      items_count: data.items.length,
      has_more: data.has_more,
    });
    const id = requestAnimationFrame(() => {
      if (timelineCursor === null) {
        setAccumulatedItems(data.items);
      } else {
        setAccumulatedItems((prev) => {
          if (!data.items.length) {
            return prev;
          }
          const seen = new Set(prev.map((item) => getTimelineItemKey(item)));
          const merged = [...prev];
          for (const item of data.items) {
            const key = getTimelineItemKey(item);
            if (seen.has(key)) {
              continue;
            }
            seen.add(key);
            merged.push(item);
          }
          return merged;
        });
      }
      // store next_cursor for subsequent pagination
      setNextCursor(data.next_cursor ?? null);
      loadMoreLockedRef.current = false;
    });
    return () => cancelAnimationFrame(id);
  }, [timelineQuery.data, timelineCursor]);

  useEffect(() => {
    if (!timelineQuery.isFetching) {
      loadMoreLockedRef.current = false;
    }
  }, [timelineQuery.isFetching]);

  const calendarQuery = useQuery({
    queryKey: ['memory', 'calendar', calendarMonth.year, calendarMonth.month, TZ_OFFSET_MINUTES],
    queryFn: () => memoryService.getCalendar(calendarMonth.year, calendarMonth.month, TZ_OFFSET_MINUTES),
    enabled: view === 'calendar',
    staleTime: STALE_TIME_TIMELINE_AND_CALENDAR_MS,
  });

  const timeCapsuleQuery = useQuery({
    queryKey: ['memory', 'time-capsule'],
    queryFn: () => memoryService.getTimeCapsule(),
    staleTime: STALE_TIME_TIME_CAPSULE_AND_REPORT_MS,
  });

  const reportQuery = useQuery({
    queryKey: ['memory', 'report', 'month'],
    queryFn: () => memoryService.getReport('month'),
    staleTime: STALE_TIME_TIME_CAPSULE_AND_REPORT_MS,
  });

  const items = accumulatedItems;
  const hasMore = timelineQuery.data?.has_more ?? false;
  const loadMore = useCallback(() => {
    if (!nextCursor) return;
    if (timelineQuery.isFetching) return;
    const now = Date.now();
    if (loadMoreLockedRef.current) return;
    if (now - lastLoadMoreAtRef.current < LOAD_MORE_MIN_INTERVAL_MS) return;
    if (nextCursor === timelineCursor) return;
    loadMoreLockedRef.current = true;
    lastLoadMoreAtRef.current = now;
    setTimelineCursor(nextCursor);
  }, [nextCursor, timelineCursor, timelineQuery.isFetching]);

  const prevMonth = useCallback(() => {
    setCalendarMonth((m) => {
      if (m.month <= 1) return { year: m.year - 1, month: 12 };
      return { year: m.year, month: m.month - 1 };
    });
  }, []);
  const nextMonth = useCallback(() => {
    setCalendarMonth((m) => {
      if (m.month >= 12) return { year: m.year + 1, month: 1 };
      return { year: m.year, month: m.month + 1 };
    });
  }, []);

  return {
    view,
    setView,
    // Feed
    items,
    hasMore,
    loadMore,
    timelineLoading: timelineQuery.isLoading,
    timelineFetching: timelineQuery.isFetching,
    timelineError: timelineQuery.isError,
    refetchTimeline: timelineQuery.refetch,
    // Calendar
    calendar: calendarQuery.data ?? null,
    calendarMonth,
    prevMonth,
    nextMonth,
    calendarLoading: calendarQuery.isLoading,
    calendarError: calendarQuery.isError,
    refetchCalendar: calendarQuery.refetch,
    // Time Capsule
    timeCapsule: timeCapsuleQuery.data ?? null,
    timeCapsuleLoading: timeCapsuleQuery.isLoading,
    timeCapsuleError: timeCapsuleQuery.isError,
    refetchTimeCapsule: timeCapsuleQuery.refetch,
    // Report
    report: reportQuery.data ?? null,
    reportLoading: reportQuery.isLoading,
    reportError: reportQuery.isError,
    refetchReport: reportQuery.refetch,
  };
}
