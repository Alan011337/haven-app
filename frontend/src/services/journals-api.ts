import type { AxiosRequestConfig } from 'axios';
import api from '@/lib/api';
import { Journal } from '@/types';
import { buildIdempotencyHeaders } from '@/lib/idempotency';

/** Single source of truth for journal content length (used by api-client and JournalInput). */
export const MAX_JOURNAL_CONTENT_LENGTH = 4000;

/** Default initial page size for faster first load; backend supports up to 100. */
export const JOURNALS_INITIAL_LIMIT = 20;

export interface CreateJournalResponse extends Journal {
  new_savings_score: number;
  score_gained: number;
}

export interface CreateJournalOptions {
  /** Optional: X-Request-Id sent with request for CUJ-02 journal timeline (same as request_id in trackJournalSubmit). */
  requestId?: string;
  /** P2-F: Idempotency-Key for offline replay (same as operation_id in offline queue). */
  idempotencyKey?: string;
}

export interface CursorListResult<T> {
  items: T[];
  nextCursor: string | null;
}

function parseNextCursorFromHeaders(headers: Record<string, unknown> | undefined): string | null {
  if (!headers) return null;
  const value = headers['x-next-cursor'] ?? headers['X-Next-Cursor'];
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export const fetchJournals = async (params?: {
  limit?: number;
  offset?: number;
  cursor?: string | null;
}, config?: AxiosRequestConfig): Promise<Journal[]> => {
  const limit = params?.limit ?? JOURNALS_INITIAL_LIMIT;
  const offset = params?.offset ?? 0;
  const response = await api.get<Journal[]>('/journals/', {
    ...config,
    params: {
      limit,
      ...(params?.cursor ? { cursor: params.cursor } : { offset }),
    },
  });
  return response.data;
};

export const fetchJournalsPage = async (params?: {
  limit?: number;
  offset?: number;
  cursor?: string | null;
}, config?: AxiosRequestConfig): Promise<CursorListResult<Journal>> => {
  const limit = params?.limit ?? JOURNALS_INITIAL_LIMIT;
  const offset = params?.offset ?? 0;
  const response = await api.get<Journal[]>('/journals/', {
    ...config,
    params: {
      limit,
      ...(params?.cursor ? { cursor: params.cursor } : { offset }),
    },
  });
  return {
    items: response.data,
    nextCursor: parseNextCursorFromHeaders((response as unknown as { headers?: Record<string, unknown> }).headers),
  };
};

export const createJournal = async (
  content: string,
  options?: CreateJournalOptions
): Promise<CreateJournalResponse> => {
  const cleanedContent = content.trim();
  if (!cleanedContent) {
    throw new Error('日記內容不能為空白。');
  }
  if (cleanedContent.length > MAX_JOURNAL_CONTENT_LENGTH) {
    throw new Error(`日記內容不可超過 ${MAX_JOURNAL_CONTENT_LENGTH} 字元。`);
  }

  const headers: Record<string, string> = {};
  if (options?.requestId && options.requestId.length >= 8) {
    headers['X-Request-Id'] = options.requestId;
  }
  const idempotencyHeaders = buildIdempotencyHeaders(options?.idempotencyKey);
  if (idempotencyHeaders) {
    Object.assign(headers, idempotencyHeaders);
  }
  const response = await api.post<CreateJournalResponse>(
    '/journals/',
    { content: cleanedContent },
    Object.keys(headers).length ? { headers } : undefined
  );
  return response.data;
};

export const deleteJournal = async (id: string | number) => {
  await api.delete(`/journals/${id}`);
};

export const fetchPartnerJournals = async (params?: {
  limit?: number;
  offset?: number;
  cursor?: string | null;
}, config?: AxiosRequestConfig): Promise<Journal[]> => {
  const limit = params?.limit ?? JOURNALS_INITIAL_LIMIT;
  const offset = params?.offset ?? 0;
  const response = await api.get<Journal[]>('/journals/partner', {
    ...config,
    params: {
      limit,
      ...(params?.cursor ? { cursor: params.cursor } : { offset }),
    },
  });
  return response.data;
};

export const fetchPartnerJournalsPage = async (params?: {
  limit?: number;
  offset?: number;
  cursor?: string | null;
}, config?: AxiosRequestConfig): Promise<CursorListResult<Journal>> => {
  const limit = params?.limit ?? JOURNALS_INITIAL_LIMIT;
  const offset = params?.offset ?? 0;
  const response = await api.get<Journal[]>('/journals/partner', {
    ...config,
    params: {
      limit,
      ...(params?.cursor ? { cursor: params.cursor } : { offset }),
    },
  });
  return {
    items: response.data,
    nextCursor: parseNextCursorFromHeaders((response as unknown as { headers?: Record<string, unknown> }).headers),
  };
};
