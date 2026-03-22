/**
 * API request/response types (backend contract).
 * Shared so web and native use the same shapes.
 */

import type { Journal } from './types';

export const MAX_JOURNAL_CONTENT_LENGTH = 12000;

export interface PartnerStatus {
  has_partner: boolean;
  latest_journal_at: string | null;
  current_score: number;
  unread_notification_count: number;
}

export interface CreateJournalOptions {
  requestId?: string;
  idempotencyKey?: string;
}

export interface CreateJournalResponse extends Journal {
  new_savings_score: number;
  score_gained: number;
}

export interface JournalDraftPayload {
  is_draft?: boolean;
}

export interface CardResponsePayload {
  card_id: string;
  content: string;
}

export interface CardResponseData {
  id: string;
  card_id: string;
  user_id: string;
  content: string;
  status: 'PENDING' | 'REVEALED';
  created_at: string;
  session_id?: string | null;
}

export interface DeckRespondResult {
  status: string;
  session_status: 'WAITING_PARTNER' | 'COMPLETED';
}

export interface DeckHistoryEntry {
  session_id: string;
  card_title: string | null;
  card_question: string;
  category: string;
  depth_level?: number;
  my_answer: string | null;
  partner_answer: string | null;
  revealed_at: string;
}

export interface CardSession {
  id: string;
  card_id: string;
  category: string;
  status: 'PENDING' | 'WAITING_PARTNER' | 'COMPLETED';
  created_at: string;
  card: { id: string; title: string | null; question: string; category: string; depth_level?: number; tags?: string[] };
  partner_name?: string;
}

export interface RespondToDeckOptions {
  idempotencyKey?: string;
}

export interface DeckHistorySummary {
  total_records: number;
  this_month_records: number;
  top_category: string | null;
  top_category_count: number;
}
