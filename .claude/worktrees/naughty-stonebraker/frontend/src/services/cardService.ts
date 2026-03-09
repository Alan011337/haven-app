import api from '@/lib/api';
import { Card, CardCategory } from '../types';

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
      console.error('Error drawing card:', error);
      throw error;
    }
  },

  respondToCard: async (data: CardResponsePayload): Promise<CardResponseData> => {
    try {
      const response = await api.post<CardResponseData>('/cards/respond', data);
      return response.data;
    } catch (error) {
      console.error('Error responding to card:', error);
      throw error;
    }
  },

  getAllCards: async (): Promise<Card[]> => {
    const response = await api.get<Card[]>('/cards/');
    return response.data;
  },

  getDailyStatus: async (): Promise<DailyStatus> => {
    const response = await api.get<DailyStatus>('/cards/daily-status');
    return response.data;
  },

  drawDailyCard: async (): Promise<Card> => {
    const response = await api.get<Card>('/cards/draw', {
      params: {
        category: 'daily_vibe',
        source: 'daily_ritual',
      },
    });
    return response.data;
  },

  respondDailyCard: async (cardId: string, content: string): Promise<CardResponseData> => {
    const response = await api.post<CardResponseData>('/cards/respond', {
      card_id: cardId,
      content,
    });
    return response.data;
  },
};
