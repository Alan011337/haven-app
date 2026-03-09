// frontend/src/components/features/SafetyTierGate.tsx

'use client';

import { useCallback, useState } from 'react';
import { AlertTriangle, Eye, PhoneCall, ShieldAlert } from 'lucide-react';
import { resolveSafetyTierBehavior, CRISIS_HOTLINES } from '@/lib/safety-policy';
import ForceLockBanner from './ForceLockBanner';

interface SafetyTierGateProps {
  tier: number;
  children: React.ReactNode;
}

export default function SafetyTierGate({ tier, children }: SafetyTierGateProps) {
  const behavior = resolveSafetyTierBehavior(tier);
  const [revealed, setRevealed] = useState(false);

  const handleReveal = useCallback(() => {
    setRevealed(true);
  }, []);

  // Tier 0: normal — render children directly
  if (behavior.partnerJournalBehavior === 'normal') {
    return <>{children}</>;
  }

  // Tier 1: nudge — show a gentle banner above children
  if (behavior.partnerJournalBehavior === 'nudge') {
    return (
      <>
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-border bg-primary/10 p-3">
          <span className="icon-badge mt-0.5" aria-hidden>
            <AlertTriangle className="h-3.5 w-3.5" />
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">
              溫馨提醒
            </p>
            <p className="text-sm text-muted-foreground mt-0.5">
              伴侶目前可能正在經歷情緒波動，閱讀時請保持同理與耐心。
            </p>
          </div>
        </div>
        {children}
      </>
    );
  }

  // Tier 2: hide_with_cooldown — hide content behind a tap-to-reveal
  if (behavior.partnerJournalBehavior === 'hide_with_cooldown') {
    if (revealed) {
      return (
        <>
          <div className="mb-4 flex items-start gap-3 rounded-xl border border-border bg-destructive/10 p-3">
            <div className="mt-0.5 rounded-lg bg-destructive/15 p-1.5 text-destructive">
              <ShieldAlert className="h-4 w-4" aria-hidden />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-destructive">
                安全提醒
              </p>
              <p className="text-sm text-foreground mt-0.5 mb-2">
                以下內容包含高敏感情緒訊號。請優先確認伴侶的身心安全。
              </p>
              <div className="flex flex-wrap gap-2">
                {CRISIS_HOTLINES.map((hotline) => (
                  <a
                    key={hotline.number}
                    href={hotline.href}
                    className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1 text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  >
                    <PhoneCall className="h-3 w-3" aria-hidden />
                    {hotline.name} {hotline.number}
                  </a>
                ))}
              </div>
            </div>
          </div>
          {children}
        </>
      );
    }

    return (
      <div className="rounded-card border border-border bg-destructive/5 p-6">
        <div className="flex items-center gap-3 mb-3">
          <span className="icon-badge !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden>
            <ShieldAlert className="h-4 w-4 text-destructive" />
          </span>
          <h3 className="text-sm font-art font-bold text-destructive">安全優先：內容暫時隱藏</h3>
        </div>
        <p className="text-sm text-foreground leading-relaxed mb-4">
          系統偵測到敏感的情緒訊號。在查看前，請先確認你與伴侶的安全狀態。
          如有緊急狀況，請撥打以下專線。
        </p>
        <div className="flex flex-wrap gap-2 mb-4">
          {CRISIS_HOTLINES.map((hotline) => (
            <a
              key={hotline.number}
              href={hotline.href}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <PhoneCall className="h-3.5 w-3.5" aria-hidden />
              {hotline.name} {hotline.number}
            </a>
          ))}
        </div>
        <button
          type="button"
          onClick={handleReveal}
          className="inline-flex items-center gap-2 rounded-xl bg-destructive px-4 py-2.5 text-sm font-bold text-destructive-foreground shadow-soft hover:shadow-lift active:scale-95 transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <Eye className="h-4 w-4" aria-hidden />
          我已確認安全，查看內容
        </button>
      </div>
    );
  }

  // Tier 3: force_lock — force lock with 30s countdown
  if (revealed) {
    return (
      <>
        <div className="mb-4 flex items-start gap-3 rounded-xl border-2 border-destructive/30 bg-destructive/10 p-3">
          <div className="mt-0.5 rounded-lg bg-destructive/15 p-1.5 text-destructive">
            <ShieldAlert className="h-4 w-4" aria-hidden />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold text-destructive">
              高風險內容
            </p>
            <p className="text-sm text-foreground mt-0.5 mb-2">
              此內容涉及嚴重風險訊號。請務必優先確認安全。
            </p>
            <div className="flex flex-wrap gap-2">
              {CRISIS_HOTLINES.map((hotline) => (
                <a
                  key={hotline.number}
                  href={hotline.href}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1 text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <PhoneCall className="h-3 w-3" aria-hidden />
                  {hotline.name} {hotline.number}
                </a>
              ))}
            </div>
          </div>
        </div>
        {children}
      </>
    );
  }

  return <ForceLockBanner onUnlock={handleReveal} cooldownSeconds={30} />;
}
