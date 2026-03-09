import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import {
  isApiEnvelopePayload,
  normalizeApiEnvelopeError,
  unwrapApiEnvelopeData,
} from '@/lib/api-envelope';

const DEFAULT_API_URL = 'http://localhost:8000/api';
const IDEMPOTENCY_CACHE_WINDOW_MS = 12_000;
const IDEMPOTENCY_CACHE_MAX_ENTRIES = 512;
const IDEMPOTENCY_CACHE_STORAGE_KEY = 'haven_idempotency_cache_v1';

function normalizeApiUrl(raw?: string): string {
  if (!raw) return DEFAULT_API_URL;
  return raw.endsWith('/') ? raw.slice(0, -1) : raw;
}

export const API_URL = normalizeApiUrl(process.env.NEXT_PUBLIC_API_URL);
const DEVICE_ID_STORAGE_KEY = 'haven_device_id';
const IDEMPOTENCY_EXEMPT_PATHS = new Set(['/auth/token', '/auth/refresh', '/auth/logout']);
const idempotencyKeyCache = new Map<string, { key: string; expiresAt: number }>();
let idempotencyCacheHydrated = false;

interface RetryableInternalAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

function resolveDeviceId(): string | null {
  if (typeof window === 'undefined') return null;
  const cached = localStorage.getItem(DEVICE_ID_STORAGE_KEY)?.trim();
  if (cached) return cached;

  const generated =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(DEVICE_ID_STORAGE_KEY, generated);
  return generated;
}

function resolveIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `web-idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function _stableSerialize(value: unknown): string {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return `[${value.map((item) => _stableSerialize(item)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const raw = value as Record<string, unknown>;
    const keys = Object.keys(raw).sort();
    const entries = keys.map((key) => `${JSON.stringify(key)}:${_stableSerialize(raw[key])}`);
    return `{${entries.join(',')}}`;
  }
  return JSON.stringify(String(value));
}

function _hashFnv1a(input: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return (hash >>> 0).toString(16);
}

async function _hashSha256Hex(input: string): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto.subtle && typeof TextEncoder !== 'undefined') {
    const encoded = new TextEncoder().encode(input);
    const digest = await crypto.subtle.digest('SHA-256', encoded);
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, '0'))
      .join('');
  }
  return _hashFnv1a(input);
}

function _pruneIdempotencyCache(nowMs: number): void {
  _hydrateIdempotencyCacheIfNeeded(nowMs);
  for (const [fingerprint, entry] of idempotencyKeyCache.entries()) {
    if (entry.expiresAt <= nowMs) {
      idempotencyKeyCache.delete(fingerprint);
    }
  }
  if (idempotencyKeyCache.size <= IDEMPOTENCY_CACHE_MAX_ENTRIES) {
    return;
  }
  const overflow = idempotencyKeyCache.size - IDEMPOTENCY_CACHE_MAX_ENTRIES;
  let evicted = 0;
  for (const [fingerprint] of idempotencyKeyCache) {
    idempotencyKeyCache.delete(fingerprint);
    evicted += 1;
    if (evicted >= overflow) break;
  }
  _persistIdempotencyCache(nowMs);
}

function _persistIdempotencyCache(nowMs: number): void {
  if (typeof window === 'undefined') return;
  try {
    const rows: Array<{ fingerprint: string; key: string; expiresAt: number }> = [];
    for (const [fingerprint, entry] of idempotencyKeyCache.entries()) {
      if (entry.expiresAt <= nowMs) continue;
      rows.push({ fingerprint, key: entry.key, expiresAt: entry.expiresAt });
    }
    window.localStorage.setItem(IDEMPOTENCY_CACHE_STORAGE_KEY, JSON.stringify(rows));
  } catch {
    // ignore storage persistence failures
  }
}

function _hydrateIdempotencyCacheIfNeeded(nowMs: number): void {
  if (idempotencyCacheHydrated || typeof window === 'undefined') return;
  idempotencyCacheHydrated = true;
  try {
    const raw = window.localStorage.getItem(IDEMPOTENCY_CACHE_STORAGE_KEY);
    if (!raw) return;
    const rows = JSON.parse(raw);
    if (!Array.isArray(rows)) return;
    for (const row of rows) {
      if (!row || typeof row !== 'object') continue;
      const fingerprint = `${(row as { fingerprint?: string }).fingerprint || ''}`.trim();
      const key = `${(row as { key?: string }).key || ''}`.trim();
      const expiresAt = Number((row as { expiresAt?: number }).expiresAt || 0);
      if (!fingerprint || !key || !Number.isFinite(expiresAt) || expiresAt <= nowMs) continue;
      idempotencyKeyCache.set(fingerprint, { key, expiresAt });
    }
  } catch {
    // ignore storage parsing failures
  }
}

