/**
 * Login for Haven Mobile. Calls backend POST /auth/token, stores access_token in SecureStore.
 */

import * as SecureStore from 'expo-secure-store';
import { TOKEN_KEY, setToken } from './HavenApiNative';

function getBaseUrl(): string {
  if (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_API_URL) {
    const url = process.env.EXPO_PUBLIC_API_URL;
    return url.endsWith('/') ? url.slice(0, -1) : url;
  }
  return 'http://localhost:8000/api';
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams();
  body.append('username', email);
  body.append('password', password);

  const res = await fetch(`${getBaseUrl()}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text);
      if (j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
    } catch {
      // ignore
    }
    throw new Error(detail || `登入失敗 (${res.status})`);
  }

  const data = (await res.json()) as LoginResponse;
  await setToken(data.access_token);
  return data;
}

export async function getStoredToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    return null;
  }
}
