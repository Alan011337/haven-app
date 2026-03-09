/**
 * P2-C Memory Lane: timeline, calendar, time capsule, relationship report.
 */

import api from '@/lib/api';
import { logClientError } from '@/lib/safe-error-log';

export interface TimelineJournalItem {
  type: 'journal';
  id: string;
  created_at: string;
  user_id: string;
  mood_label?: string | null;
  content_preview?: string | null;
  is_own: boolean;
}

export interface TimelineCardItem {
  type: 'card';
  session_id: string;
  revealed_at: string;
  card_title: string;
  card_question: string;
  category: string;
  my_answer?: string | null;
  partner_answer?: string | null;
  is_own: boolean;
}

export interface TimelinePhotoItem {
  type: 'photo';
  id: string;
  created_at: string;
  user_id: string;
  caption?: string | null;
  is_own: boolean;
}

export type TimelineItem = TimelineJournalItem | TimelineCardItem | TimelinePhotoItem;

export interface TimelineResponse {
  items: TimelineItem[];
  has_more: boolean;
  next_cursor?: string | null;
}

export interface CalendarDay {
  date: string;
  mood_color?: string | null;
  journal_count: number;
  card_count: number;
  has_photo: boolean;
}

export interface CalendarResponse {
  year: number;
  month: number;
  days: CalendarDay[];
}

export interface TimeCapsuleMemory {
  date: string;
  journals_count: number;
  cards_count: number;
  summary_text?: string | null;
  items: Array<{ type: string; id?: string; created_at?: string }>;
}

export interface TimeCapsuleResponse {
  available: boolean;
  memory?: TimeCapsuleMemory | null;
}

export interface RelationshipReportResponse {
  period: 'week' | 'month';
  from_date: string;
  to_date: string;
  emotion_trend_summary?: string | null;
  top_topics: string[];
  health_suggestion?: string | null;
  generated_at: string;
}

export const memoryService = {
  getTimeline: async (params?: {
    limit?: number;
    before?: string;
    cursor?: string;
    from_date?: string;
    to_date?: string;
  }): Promise<TimelineResponse> => {
    try {
      const res = await api.get<TimelineResponse>('/memory/timeline', { params });
      return res.data;
    } catch (e) {
      logClientError('memory-timeline-failed', e);
      throw e;
    }
  },

  getCalendar: async (year: number, month: number): Promise<CalendarResponse> => {
    try {
      const res = await api.get<CalendarResponse>('/memory/calendar', {
        params: { year, month },
      });
      return res.data;
    } catch (e) {
      logClientError('memory-calendar-failed', e);
      throw e;
    }
  },

  getTimeCapsule: async (): Promise<TimeCapsuleResponse> => {
    try {
      const res = await api.get<TimeCapsuleResponse>('/memory/time-capsule');
      return res.data;
    } catch (e) {
      logClientError('memory-time-capsule-failed', e);
      throw e;
    }
  },

  getReport: async (period: 'week' | 'month'): Promise<RelationshipReportResponse> => {
    try {
      const res = await api.get<RelationshipReportResponse>('/memory/report', {
        params: { period },
      });
      return res.data;
    } catch (e) {
      logClientError('memory-report-failed', e);
      throw e;
    }
  },
};
