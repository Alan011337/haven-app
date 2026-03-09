// frontend/src/contexts/AuthContext.tsx

'use client';

import React, { createContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { logClientError } from '@/lib/safe-error-log';
import {
  capturePosthogEvent,
  identifyPosthogUser,
  resetPosthogUser,
} from '@/lib/posthog';
import { User } from '@/types';

// --- 定義型別 (Types) ---

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (token: string, userData: User, redirectTo?: AuthLoginRedirectPath) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

export type AuthLoginRedirectPath = '/' | '/settings';

// --- 建立 Context (空殼) ---
// 這裡要把 export 加上去，因為 hooks 檔案需要引用它
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// --- 建立 Provider (供應商) ---
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // 1. 初始化檢查：驗證 httpOnly Cookie 中的令牌是否有效
  useEffect(() => {
    const initAuth = async () => {
      try {
        // 由於使用 httpOnly Cookie 和 withCredentials: true，
        // 浏览器會自動發送 Cookie。只需驗證當前用戶
        const response = await api.get<User>('/users/me'); 
        setUser(response.data);
        identifyPosthogUser(String(response.data.id || ''));
      } catch (error) {
        // 如果 401 或其他錯誤，表示沒有有效的 Cookie
        logClientError('auth-init-verify-failed', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // 2. 登入邏輯（在前端只用於 UI 更新，實際令牌由後端 httpOnly Cookie 管理）
  const login = useCallback(
    (token: string, userData: User, redirectTo: AuthLoginRedirectPath = '/') => {
      // 註：password 將由後端通過 httpOnly Cookie 自動設置
      // 前端這裡只是更新 React 狀態以反映 UI
      setUser(userData);
      identifyPosthogUser(String(userData.id || ''));
      capturePosthogEvent('login_succeeded', { auth_stage: 'login' });
      router.push(redirectTo);
    },
    [router],
  );

  // 3. 登出邏輯
  const logout = useCallback(async () => {
    capturePosthogEvent('logout_clicked', { auth_stage: 'logout' });
    try {
      // 調用後端登出端點以清除 httpOnly Cookie
      await api.post('/auth/logout');
    } catch (error) {
      logClientError('auth-logout-failed', error);
    } finally {
      // 無論後端請求是否成功，都清除前端狀態
      setUser(null);
      resetPosthogUser();
      router.push('/login');
    }
  }, [router]);

  // 3b. 監聽認證過期事件（由 api.ts interceptor 觸發）
  useEffect(() => {
    const handleExpired = () => {
      capturePosthogEvent('token_refresh_failed', { reason: 'auth_expired' });
      void logout();
    };
    window.addEventListener('haven:auth-expired', handleExpired);
    return () => window.removeEventListener('haven:auth-expired', handleExpired);
  }, [logout]);

  // 4. 資料刷新邏輯
  const refreshUser = useCallback(async () => {
    try {
      const response = await api.get<User>('/users/me');
      setUser(response.data);
      identifyPosthogUser(String(response.data.id || ''));
      capturePosthogEvent('token_refresh_succeeded', { auth_stage: 'refresh_user' });
    } catch (error) {
      logClientError('auth-refresh-user-failed', error);
      capturePosthogEvent('token_refresh_failed', { reason: 'refresh_user_failed' });
    }
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, logout, refreshUser }),
    [user, isLoading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
