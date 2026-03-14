// frontend/src/app/login/page.tsx

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { isAxiosError } from 'axios';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  HeartHandshake,
  LockKeyhole,
  Sparkles,
} from 'lucide-react';
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
      panelEyebrow="Return to Haven"
      panelTitle="回到只屬於你們兩個的安靜空間。"
      panelSubtitle="登入不是進入一個工具，而是回到你們共同保留的節奏、對話與記憶。這裡仍然安靜、私密，而且有分寸。"
      storyEyebrow="Private re-entry ritual"
      storyTitle="登入，不該像回到一個後台；而應該像回到你們之間。"
      storyBody="Haven 把登入頁當成重新進入關係節奏的門廊。第一眼先給你安定、溫度與信任，再把你帶回那些尚未說完的話。"
      storyQuote="真正高級的親密介面，不催促，只讓人願意回來。"
      storyCredit="Haven Entry Ritual"
      highlights={[
        {
          value: '01',
          label: 'Private by Default',
          description: '不是公開動態牆，也不是訊息轟炸；你回來的是只屬於兩個人的空間。',
        },
        {
          value: '02',
          label: 'Shared Continuity',
          description: '首頁儀式、牌卡與共同記憶會接回你們上次停下來的位置，而不是重新開始。',
        },
        {
          value: '03',
          label: 'Invite-Only Beta',
          description: '節制開放，讓每一次進場都帶著被妥善對待的感覺，而不是廉價流量入口。',
        },
      ]}
      callout={
        <div className="stack-block">
          {error && (
            <div
              id="login-error"
              role="alert"
              className="flex items-start gap-2.5 rounded-[1.3rem] border border-destructive/20 bg-destructive/5 p-4 text-destructive"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="type-caption leading-relaxed">{error}</span>
            </div>
          )}

          <div className="rounded-[1.45rem] border border-primary/12 bg-primary/6 p-4">
            <p className="type-micro uppercase text-primary/72">登入後會發生什麼</p>
            <ul className="mt-3 space-y-2 type-caption text-foreground">
              <li>1. 回到你們最近一次停下的首頁節奏與共同記錄。</li>
              <li>2. 如果你是透過邀請加入，系統會接著把你帶到對應設定流程。</li>
              <li>3. 所有互動仍維持私密預設，不會突然變成公開或吵雜的介面。</li>
            </ul>
          </div>
        </div>
      }
      footer={
        <div className="stack-block">
          <p className="text-center">
            還沒有帳號？{' '}
            <Link
              href="/register"
              className="font-medium text-primary transition-colors duration-haven ease-haven hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              註冊新帳號
            </Link>
          </p>
          <p className="type-caption text-center text-muted-foreground">
            Haven 目前仍是邀請制 beta。註冊後登入，才會真正進入你們的共享空間。
          </p>
        </div>
      }
    >
      <form
        onSubmit={handleLogin}
        className="stack-section"
        aria-labelledby="login-heading"
        aria-describedby={error ? 'login-error' : undefined}
      >
        <div className="rounded-[1.45rem] border border-white/50 bg-white/68 p-5 shadow-soft animate-slide-up-fade">
          <div className="stack-block">
            <p className="type-micro uppercase text-primary/76">Sign in</p>
            <h3 className="type-section-title text-foreground">使用你受邀加入時設定的 Email 與密碼</h3>
            <p className="type-caption text-muted-foreground">
              如果你剛完成註冊，登入後會直接把你帶回 Haven 的下一步，而不是再把你丟回一個冷冰冰的入口頁。
            </p>
          </div>
        </div>

        <div className="stack-section">
          <div className="animate-slide-up-fade-1">
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              required
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="animate-slide-up-fade-2">
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
        </div>

        <div className="flex flex-wrap gap-2 rounded-[1.35rem] border border-white/45 bg-white/64 p-4 shadow-soft animate-slide-up-fade-3">
          <span className="inline-flex items-center gap-[var(--space-inline)] rounded-full bg-primary/10 px-3 py-1.5 type-caption text-foreground">
            <LockKeyhole className="h-3.5 w-3.5 text-primary" aria-hidden />
            私密預設
          </span>
          <span className="inline-flex items-center gap-[var(--space-inline)] rounded-full bg-accent/12 px-3 py-1.5 type-caption text-foreground">
            <HeartHandshake className="h-3.5 w-3.5 text-primary" aria-hidden />
            雙人共享空間
          </span>
          <span className="inline-flex items-center gap-[var(--space-inline)] rounded-full bg-primary/8 px-3 py-1.5 type-caption text-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-primary" aria-hidden />
            延續上次的節奏
          </span>
        </div>

        <div className="pt-1 animate-slide-up-fade-4">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            loading={loading}
            disabled={loading}
            rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
          >
            登入並回到 Haven
          </Button>
        </div>

        <div className="rounded-[1.35rem] border border-white/45 bg-white/58 p-4 animate-slide-up-fade-5">
          <div className="stack-inline items-start">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
            <p className="type-caption text-muted-foreground">
              這裡只處理回到 Haven 所需要的最少步驟。登入成功後，系統會把你帶回真正重要的內容，而不是讓你停留在驗證本身。
            </p>
          </div>
        </div>
      </form>
    </EditorialAuthShell>
  );
}
