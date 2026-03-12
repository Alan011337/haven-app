// frontend/src/app/register/page.tsx
"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { isAxiosError } from 'axios';
import { AlertCircle, ArrowRight, CheckCircle2, Gift, HeartHandshake, LockKeyhole } from 'lucide-react';
import { trackBindStart, trackBindSuccess } from '@/lib/cuj-events';
import { register } from '@/services/auth';
import { trackReferralLandingView } from '@/services/api-client';
import { useToast } from '@/hooks/useToast';
import {
  getOrCreateReferralLandingEventId,
  normalizeInviteCode,
  rememberReferralInviteCode,
} from '@/lib/referral';
import { logClientError } from '@/lib/safe-error-log';
import { EditorialAuthShell } from '@/components/haven/EditorialAuthShell';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    fullName: '',
    agreedToTerms: false,
  });
  const [referralInviteCode, setReferralInviteCode] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const currentSearchParams = new URLSearchParams(window.location.search);
    const inviteParam =
      currentSearchParams.get('invite') ||
      currentSearchParams.get('invite_code') ||
      currentSearchParams.get('ref');
    const normalized = normalizeInviteCode(inviteParam);
    if (!normalized) return;

    setReferralInviteCode(normalized);
    rememberReferralInviteCode(normalized);

    const eventId = getOrCreateReferralLandingEventId();
    void trackReferralLandingView({
      invite_code: normalized,
      event_id: eventId,
      source: 'register_page',
      landing_path: '/register',
    }).catch((trackError) => {
      logClientError('referral-landing-track-failed', trackError);
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (formData.password.length < 8) {
      setError('密碼至少需要 8 個字元');
      return;
    }
    if (!formData.agreedToTerms) {
      setError('請確認您已滿 18 歲並同意服務條款與隱私權政策');
      return;
    }
    setLoading(true);
    trackBindStart();

    try {
      await register(
        formData.email,
        formData.password,
        formData.fullName,
        formData.agreedToTerms,
        'v1.0',
        'v1.0',
      );
      
      trackBindSuccess();
      showToast('註冊成功！請登入', 'success');
      router.push('/login');
    } catch (error: unknown) {
      logClientError('register-failed', error);
      if (isAxiosError(error)) {
        const status = error.response?.status;
        if (status === 403) {
          setError('邀請制內測：目前僅開放受邀測試者。');
        } else if (status === 400 || status === 409) {
          setError('這個 Email 已經被註冊過了');
        } else if (status === 422) {
          const detail = error.response?.data?.detail;
          if (typeof detail === 'string') {
            setError(detail);
          } else {
            setError('輸入格式有誤，請檢查欄位內容');
          }
        } else if (status === 429) {
          setError('操作過於頻繁，請稍後再試');
        } else {
          setError('註冊失敗，請稍後再試');
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
      panelHeadingId="register-heading"
      panelEyebrow="Create your editorial sanctuary"
      panelTitle="為你們建立一個更有呼吸感的親密空間。"
      panelSubtitle="註冊完成後，你可以開始記錄雙方的日常、每日共感與牌卡儀式。Haven 會把重要的互動留下，把噪音移開。"
      storyEyebrow="Curated onboarding"
      storyTitle="精品感，不只是外觀，而是關係被對待的方式。"
      storyBody="從第一封邀請開始，Haven 就把伴侶互動當成值得被設計、被整理、被尊重的素材。這不是加速器，而是一個讓關係慢慢發亮的版面系統。"
      storyQuote="好的關係介面，應該讓人更想靠近，而不是更快耗盡。"
      storyCredit="Haven Couple OS"
      highlights={[
        {
          value: '01',
          label: 'Invite Layer',
          description: '維持邀請制 beta，讓每段關係都在安靜的節奏裡進場。',
        },
        {
          value: '02',
          label: 'Shared Memory',
          description: '日記、牌卡與地圖不是碎片，而是同一條記憶敘事線。',
        },
        {
          value: '03',
          label: 'Soft Guardrails',
          description: '條款、年齡與推薦流程都被清楚收束，不打擾但不省略。',
        },
      ]}
      callout={
        <>
          {error && (
            <div
              id="register-error"
              role="alert"
              className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-body text-destructive"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="text-sm leading-relaxed">{error}</span>
            </div>
          )}

          {referralInviteCode && (
            <div className="flex items-start gap-2.5 rounded-xl border border-primary/20 bg-primary/5 p-4 text-body text-foreground">
              <Gift className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
              <span className="text-sm leading-relaxed">
                已偵測邀請碼：<span className="font-semibold text-primary">{referralInviteCode}</span>
                。完成註冊並登入後，系統會自動記錄推薦來源。
              </span>
            </div>
          )}
        </>
      }
      footer={
        <p className="text-center">
          已經有帳號了嗎？{' '}
          <Link
            href="/login"
            className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            登入
          </Link>
        </p>
      }
    >
      <form
        onSubmit={handleSubmit}
        className="space-y-5"
        aria-labelledby="register-heading"
        aria-describedby={error ? 'register-error' : undefined}
      >
        <div className="animate-slide-up-fade">
          <Input
            label="暱稱 / 姓名"
            type="text"
            required
            placeholder="你想怎麼被稱呼？"
            value={formData.fullName}
            onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
          />
        </div>
        <div className="animate-slide-up-fade-1">
          <Input
            label="Email"
            type="email"
            required
            placeholder="name@example.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />
        </div>
        <div className="animate-slide-up-fade-2">
          <Input
            label="密碼"
            type="password"
            required
            minLength={8}
            maxLength={128}
            placeholder="至少 8 個字元"
            helperText="密碼至少需要 8 個字元"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          />
        </div>

        <div className="rounded-[1.4rem] border border-white/45 bg-white/65 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm text-foreground">
            <HeartHandshake className="h-4 w-4 text-primary" aria-hidden />
            註冊前確認
          </div>
          <div className="flex items-start gap-3">
            <input
              id="agree-terms"
              type="checkbox"
              checked={formData.agreedToTerms}
              onChange={(e) => setFormData({ ...formData, agreedToTerms: e.target.checked })}
              className="mt-1 h-4 w-4 rounded border-input text-primary accent-primary focus-visible:ring-ring transition-colors duration-haven-fast ease-haven"
            />
            <label htmlFor="agree-terms" className="text-sm leading-relaxed text-muted-foreground">
              我已滿 18 歲，並同意{' '}
              <Link
                href="/legal/terms"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                服務條款
              </Link>
              {' '}與{' '}
              <Link
                href="/legal/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                隱私權政策
              </Link>
              。
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-xs text-primary">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
              Invite-only beta
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/12 px-3 py-1 text-xs text-accent-foreground">
              <LockKeyhole className="h-3.5 w-3.5" aria-hidden />
              資料與會話保護
            </span>
          </div>
        </div>

        <div className="pt-1">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            loading={loading}
            disabled={loading || !formData.agreedToTerms}
            rightIcon={<ArrowRight className="h-4 w-4" aria-hidden />}
          >
            註冊帳號
          </Button>
        </div>
      </form>
    </EditorialAuthShell>
  );
}
