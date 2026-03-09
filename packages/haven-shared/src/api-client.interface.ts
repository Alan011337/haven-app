/**
 * Haven API client interface (transport-agnostic).
 * Web implements with axios + localStorage; native implements with fetch + AsyncStorage.
 * Core flows (journal, card draw, deck) depend on this contract only.
 */

import type {
  CreateJournalOptions,
  CreateJournalResponse,
  PartnerStatus,
  CardResponseData,
  DeckRespondResult,
  CardSession,
  DeckHistoryEntry,
  DeckHistorySummary,
} from './api-types.js';
import type { Card } from './types';

export interface HavenApiClient {
  // Auth / identity (used by transport for headers)
  getToken(): string | null;
  getDeviceId(): string | null;

  // Journals (Core Flow)
  createJournal(content: string, options?: CreateJournalOptions): Promise<CreateJournalResponse>;
  getJournals(): Promise<import('./types').Journal[]>;
  getPartnerJournals(): Promise<import('./types').Journal[]>;
  deleteJournal(id: string | number): Promise<void>;

  // Partner / home
  getPartnerStatus(): Promise<PartnerStatus>;

  // Cards – daily ritual
  getDailyStatus(): Promise<{
    state: string;
    card: Card | null;
    my_content?: string;
    partner_content?: string;
    session_id?: string | null;
  }>;
  drawDailyCard(): Promise<Card>;
  respondDailyCard(cardId: string, content: string, options?: { idempotencyKey?: string }): Promise<CardResponseData>;

  // Cards – deck room
  drawDeckCard(category: string, forceNew?: boolean): Promise<CardSession>;
  respondToDeckCard(sessionId: string, content: string, options?: { idempotencyKey?: string }): Promise<DeckRespondResult>;
  getDeckHistory(params?: { category?: string; limit?: number; offset?: number; revealed_from?: string; revealed_to?: string }): Promise<DeckHistoryEntry[]>;
  getDeckHistorySummary(params?: { category?: string; revealed_from?: string; revealed_to?: string }): Promise<DeckHistorySummary>;
}
