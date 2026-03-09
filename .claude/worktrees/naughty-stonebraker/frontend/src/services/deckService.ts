// frontend/src/services/deckService.ts

import api from '@/lib/api';
import { normalizeDeckCategory } from '@/lib/deck-category';

// ----------------------------------------------------------------
// 1. 定義資料型別 (TypeScript Interfaces)
// ----------------------------------------------------------------

// 對應後端的 CardRead (根據你的 CardSessionBase, card_id 是 UUID，所以這裡是 string)
export interface CardData {
  id: string; 
  title: string | null; // 後端是 Optional[str]
  question: string;
  category: string;
  depth_level?: number;
  tags?: string[];
}

// 對應後端的 DeckHistoryEntry
export interface DeckHistoryEntry {
  // 注意：你的 Python Model 裡沒有回傳 history 本身的 id，只有 session_id
  session_id: string;     
  card_title: string | null;
  card_question: string;
  category: string;
  depth_level?: number;
  my_answer: string | null;      // 後端是 Optional[str]
  partner_answer: string | null; // 後端是 Optional[str]
  revealed_at: string;
}

// 對應後端的 CardSessionRead
export interface CardSession {
  id: string;      // UUID
  card_id: string; // UUID
  category: string;
  status: 'PENDING' | 'WAITING_PARTNER' | 'COMPLETED';
  created_at: string;
  card: CardData;  // 這是嵌套的卡片資料
  partner_name?: string; // 這是前端可能額外需要的，後端如果沒傳就是 undefined
}

// 回答後的回傳結構
export interface RespondResult {
  status: string;
  session_status: 'WAITING_PARTNER' | 'COMPLETED';
}

// 新增介面 (根據後端 CardResponse)
export interface CardResponse {
  id: string;
  card_id: string;
  user_id: string;
  content: string;
  status: string;
  created_at: string;
  session_id: string | null;
}

export interface DeckCardCount {
  category: string;
  total_cards: number;
  answered_cards: number;
  completion_rate: number;
}

export interface DeckHistoryQuery {
  category?: string;
  limit?: number;
  offset?: number;
  revealed_from?: string;
  revealed_to?: string;
}

export interface DeckHistorySummary {
  total_records: number;
  this_month_records: number;
  top_category: string | null;
  top_category_count: number;
}

// ----------------------------------------------------------------
// 2. API 函式 (Service Functions)
// ----------------------------------------------------------------

// 1. 抽卡 (開啟一個 Session)
export const drawDeckCard = async (category: string, forceNew: boolean = false): Promise<CardSession> => {
  const normalizedCategory = normalizeDeckCategory(category);
  if (!normalizedCategory) {
    throw new Error(`無效的牌組分類：${category}`);
  }

  const response = await api.post<CardSession>('/card-decks/draw', null, {
    params: { 
      category: normalizedCategory,
      skip_waiting: forceNew
    }
  });
  return response.data;
};

// 2. 回答卡片
export const respondToDeckCard = async (sessionId: string, content: string): Promise<RespondResult> => {
  const cleanedContent = content.trim();
  if (!cleanedContent) {
    throw new Error('回答內容不能為空白。');
  }

  const response = await api.post<RespondResult>(
    `/card-decks/respond/${sessionId}`,
    { content: cleanedContent }
  );
  return response.data;
};

// 3. 取得歷史紀錄
export const fetchDeckHistory = async (query: DeckHistoryQuery = {}): Promise<DeckHistoryEntry[]> => {
  const normalizedCategory = normalizeDeckCategory(query.category);
  const limit = query.limit ?? 20;
  const offset = query.offset ?? 0;
  const response = await api.get<DeckHistoryEntry[]>('/card-decks/history', {
    params: { 
      category: normalizedCategory ?? undefined,
      limit,
      offset,
      revealed_from: query.revealed_from,
      revealed_to: query.revealed_to,
    }
  });
  return response.data;
};

export const fetchDeckHistorySummary = async (
  query: DeckHistoryQuery = {},
): Promise<DeckHistorySummary> => {
  const normalizedCategory = normalizeDeckCategory(query.category);
  const response = await api.get<DeckHistorySummary>('/card-decks/history/summary', {
    params: {
      category: normalizedCategory ?? undefined,
      revealed_from: query.revealed_from,
      revealed_to: query.revealed_to,
    },
  });
  return response.data;
};

// 4. 取得牌組題數統計
export const fetchDeckCardCounts = async (): Promise<DeckCardCount[]> => {
  const response = await api.get<DeckCardCount[]>('/card-decks/stats');
  return response.data;
};

// 🔥 新增這個函式：用來撈取特定卡片的對話紀錄
export const fetchCardConversation = async (
  cardId: string,
  sessionId?: string,
): Promise<CardResponse[]> => {
  // 注意：這裡的路徑要對應後端 routers/cards.py 的路徑
  const response = await api.get<CardResponse[]>(`/cards/${cardId}/conversation`, {
    params: {
      session_id: sessionId,
    },
  });
  return response.data;
};