async function _buildIdempotencyFingerprint(config: InternalAxiosRequestConfig): Promise<string> {
  const method = (config.method || 'post').toUpperCase();
  const rawUrl = `${config.url ?? ''}`.trim();
  const basePath = rawUrl.split('?')[0] || '';
  const paramsToken = config.params ? _stableSerialize(config.params) : '';
  const bodyToken = typeof config.data === 'undefined' ? '' : _stableSerialize(config.data);
  const token = `${method}|${basePath}|${paramsToken}|${bodyToken}`;
  return _hashSha256Hex(token);
}

async function resolveStableIdempotencyKey(config: InternalAxiosRequestConfig): Promise<string> {
  const nowMs = Date.now();
  _pruneIdempotencyCache(nowMs);
  const fingerprint = await _buildIdempotencyFingerprint(config);
  const cached = idempotencyKeyCache.get(fingerprint);
  if (cached && cached.expiresAt > nowMs) {
    return cached.key;
  }
  const generated = resolveIdempotencyKey();
  idempotencyKeyCache.set(fingerprint, {
    key: generated,
    expiresAt: nowMs + IDEMPOTENCY_CACHE_WINDOW_MS,
  });
  _persistIdempotencyCache(nowMs);
  return generated;
}

function shouldAttachIdempotencyKey(config: InternalAxiosRequestConfig): boolean {
  const method = (config.method || 'get').toUpperCase();
  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    return false;
  }
  const rawUrl = `${config.url ?? ''}`.trim();
  if (!rawUrl) return false;
  const withoutQuery = rawUrl.split('?')[0] || '';
  return !IDEMPOTENCY_EXEMPT_PATHS.has(withoutQuery);
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 20_000,  // 降低超時時間（原為 60s，現為 20s）
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // 🔒 令浏览器自動在所有請求中帶上 httpOnly Cookie
});

// 🔥 攔截器：添加 X-Device-Id header
api.interceptors.request.use(async (config) => {
  if (typeof window !== 'undefined') {
    const deviceId = resolveDeviceId();
    if (deviceId) {
      config.headers['X-Device-Id'] = deviceId;
    }
  }
  if (shouldAttachIdempotencyKey(config) && !config.headers['Idempotency-Key']) {
    config.headers['Idempotency-Key'] = await resolveStableIdempotencyKey(config);
  }
  return config;
});

// 🔥 攔截器：處理 401 自動刷新令牌
api.interceptors.response.use(
  (response: AxiosResponse) => {
    const payload = response.data;
    if (isApiEnvelopePayload(payload)) {
      // Contract marker: response.data = payload.data
      response.data = unwrapApiEnvelopeData(payload);
    }
    return response;
  },
  async (error: AxiosError) => {
    const maybeEnvelope = error.response?.data;
    const normalizedError = normalizeApiEnvelopeError(maybeEnvelope);
    if (normalizedError) {
      if (error.response) {
        const envelopeObject =
          maybeEnvelope && typeof maybeEnvelope === 'object'
            ? (maybeEnvelope as Record<string, unknown>)
            : {};
        error.response.data = {
          ...envelopeObject,
          detail: normalizedError.detail,
          message: normalizedError.message,
          code: normalizedError.code,
        };
      }
    }
    const originalConfig = error.config as RetryableInternalAxiosRequestConfig | undefined;
    
    // 如果是 401 且尚未重試過
    if (error.response?.status === 401 && originalConfig && !originalConfig._retry) {
      originalConfig._retry = true;
      
      try {
        // 嘗試刷新令牌
        // 由於使用 httpOnly Cookie，刷新邏輯在前端無法直接訪問令牌
        // 這裡只是觸發通知 AuthContext 令牌已過期
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('haven:auth-expired'));
        }
      } catch (refreshError) {
        // 刷新失敗，觸發登出
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('haven:auth-expired'));
        }
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  },
);

export { api };
export default api;
