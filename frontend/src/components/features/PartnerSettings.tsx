// frontend/src/components/features/PartnerSettings.tsx

"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { isAxiosError } from 'axios';
import { useRouter } from 'next/navigation';
import { Heart, Link2, Copy, Check, Sparkles, Loader2, ArrowRight, Smartphone, QrCode } from 'lucide-react';
import { logClientError } from '@/lib/safe-error-log';
import { createReferralCoupleInviteEventId, buildReferralInviteUrl } from '@/lib/referral';
import { trackReferralCoupleInvite } from '@/services/api-client';
import { fetchUserMe, generateInviteCode, pairWithPartner } from '@/services/user';
import { useToast } from '@/hooks/useToast';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

interface UserData {
  id: string;
  email: string;
  partner_id?: string;
  partner_name?: string; 
  invite_code?: string;
}

export default function PartnerSettings() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [inviteCode, setInviteCode] = useState('');
  const [inputCode, setInputCode] = useState('');
  const [binding, setBinding] = useState(false);
  const [copied, setCopied] = useState(false);
  const { showToast } = useToast();

  // --- 1. 取得使用者資料 ---
  const fetchUser = useCallback(async () => {
    try {
      const me = await fetchUserMe();
      setUser(me);
      // /users/me 未必回傳 invite_code；避免把 user id 當邀請碼顯示。
      setInviteCode(me.invite_code || '');
    } catch (e) {
      logClientError('partner-settings-fetch-user-failed', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // --- 2. 產生邀請碼 ---
  const handleGenerate = async () => {
    try {
      const result = await generateInviteCode();
      setInviteCode(result.code);
    } catch (error) {
      logClientError('partner-settings-generate-invite-failed', error);
      showToast("產生失敗，請稍後再試", 'error');
    }
  };

  // --- 3. 綁定伴侶 ---
  const handleBind = async () => {
    if(!inputCode) return;
    setBinding(true);
    try {
      await pairWithPartner(inputCode);
      await fetchUser(); 
      showToast("綁定成功！", 'success');
    } catch (error) {
      logClientError('partner-settings-bind-failed', error);
      if (isAxiosError(error) && error.response?.status === 409) {
        showToast(error.response.data?.detail || "綁定狀態衝突，請稍後再試。", 'error');
      } else if (isAxiosError(error) && error.response?.status === 400) {
        showToast("綁定失敗，邀請碼不存在或已失效。", 'error');
      } else {
        showToast("綁定失敗，請確認代碼是否正確或過期", 'error');
      }
    } finally {
      setBinding(false);
    }
  };

  // --- 4. 複製到剪貼簿 ---
  const copyToClipboard = async () => {
    if (!inviteCode) return;
    const inviteUrl = buildReferralInviteUrl(
      inviteCode,
      typeof window !== 'undefined' ? window.location.origin : null,
    );
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      showToast("邀請連結已複製", 'info');
      setTimeout(() => setCopied(false), 2000);

      try {
        await trackReferralCoupleInvite({
          invite_code: inviteCode,
          event_id: createReferralCoupleInviteEventId(),
          source: 'partner_settings',
          share_channel: 'link_copy',
          landing_path: '/register',
        });
      } catch (trackingError) {
        logClientError('referral-couple-invite-track-failed', trackingError);
      }
    } catch (error) {
      logClientError('partner-settings-copy-invite-failed', error);
      showToast("複製失敗，請稍後再試", 'error');
    }
  };

  // 取得姓名首字
  const getInitial = (name?: string) => name ? name.charAt(0).toUpperCase() : "?";

  if (loading) return <div className="p-12 flex justify-center"><div className="relative"><div className="absolute inset-0 bg-primary/10 rounded-full blur-xl animate-breathe" aria-hidden /><Loader2 className="animate-spin text-primary w-8 h-8 relative z-10" aria-hidden /></div></div>;

  return (
    <section className="relative overflow-hidden rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8">
      <p className="mb-6 text-sm leading-relaxed text-muted-foreground">
        連結彼此的帳號，讓 AI 成為你們關係的橋樑，在專屬於你們的雲端日記中相遇。
      </p>

      <div className="relative">
          
          {user?.partner_id ? (
            // ==========================
            // === 情境 A: 已連結狀態 ===
            // ==========================
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-700">
              
              <div className="flex items-center justify-center gap-8 mb-10 relative w-full max-w-md">
                <div className="flex flex-col items-center gap-3 relative z-10">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-muted to-muted/60 border-4 border-card shadow-soft shadow-glass-inset flex items-center justify-center">
                    <span className="text-3xl font-art font-black text-foreground">{getInitial(user.email)}</span>
                  </div>
                  <span className="text-xs font-bold text-muted-foreground tracking-widest uppercase bg-muted px-3 py-1 rounded-full">You</span>
                </div>
                <div className="flex-1 h-[3px] bg-border relative mx-2 rounded-full overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-foreground/10 to-transparent w-full -translate-x-full animate-[shimmer_2s_infinite]" aria-hidden />
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 bg-card rounded-full border-4 border-primary/20 shadow-soft flex items-center justify-center z-20">
                    <Heart className="w-6 h-6 text-primary fill-primary animate-[pulse_3s_ease-in-out_infinite]" aria-hidden />
                  </div>
                </div>
                <div className="flex flex-col items-center gap-3 relative z-10">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary/15 to-primary/5 border-4 border-card shadow-soft shadow-glass-inset flex items-center justify-center">
                    <span className="text-3xl font-art font-black text-primary">{getInitial(user.partner_name)}</span>
                  </div>
                  <span className="text-xs font-bold text-primary tracking-widest uppercase bg-primary/10 px-3 py-1 rounded-full">Partner</span>
                </div>
              </div>

              <div className="text-center space-y-3">
                <h3 className="text-3xl font-art font-bold text-foreground tracking-tight">
                  已與 <span className="text-primary">{user.partner_name || '伴侶'}</span> 連結
                </h3>
                <div className="flex justify-center">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/20 text-accent text-sm font-bold border border-border shadow-soft">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" aria-hidden />
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent" aria-hidden />
                    </span>
                    關係狀態：活躍中
                  </div>
                </div>

                {/* 按鈕：跳轉到伴侶日記頁面 */}
                <div className="pt-8">
                    <Button
                        size="lg"
                        variant="primary"
                        rightIcon={<ArrowRight className="w-5 h-5" aria-hidden />}
                        onClick={() => router.push('/?tab=partner')}
                        className="px-10 py-4"
                    >
                        去看看對方的日記
                    </Button>
                </div>
              </div>
            </div>
          ) : (
            // ==========================
            // === 情境 B: 未連結狀態 ===
            // ==========================
            <div className="space-y-10 animate-in slide-in-from-bottom-4 duration-500">
               <div className="text-center">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/12 to-primary/4 border border-primary/8 flex items-center justify-center mx-auto mb-6 shadow-soft">
                    <Link2 className="text-primary w-10 h-10" aria-hidden />
                  </div>
                  <h3 className="text-2xl font-art font-bold text-foreground mb-2">尚未連結伴侶</h3>
                  <p className="text-muted-foreground">請產生邀請碼給對方，或是輸入對方的代碼。</p>
               </div>

               <div className="grid md:grid-cols-2 gap-8 relative z-10">
                  <div className="bg-card p-8 rounded-card border border-border flex flex-col justify-between shadow-soft hover:shadow-lift transition-shadow duration-haven ease-haven relative overflow-hidden animate-slide-up-fade">
                    <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
                    <div>
                        <div className="flex items-center gap-2 mb-4">
                           <span className="icon-badge" aria-hidden><QrCode className="w-4 h-4" /></span>
                           <span className="text-xs font-bold text-primary uppercase tracking-widest">你的邀請碼</span>
                        </div>
                        <div className="flex gap-2 mb-6">
                            <code className="flex-1 bg-background border-2 border-input p-4 rounded-input text-xl font-mono text-foreground text-center font-bold tracking-widest">
                                {inviteCode || "------"}
                            </code>
                            <button
                                type="button"
                                onClick={copyToClipboard}
                                disabled={!inviteCode}
                                aria-label="複製邀請碼"
                                className="px-4 bg-background border-2 border-input rounded-input hover:bg-muted transition-all duration-haven-fast ease-haven text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                {copied ? <Check size={20} className="text-primary" aria-hidden /> : <Copy size={20} aria-hidden />}
                            </button>
                        </div>
                    </div>
                    <Button
                        variant="secondary"
                        size="md"
                        leftIcon={<Sparkles size={16} />}
                        onClick={handleGenerate}
                        className="w-full"
                    >
                        產生新代碼
                    </Button>
                  </div>

                  <div className="bg-card p-8 rounded-card border border-border shadow-soft hover:shadow-lift transition-shadow duration-haven ease-haven relative overflow-hidden animate-slide-up-fade-1">
                    <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-accent/25 to-transparent" aria-hidden />
                    <div className="flex items-center gap-2 mb-4">
                       <span className="icon-badge !bg-gradient-to-br !from-accent/12 !to-accent/4 !border-accent/8" aria-hidden><Smartphone className="w-4 h-4 text-accent" /></span>
                       <label htmlFor="partner-code-input" className="text-xs font-bold text-accent uppercase tracking-widest">輸入伴侶代碼</label>
                    </div>

                    <div className="space-y-4">
                      <Input
                        id="partner-code-input"
                        type="text"
                        value={inputCode}
                        onChange={(e) => setInputCode(e.target.value.toUpperCase())}
                        placeholder="在此輸入 6 碼"
                        maxLength={6}
                        className="text-lg font-mono text-center uppercase"
                      />
                      <Button
                        variant="primary"
                        size="lg"
                        className="w-full"
                        loading={binding}
                        disabled={binding || inputCode.length < 6}
                        leftIcon={!binding ? <Link2 className="w-5 h-5" /> : undefined}
                        onClick={handleBind}
                      >
                        確認綁定
                      </Button>
                    </div>
                  </div>
               </div>
            </div>
          )}
      </div>
    </section>
  );
}
