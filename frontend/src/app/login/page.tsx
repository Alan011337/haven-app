// frontend/src/app/login/page.tsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { isAxiosError } from 'axios';
import { AlertCircle, Heart } from 'lucide-react';
import { getCurrentUser, login } from '@/services/auth';
import { trackReferralSignup } from '@/services/api-client';
import { useAuth } from '@/hooks/use-auth';
import {
  clearReferralTrackingContext,
  getOrCreateReferralSignupEventId,
  readReferralInviteCode,
} from '@/lib/referral';
import { logClientError } from '@/lib/safe-error-log';
import { GlassCard } from '@/components/haven/GlassCard';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

export default function LoginPage() {
  const { login: loginWithContext } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await login(email, password);

      try {
        // ✅ 令牌由後端通過 httpOnly Cookie 設置
        // 前端只需驗證用戶信息
        const userData = await getCurrentUser(data.access_token);
        const referralInviteCode = readReferralInviteCode();
        const postLoginRedirect = referralInviteCode ? '/settings' : '/';
        if (referralInviteCode) {
          try {
            await trackReferralSignup({
              invite_code: referralInviteCode,
              event_id: getOrCreateReferralSignupEventId(),
              source: 'login_page',
            });
            clearReferralTrackingContext();
          } catch (referralError) {
            logClientError('referral-signup-track-failed', referralError);
          }
        }
        // loginWithContext 不再需要傳遞 token（由 Cookie 管理）
        loginWithContext(data.access_token, userData, postLoginRedirect);
      } catch (profileError) {
        logClientError('login-profile-load-failed', profileError);
        setError('登入成功，但讀取使用者資料失敗，請再試一次');
      }

    } catch (err) {
      logClientError('login-failed', err);
      if (isAxiosError(err)) {
        const status = err.response?.status;
        const isNetworkError = err.code === 'ERR_NETWORK' || !err.response;
        if (isNetworkError) {
          setError('無法連線至伺服器，請確認後端 API 已啟動（例如在 backend 目錄執行 uvicorn app.main:app --reload）');
        } else if (status === 403) {
          setError('邀請制內測：目前僅開放受邀測試者。');
        } else if (status === 400 || status === 401) {
          setError('帳號或密碼錯誤');
        } else if (status === 429) {
          setError('登入嘗試次數過多，請稍後再試');
        } else if (status === 422) {
          setError('輸入格式有誤，請檢查 Email 與密碼');
        } else {
          setError('連線錯誤，請稍後再試');
        }
      } else {
        setError('連線錯誤，請檢查網路連線');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center space-page bg-auth-gradient overflow-hidden">
      {/* Decorative floating orbs */}
      <div className="absolute top-20 left-[15%] w-72 h-72 rounded-full bg-primary/8 blur-hero-orb animate-float pointer-events-none" aria-hidden />
      <div className="absolute bottom-32 right-[10%] w-56 h-56 rounded-full bg-accent/10 blur-hero-orb-sm animate-float-delayed pointer-events-none" aria-hidden />
      <div className="absolute top-1/2 left-[60%] w-40 h-40 rounded-full bg-primary/5 blur-hero-orb-sm animate-float-slow pointer-events-none" aria-hidden />

      <div className="relative z-10 w-full max-w-md animate-scale-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-3xl bg-gradient-to-br from-primary to-primary/80 shadow-lift shadow-glass-inset mb-5 relative">
            <div className="absolute inset-0 bg-primary/20 rounded-3xl blur-xl animate-breathe" aria-hidden />
            <Heart className="w-7 h-7 text-primary-foreground fill-primary-foreground relative" />
          </div>
          <h1 id="login-heading" className="text-3xl font-art font-bold text-gradient-gold mb-2 animate-slide-up-fade">Welcome Back</h1>
          <p className="text-caption text-muted-foreground font-light">回到你的心靈避風港</p>
        </div>

        <GlassCard className="w-full p-8 md:p-10 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
          {error && (
            <div id="login-error" role="alert" className="mb-5 flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-body text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="text-sm leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5" aria-labelledby="login-heading" aria-describedby={error ? 'login-error' : undefined}>
            <div className="animate-slide-up-fade">
              <Input
                label="Email"
                type="email"
                autoComplete="email"
                required
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="animate-slide-up-fade-1">
              <Input
                label="密碼"
                type="password"
                autoComplete="current-password"
                required
                placeholder="請輸入密碼"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="pt-2 animate-slide-up-fade-2">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                loading={loading}
                disabled={loading}
              >
                登入
              </Button>
            </div>
          </form>

          <div className="mt-8 text-center text-sm text-muted-foreground">
            <div className="section-divider mb-6" />
            還沒有帳號？{' '}
            <Link href="/register" className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
              註冊新帳號
            </Link>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
