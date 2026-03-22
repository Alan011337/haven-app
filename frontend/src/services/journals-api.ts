import type { AxiosRequestConfig } from 'axios';
import api from '@/lib/api';
import { MAX_JOURNAL_CONTENT_LENGTH } from 'haven-shared';
import type {
  Journal,
  JournalAttachmentPublic,
  JournalVisibility,
} from '@/types';
import { buildIdempotencyHeaders } from '@/lib/idempotency';

export { MAX_JOURNAL_CONTENT_LENGTH };

/** Default initial page size for faster first load; backend supports up to 100. */
export const JOURNALS_INITIAL_LIMIT = 20;

export interface CreateJournalResponse extends Journal {
  new_savings_score: number;
  score_gained: number;
}

export interface JournalUpsertPayload {
  content: string;
  is_draft?: boolean;
  title?: string | null;
  visibility?: JournalVisibility;
  content_format?: 'markdown';
}

export interface CreateJournalOptions {
  /** Optional: X-Request-Id sent with request for CUJ-02 journal timeline (same as request_id in trackJournalSubmit). */
  requestId?: string;
  /** P2-F: Idempotency-Key for offline replay (same as operation_id in offline queue). */
  idempotencyKey?: string;
}

export interface UpdateJournalPayload {
  content?: string;
  is_draft?: boolean;
  title?: string | null;
  visibility?: JournalVisibility;
}

export interface CursorListResult<T> {
  items: T[];
  nextCursor: string | null;
}

function extractValidationDetailMessage(detail: unknown): string | null {
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first && typeof first === 'object') {
      const item = first as { loc?: unknown; msg?: unknown };
      const loc = Array.isArray(item.loc)
        ? item.loc
            .map((segment) => `${segment ?? ''}`.trim())
            .filter(Boolean)
            .join('.')
        : '';
      const message = typeof item.msg === 'string' ? item.msg.trim() : '';
      if (loc && message) return `${loc}: ${message}`;
      if (message) return message;
    }
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim();
  }

  if (detail && typeof detail === 'object') {
    const record = detail as { msg?: unknown; detail?: unknown; message?: unknown };
    if (typeof record.msg === 'string' && record.msg.trim()) {
      return record.msg.trim();
    }
    if (typeof record.detail === 'string' && record.detail.trim()) {
      return record.detail.trim();
    }
    if (typeof record.message === 'string' && record.message.trim()) {
      return record.message.trim();
    }
  }

  return null;
}

function extractJournalApiErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: unknown } }).response;
    const detail = response?.data && typeof response.data === 'object'
      ? (response.data as { detail?: unknown; message?: unknown }).detail
        ?? (response.data as { detail?: unknown; message?: unknown }).message
      : undefined;
    const detailedMessage = extractValidationDetailMessage(detail);
    if (detailedMessage) return detailedMessage;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
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
  draft: string | JournalUpsertPayload,
  options?: CreateJournalOptions
): Promise<CreateJournalResponse> => {
  const payload =
    typeof draft === 'string'
      ? {
          content: draft,
          content_format: 'markdown' as const,
          is_draft: false,
          visibility: 'PARTNER_TRANSLATED_ONLY' as const,
        }
      : {
          ...draft,
          content_format: 'markdown' as const,
          is_draft: draft.is_draft ?? false,
          visibility: draft.visibility ?? 'PARTNER_TRANSLATED_ONLY',
        };

  const normalizedContent = payload.content.replace(/\r\n/g, '\n');
  const cleanedContent = normalizedContent.trim();
  if (!payload.is_draft && !cleanedContent) {
    throw new Error('日記內容不能為空白。');
  }
  if (normalizedContent.length > MAX_JOURNAL_CONTENT_LENGTH) {
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
  try {
    const response = await api.post<CreateJournalResponse>(
      '/journals/',
      {
        ...payload,
        content: payload.is_draft ? normalizedContent : cleanedContent,
      },
      Object.keys(headers).length ? { headers } : undefined
    );
    return response.data;
  } catch (error) {
    throw new Error(extractJournalApiErrorMessage(error, '儲存失敗，請稍後再試。'));
  }
};

export const fetchJournalById = async (
  id: string,
  config?: AxiosRequestConfig,
): Promise<Journal> => {
  const response = await api.get<Journal>(`/journals/${id}`, config);
  return response.data;
};

export const updateJournal = async (
  id: string,
  payload: UpdateJournalPayload,
): Promise<Journal> => {
  try {
    const response = await api.patch<Journal>(`/journals/${id}`, payload);
    return response.data;
  } catch (error) {
    throw new Error(extractJournalApiErrorMessage(error, '更新失敗，請稍後再試。'));
  }
};

export const uploadJournalAttachment = async (
  journalId: string,
  file: File,
): Promise<JournalAttachmentPublic> => {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await api.post<JournalAttachmentPublic>(
      `/journals/${journalId}/attachments`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      },
    );
    return response.data;
  } catch (error) {
    throw new Error(extractJournalApiErrorMessage(error, '圖片上傳失敗，請稍後再試。'));
  }
};

export const deleteJournalAttachment = async (
  journalId: string,
  attachmentId: string,
): Promise<void> => {
  await api.delete(`/journals/${journalId}/attachments/${attachmentId}`);
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
