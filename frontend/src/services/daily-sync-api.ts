import { apiGet, apiPost } from '@/services/api-transport';

export interface DailySyncStatusPublic {
  today: string;
  my_filled: boolean;
  partner_filled: boolean;
  unlocked: boolean;
  my_mood_score: number | null;
  my_question_id: string | null;
  my_answer_text: string | null;
  partner_mood_score: number | null;
  partner_question_id: string | null;
  partner_answer_text: string | null;
  today_question_id: string | null;
  today_question_label: string | null;
}

export const fetchDailySyncStatus = async (): Promise<DailySyncStatusPublic> => {
  return apiGet<DailySyncStatusPublic>('/daily-sync/status');
};

export const submitDailySync = async (payload: {
  mood_score: number;
  question_id: string;
  answer_text: string;
}): Promise<{ status: string; message: string }> => {
  return apiPost<{ status: string; message: string }>('/daily-sync', payload);
};
