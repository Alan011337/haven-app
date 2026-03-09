// frontend/src/services/auth.ts
import api from '@/lib/api';
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

// 2. 註冊 (Register) - 這部分你已經成功了，保持原樣
export const register = async (
  email: string,
  password: string,
  full_name: string,
): Promise<User> => {
  const response = await api.post('/users/', {
    email,
    password,
    full_name,
  });
  return response.data;
};

// 3. 取得目前使用者
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get<User>('/users/me');
  return response.data;
};
