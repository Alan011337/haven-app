// frontend/src/app/login/page.js

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link'; 
import { isAxiosError } from 'axios';
import { login } from '@/services/auth'; 

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await login(email, password);

      // 儲存 Token
      localStorage.setItem('token', data.access_token);

      // 成功訊息
      router.push('/'); // 跳轉回首頁

    } catch (err) {
      console.error('登入失敗:', err);
      if (isAxiosError(err) && (err.response?.status === 400 || err.response?.status === 401)) {
        setError('帳號或密碼錯誤');
      } else {
        setError('連線錯誤，請檢查後端是否已啟動');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-md bg-white p-8 shadow-lg rounded-xl border border-gray-100">
        <h1 className="mb-6 text-2xl font-bold text-center text-gray-800">登入 Haven</h1>
        
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              // 👇 加入這行，忽略擴充功能造成的屬性差異
              suppressHydrationWarning
              required
              className="block w-full rounded-lg border border-gray-300 p-2.5 shadow-sm focus:border-purple-500 focus:ring-purple-500 outline-none transition-all"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密碼</label>
            <input
              type="password"
              // 👇 加入這行
              suppressHydrationWarning
              required
              className="block w-full rounded-lg border border-gray-300 p-2.5 shadow-sm focus:border-purple-500 focus:ring-purple-500 outline-none transition-all"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-md text-sm font-medium text-white transition-colors
              ${loading ? 'bg-purple-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'}`}
          >
            {loading ? '登入中...' : '登入'}
          </button>
        </form>
        
        <div className="mt-6 text-center text-sm text-gray-600">
          還沒有帳號？{' '}
          <Link href="/register" className="font-medium text-purple-600 hover:text-purple-500 hover:underline">
            註冊新帳號
          </Link>
        </div>
      </div>
    </div>
  );
}
