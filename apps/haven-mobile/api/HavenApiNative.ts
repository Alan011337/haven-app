/**
 * Haven API client for React Native (Expo).
 * Implements HavenApiClient with fetch + expo-secure-store (token, deviceId).
 */

import * as SecureStore from 'expo-secure-store';
import type { HavenApiClient } from 'haven-shared';
import type {
  CreateJournalOptions,
  CreateJournalResponse,
  PartnerStatus,
  CardResponseData,
  DeckRespondResult,
  CardSession,
  DeckHistoryEntry,
  DeckHistorySummary,
} from 'haven-shared';
import type { Card, Journal } from 'haven-shared';

export const TOKEN_KEY = 'haven_token';
const DEVICE_ID_KEY = 'haven_device_id';

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

function getBaseUrl(): string {
  if (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_API_URL) {
    const url = process.env.EXPO_PUBLIC_API_URL;
    return url.endsWith('/') ? url.slice(0, -1) : url;
  }
  return 'http://localhost:8000/api';
}

function generateDeviceId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `rn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function getStoredToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    return null;
  }
}

async function getStoredDeviceId(): Promise<string> {
  try {
    const id = await SecureStore.getItemAsync(DEVICE_ID_KEY);
    if (id) return id;
    const newId = generateDeviceId();
    await SecureStore.setItemAsync(DEVICE_ID_KEY, newId);
    return newId;
  } catch {
    return generateDeviceId();
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: object,
  options?: { idempotencyKey?: string; requestId?: string }
): Promise<T> {
  const base = getBaseUrl();
  const token = await getStoredToken();
  const deviceId = await getStoredDeviceId();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Device-Id': deviceId,
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options?.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey;
  if (options?.requestId) headers['X-Request-Id'] = options.requestId;

  const res = await fetch(`${base}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text);
      if (j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
    } catch {
      // use text as-is
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const HavenApiNative: HavenApiClient = {
  getToken(): string | null {
    return null;
  },
  getDeviceId(): string | null {
    return null;
  },

  async createJournal(content: string, options?: CreateJournalOptions): Promise<CreateJournalResponse> {
    return request<CreateJournalResponse>('POST', '/journals/', { content }, {
      idempotencyKey: options?.idempotencyKey,
      requestId: options?.requestId,
    });
  },

  async getJournals(): Promise<Journal[]> {
    return request<Journal[]>('GET', '/journals/');
  },

  async getPartnerJournals(): Promise<Journal[]> {
    return request<Journal[]>('GET', '/journals/partner');
  },

  async deleteJournal(id: string | number): Promise<void> {
    return request<void>('DELETE', `/journals/${id}`);
  },

  async getPartnerStatus(): Promise<PartnerStatus> {
    return request<PartnerStatus>('GET', '/users/partner-status');
  },

  async getDailyStatus(): Promise<{
    state: string;
    card: Card | null;
    my_content?: string;
    partner_content?: string;
    session_id?: string | null;
  }> {
    return request('GET', '/cards/daily-status');
  },

  async drawDailyCard(): Promise<Card> {
    return request<Card>('GET', '/cards/draw?category=daily_vibe&source=daily_ritual');
  },

  async respondDailyCard(
    cardId: string,
    content: string,
    options?: { idempotencyKey?: string }
  ): Promise<CardResponseData> {
    return request<CardResponseData>('POST', '/cards/respond', { card_id: cardId, content }, {
      idempotencyKey: options?.idempotencyKey,
    });
  },

  async drawDeckCard(category: string, forceNew?: boolean): Promise<CardSession> {
    const sp = new URLSearchParams({ category });
    if (forceNew) sp.set('skip_waiting', 'true');
    return request<CardSession>('POST', `/card-decks/draw?${sp.toString()}`);
  },

  async respondToDeckCard(
    sessionId: string,
    content: string,
    options?: { idempotencyKey?: string }
  ): Promise<DeckRespondResult> {
    return request<DeckRespondResult>('POST', `/card-decks/respond/${sessionId}`, { content }, {
      idempotencyKey: options?.idempotencyKey,
    });
  },

  async getDeckHistory(params?: {
    category?: string;
    limit?: number;
    offset?: number;
    revealed_from?: string;
    revealed_to?: string;
  }): Promise<DeckHistoryEntry[]> {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.limit != null) sp.set('limit', String(params.limit));
    if (params?.offset != null) sp.set('offset', String(params.offset));
    if (params?.revealed_from) sp.set('revealed_from', params.revealed_from);
    if (params?.revealed_to) sp.set('revealed_to', params.revealed_to);
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return request<DeckHistoryEntry[]>('GET', `/card-decks/history${q}`);
  },

  async getDeckHistorySummary(params?: {
    category?: string;
    revealed_from?: string;
    revealed_to?: string;
  }): Promise<DeckHistorySummary> {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.revealed_from) sp.set('revealed_from', params.revealed_from);
    if (params?.revealed_to) sp.set('revealed_to', params.revealed_to);
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return request<DeckHistorySummary>('GET', `/card-decks/history/summary${q}`);
  },
};
