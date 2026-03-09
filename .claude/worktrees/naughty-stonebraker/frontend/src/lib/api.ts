import axios from 'axios';

const DEFAULT_API_URL = 'http://localhost:8000/api';

function normalizeApiUrl(raw?: string): string {
  if (!raw) return DEFAULT_API_URL;
  return raw.endsWith('/') ? raw.slice(0, -1) : raw;
}

export const API_URL = normalizeApiUrl(process.env.NEXT_PUBLIC_API_URL);
const DEVICE_ID_STORAGE_KEY = 'haven_device_id';

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

const api = axios.create({
  baseURL: API_URL,
  timeout: 60_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 🔥 攔截器：每次發送請求前，自動去 localStorage 抓 Token 並掛上去
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const deviceId = resolveDeviceId();
    if (deviceId) {
      config.headers['X-Device-Id'] = deviceId;
    }
  }
  return config;
});

// 🔥 攔截器：如果後端回傳 401 (未授權)，自動登出
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
    return Promise.reject(error);
  },
);

export { api };
export default api;
