// frontend/src/contexts/AuthContext.tsx

'use client';

import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api'; 
import { User } from '@/types';

// --- 定義型別 (Types) ---

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

// --- 建立 Context (空殼) ---
// 這裡要把 export 加上去，因為 hooks 檔案需要引用它
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// --- 建立 Provider (供應商) ---
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // 1. 初始化檢查 Token
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // 這裡建議掛上 Token 到 header (如果 api lib 沒做)
          // api.defaults.headers.Authorization = `Bearer ${token}`;
          
          const response = await api.get<User>('/users/me'); 
          setUser(response.data);
        } catch (error) {
          console.error("登入驗證失敗", error);
          localStorage.removeItem('token');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  // 2. 登入邏輯
  const login = (token: string, userData: User) => {
    localStorage.setItem('token', token);
    setUser(userData);
    router.push('/'); 
  };

  // 3. 登出邏輯
  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    router.push('/login');
  };

  // 4. 資料刷新邏輯
  const refreshUser = async () => {
      try {
          const response = await api.get<User>('/users/me');
          setUser(response.data);
      } catch {
          console.error("無法刷新使用者");
      }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}
