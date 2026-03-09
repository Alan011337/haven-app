// frontend/src/app/register/page.tsx
"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { isAxiosError } from 'axios';
import { AlertCircle, Gift, Heart } from 'lucide-react';
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
import { GlassCard } from '@/components/haven/GlassCard';
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
    <div className="relative flex min-h-screen flex-col items-center justify-center space-page bg-auth-gradient overflow-hidden">
      {/* Decorative floating orbs */}
      <div className="absolute top-16 right-[20%] w-64 h-64 rounded-full bg-primary/8 blur-hero-orb animate-float pointer-events-none" aria-hidden />
      <div className="absolute bottom-24 left-[12%] w-48 h-48 rounded-full bg-accent/10 blur-hero-orb-sm animate-float-delayed pointer-events-none" aria-hidden />

      <div className="relative z-10 w-full max-w-md animate-scale-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-3xl bg-gradient-to-br from-primary to-primary/80 shadow-lift shadow-glass-inset mb-5 relative">
            <div className="absolute inset-0 bg-primary/20 rounded-3xl blur-xl animate-breathe" aria-hidden />
            <Heart className="w-7 h-7 text-primary-foreground fill-primary-foreground relative" />
          </div>
          <h1 id="register-heading" className="text-3xl font-art font-bold text-gradient-gold mb-2 animate-slide-up-fade">Join Haven</h1>
          <p className="text-caption text-muted-foreground font-light">建立帳號，開始你的心靈旅程</p>
        </div>

        <GlassCard className="w-full p-8 md:p-10 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" aria-hidden />
          {error && (
            <div id="register-error" role="alert" className="mb-5 flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-body text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="text-sm leading-relaxed">{error}</span>
            </div>
          )}

          {referralInviteCode && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-primary/20 bg-primary/5 p-4 text-body text-foreground">
              <Gift className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
              <span className="text-sm leading-relaxed">
                已偵測邀請碼：<span className="font-semibold text-primary">{referralInviteCode}</span>
                。完成註冊並登入後，系統會自動記錄推薦來源。
              </span>
            </div>
          )}

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

            <div className="flex items-start gap-3 animate-slide-up-fade-3">
              <input
                id="agree-terms"
                type="checkbox"
                checked={formData.agreedToTerms}
                onChange={(e) => setFormData({ ...formData, agreedToTerms: e.target.checked })}
                className="mt-1 h-4 w-4 rounded border-input text-primary accent-primary focus-visible:ring-ring transition-colors duration-haven-fast ease-haven"
              />
              <label htmlFor="agree-terms" className="text-sm text-muted-foreground leading-relaxed">
                我已滿 18 歲，並同意{' '}
                <Link href="/legal/terms" target="_blank" rel="noopener noreferrer" className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                  服務條款
                </Link>
                {' '}與{' '}
                <Link href="/legal/privacy" target="_blank" rel="noopener noreferrer" className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                  隱私權政策
                </Link>
                。
              </label>
            </div>

            <div className="pt-1">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                loading={loading}
                disabled={loading || !formData.agreedToTerms}
              >
                註冊帳號
              </Button>
            </div>
          </form>

          <div className="mt-8 text-center text-sm text-muted-foreground">
            <div className="section-divider mb-6" />
            已經有帳號了嗎？{' '}
            <Link href="/login" className="font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
              登入
            </Link>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
