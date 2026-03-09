import api from '@/lib/api';
import { Card, CardCategory } from '@/types';
import { logClientError } from '@/lib/safe-error-log';
import { buildIdempotencyHeaders } from '@/lib/idempotency';

// 定義回答卡片的資料結構
export interface CardResponsePayload {
  card_id: string;
  content: string;
}

export interface CardResponseData {
  id: string;
  card_id: string;
  user_id: string;
  content: string;
  status: 'PENDING' | 'REVEALED'; // 關鍵狀態
  created_at: string;
  session_id?: string | null;
}

export interface DailyStatus {
  state: 'IDLE' | 'PARTNER_STARTED' | 'WAITING_PARTNER' | 'COMPLETED';
  card: Card | null;
  my_content?: string;
  partner_content?: string;
  partner_name?: string;
  session_id?: string | null;
}

export const cardService = {
  drawCard: async (category?: CardCategory): Promise<Card> => {
    try {
      const params = category ? { category } : {};
      const response = await api.get<Card>('/cards/draw', {
        params,
      });
      return response.data;
    } catch (error) {
      logClientError('draw-card-failed', error);
      throw error;
    }
  },

  respondToCard: async (data: CardResponsePayload): Promise<CardResponseData> => {
    try {
      const response = await api.post<CardResponseData>('/cards/respond', data);
      return response.data;
    } catch (error) {
      logClientError('respond-card-failed', error);
      throw error;
    }
  },

  getAllCards: async (): Promise<Card[]> => {
    try {
      const response = await api.get<Card[]>('/cards/');
      return response.data;
    } catch (error) {
      logClientError('get-all-cards-failed', error);
      throw error;
    }
  },

  getDailyStatus: async (): Promise<DailyStatus> => {
    try {
      const response = await api.get<DailyStatus>('/cards/daily-status');
      return response.data;
    } catch (error) {
      logClientError('get-daily-status-failed', error);
      throw error;
    }
  },

  drawDailyCard: async (): Promise<Card> => {
    try {
      const response = await api.get<Card>('/cards/draw', {
        params: {
          category: 'daily_vibe',
          source: 'daily_ritual',
        },
      });
      return response.data;
    } catch (error) {
      logClientError('draw-daily-card-failed', error);
      throw error;
    }
  },

  respondDailyCard: async (
    cardId: string,
    content: string,
    options?: { idempotencyKey?: string }
  ): Promise<CardResponseData> => {
    try {
      const headers = buildIdempotencyHeaders(options?.idempotencyKey);
      const response = await api.post<CardResponseData>(
        '/cards/respond',
        { card_id: cardId, content },
        headers ? { headers } : undefined
      );
      return response.data;
    } catch (error) {
      logClientError('respond-daily-card-failed', error);
      throw error;
    }
  },
};
