// frontend/src/app/login/page.tsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { isAxiosError } from 'axios';
import { AlertCircle, ArrowRight, BookHeart, LockKeyhole, ShieldCheck } from 'lucide-react';
import { getCurrentUser, login } from '@/services/auth';
import { trackReferralSignup } from '@/services/api-client';
import { useAuth } from '@/hooks/use-auth';
import {
  clearReferralTrackingContext,
  getOrCreateReferralSignupEventId,
  readReferralInviteCode,
} from '@/lib/referral';
import { logClientError } from '@/lib/safe-error-log';
import { EditorialAuthShell } from '@/components/haven/EditorialAuthShell';
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
    <EditorialAuthShell
      panelHeadingId="login-heading"
      panelEyebrow="Returning to your refuge"
      panelTitle="Welcome back to the quiet between you two."
      panelSubtitle="登入後，Haven 會替你續上昨天的心緒、今日的儀式，以及那些值得被柔軟收藏的片刻。"
      storyEyebrow="Invite-only editorial beta"
      storyTitle="讓關係的日常，回到被溫柔設計過的樣子。"
      storyBody="Haven 不是另一個吵雜的訊息流，而是一個留給伴侶兩人的靜奢編輯空間。你寫下的、等待的、回應的，都會以更安靜、更細膩的節奏展開。"
      storyQuote="越重要的關係，越值得被好好排版。"
      storyCredit="Haven Editorial System"
      highlights={[
        {
          value: 'Private',
          label: 'Journal Sanctuary',
          description: '以私密、柔和、低干擾的方式承接你們的日記與情緒。',
        },
        {
          value: 'Ritual',
          label: 'Daily Connection',
          description: '每日共感與牌卡節奏被保留下來，不必被趕著完成。',
        },
        {
          value: 'Calm',
          label: 'Signal Over Noise',
          description: '把真正重要的提醒留在前景，其餘退回背景。',
        },
      ]}
      callout={
        <div className="grid gap-3 rounded-[1.4rem] border border-primary/10 bg-primary/5 p-4 sm:grid-cols-3">
          <div className="flex items-center gap-2 text-sm text-foreground">
            <LockKeyhole className="h-4 w-4 text-primary" aria-hidden />
            邀請制內測
          </div>
          <div className="flex items-center gap-2 text-sm text-foreground">
            <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
            Cookie 安全登入
          </div>
          <div className="flex items-center gap-2 text-sm text-foreground">
            <BookHeart className="h-4 w-4 text-primary" aria-hidden />
            日記與儀式同步
          </div>
        </div>
      }
      footer={
        <p className="text-center">
          還沒有帳號？{' '}
          <Link
            href="/register"
            className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            註冊新帳號
          </Link>
        </p>
      }
    >
      {error && (
        <div
          id="login-error"
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-body text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span className="text-sm leading-relaxed">{error}</span>
        </div>
      )}

      <form
        onSubmit={handleLogin}
        className="space-y-5"
        aria-labelledby="login-heading"
        aria-describedby={error ? 'login-error' : undefined}
      >
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
        <div className="rounded-[1.35rem] border border-white/45 bg-white/65 p-4 text-sm leading-7 text-muted-foreground">
          使用你的內測信箱登入即可回到首頁；若你是透過邀請碼進站，登入後系統會接續完成推薦追蹤與綁定流程。
        </div>
        <div className="pt-1 animate-slide-up-fade-2">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            loading={loading}
            disabled={loading}
            rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
          >
            登入 Haven
          </Button>
        </div>
      </form>
    </EditorialAuthShell>
  );
}
