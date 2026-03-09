import api from '@/lib/api';
import { Journal } from '@/types';

const MAX_JOURNAL_CONTENT_LENGTH = 4000;

export interface PartnerStatus {
  has_partner: boolean;
  latest_journal_at: string | null;
  current_score: number;
  unread_notification_count: number;
}

export interface ActionCardData {
  key: string;
  title: string;
  description: string;
  category: 'comfort' | 'action' | 'connection';
  difficulty_level: number;
}

export interface CreateJournalResponse extends Journal {
  new_savings_score: number;
  score_gained: number;
}

export interface NotificationMarkReadResult {
  updated: number;
}

export interface NotificationRetryResult {
  queued: boolean;
}

export interface NotificationEventItem {
  id: string;
  channel: string;
  action_type: 'JOURNAL' | 'CARD';
  status: 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED';
  receiver_user_id?: string | null;
  sender_user_id?: string | null;
  source_session_id?: string | null;
  receiver_email: string;
  dedupe_key?: string | null;
  is_read: boolean;
  read_at?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface NotificationStats {
  total_count: number;
  unread_count: number;
  queued_count: number;
  sent_count: number;
  failed_count: number;
  throttled_count: number;
  journal_count: number;
  card_count: number;
  recent_24h_count: number;
  recent_24h_failed_count: number;
  window_days: number;
  window_total_count: number;
  window_sent_count: number;
  window_failed_count: number;
  window_throttled_count: number;
  window_queued_count: number;
  window_daily: NotificationDailyStatsItem[];
  window_top_failure_reasons: NotificationErrorReasonStatsItem[];
  last_event_at?: string | null;
}

export interface NotificationFilters {
  unread_only?: boolean;
  action_type?: 'JOURNAL' | 'CARD';
  status?: 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED';
  error_reason?: string;
}

export interface NotificationDailyStatsItem {
  date: string;
  total_count: number;
  sent_count: number;
  failed_count: number;
  throttled_count: number;
  queued_count: number;
}

export interface NotificationErrorReasonStatsItem {
  reason: string;
  count: number;
}

const LOCAL_CARDS: Record<string, ActionCardData> = {
  card_hug: {
    key: 'card_hug',
    title: '溫柔擁抱',
    description: '先放下對錯，給對方一個不帶評價的擁抱。',
    category: 'comfort',
    difficulty_level: 1,
  },
  card_walk: {
    key: 'card_walk',
    title: '散步五分鐘',
    description: '一起走一小段路，讓情緒慢慢落地。',
    category: 'action',
    difficulty_level: 1,
  },
  card_tea: {
    key: 'card_tea',
    title: '一杯熱飲',
    description: '幫彼此準備一杯熱飲，建立安定感。',
    category: 'comfort',
    difficulty_level: 1,
  },
  card_write: {
    key: 'card_write',
    title: '一句感謝',
    description: '寫下一句今天最想謝謝對方的話。',
    category: 'connection',
    difficulty_level: 1,
  },
};

export const fetchJournals = async (): Promise<Journal[]> => {
  const response = await api.get('/journals/');
  return response.data;
};

export const createJournal = async (content: string): Promise<CreateJournalResponse> => {
  const cleanedContent = content.trim();
  if (!cleanedContent) {
    throw new Error('日記內容不能為空白。');
  }
  if (cleanedContent.length > MAX_JOURNAL_CONTENT_LENGTH) {
    throw new Error(`日記內容不可超過 ${MAX_JOURNAL_CONTENT_LENGTH} 字元。`);
  }

  const response = await api.post<CreateJournalResponse>('/journals/', {
    content: cleanedContent
  });
  return response.data;
};

export const deleteJournal = async (id: string | number) => {
  await api.delete(`/journals/${id}`);
};

export const fetchPartnerJournals = async (): Promise<Journal[]> => {
  const response = await api.get('/journals/partner');
  return response.data;
};


export const fetchCard = async (key: string): Promise<ActionCardData> => {
  return LOCAL_CARDS[key] ?? {
    key,
    title: key.replace(/[_-]/g, ' '),
    description: '用一句真心話，回應你最在意的那個人。',
    category: 'connection',
    difficulty_level: 1,
  };
};


export const fetchPartnerStatus = async (): Promise<PartnerStatus> => {
  if (typeof window === 'undefined') {
    return { has_partner: false, latest_journal_at: null, current_score: 0, unread_notification_count: 0 };
  }
  const token = localStorage.getItem('token');
  if (!token) {
    return { has_partner: false, latest_journal_at: null, current_score: 0, unread_notification_count: 0 };
  }

  try {
    const response = await api.get<PartnerStatus>('/users/partner-status');
    return response.data;
  } catch (error) {
    console.warn('無法取得伴侶狀態:', error);
    return { has_partner: false, latest_journal_at: null, current_score: 0, unread_notification_count: 0 };
  }
};

export const markNotificationsRead = async (actionType?: 'journal' | 'card'): Promise<NotificationMarkReadResult> => {
  const response = await api.post<NotificationMarkReadResult>('/users/notifications/mark-read', null, {
    params: actionType ? { action_type: actionType } : undefined,
  });
  return response.data;
};

export const fetchNotifications = async (params?: {
  limit?: number;
  offset?: number;
} & NotificationFilters): Promise<NotificationEventItem[]> => {
  const response = await api.get<NotificationEventItem[]>('/users/notifications', { params });
  return response.data;
};

export const fetchNotificationStats = async (
  params?: {
    window_days?: number;
  } & NotificationFilters,
): Promise<NotificationStats> => {
  const response = await api.get<NotificationStats>('/users/notifications/stats', {
    params,
  });
  return response.data;
};

export const markNotificationRead = async (notificationId: string): Promise<NotificationMarkReadResult> => {
  const response = await api.post<NotificationMarkReadResult>(`/users/notifications/${notificationId}/read`);
  return response.data;
};

export const retryNotification = async (notificationId: string): Promise<NotificationRetryResult> => {
  const response = await api.post<NotificationRetryResult>(`/users/notifications/${notificationId}/retry`);
  return response.data;
};
