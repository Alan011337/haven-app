// frontend/src/services/auth.ts
import api, { type ApiRequestConfig } from '@/lib/api';
import type { User } from '@/types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// 1. 登入 (Login)
export const login = async (email: string, password: string): Promise<LoginResponse> => {
  // ⚠️ 修正重點：FastAPI 登入接口不喜歡 FormData，它喜歡 URLSearchParams
  const params = new URLSearchParams();
  params.append('username', email); // 雖然我們用 email，但欄位名必須叫 username
  params.append('password', password);

  // 送出請求，並指定 Header 確保萬無一失
  const response = await api.post('/auth/token', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  return response.data;
};

// 2. 註冊 (Register)
export const register = async (
  email: string,
  password: string,
  full_name: string,
  age_confirmed: boolean,
  terms_version: string,
  privacy_version: string,
  birth_year?: number,
): Promise<User> => {
  const response = await api.post('/users/', {
    email,
    password,
    full_name,
    age_confirmed,
    agreed_to_terms: age_confirmed,
    terms_version,
    privacy_version,
    ...(birth_year ? { birth_year } : {}),
  });
  return response.data;
};

// 3. 取得目前使用者
export const getCurrentUser = async (config?: ApiRequestConfig): Promise<User> => {
  const response = await api.get<User>('/users/me', config);
  return response.data;
};
