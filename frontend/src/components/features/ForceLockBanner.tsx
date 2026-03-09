// frontend/src/components/features/ForceLockBanner.tsx

'use client';

import { useCallback, useEffect, useState } from 'react';
import { ShieldAlert, PhoneCall, Lock, Unlock } from 'lucide-react';
import { CRISIS_HOTLINES } from '@/lib/safety-policy';

interface ForceLockBannerProps {
  onUnlock: () => void;
  cooldownSeconds?: number;
}

export default function ForceLockBanner({
  onUnlock,
  cooldownSeconds = 30,
}: ForceLockBannerProps) {
  const [remaining, setRemaining] = useState(cooldownSeconds);
  const [unlocked, setUnlocked] = useState(false);

  useEffect(() => {
    if (remaining <= 0) return;
    const timer = setInterval(() => {
      setRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [remaining]);

  const handleUnlock = useCallback(() => {
    if (remaining > 0) return;
    setUnlocked(true);
    onUnlock();
  }, [remaining, onUnlock]);

  if (unlocked) return null;

  return (
    <div className="rounded-card border-2 border-destructive/30 bg-destructive/5 p-6 shadow-soft">
      <div className="flex items-center gap-3 mb-4">
        <span className="icon-badge !w-11 !h-11 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden>
          <ShieldAlert className="h-5 w-5 text-destructive" />
        </span>
        <div>
          <h3 className="text-base font-art font-bold text-destructive">
            安全優先模式：內容已鎖定
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            系統偵測到嚴重的情緒風險訊號
          </p>
        </div>
      </div>

      <p className="text-sm text-foreground leading-relaxed mb-4">
        目前內容涉及高風險情緒。在查看前，請先確認你與伴侶的身心安全。
        如有緊急狀況，請立即撥打以下專線。
      </p>

      <div className="flex flex-wrap gap-2 mb-5">
        {CRISIS_HOTLINES.map((hotline) => (
          <a
            key={hotline.number}
            href={hotline.href}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-sm font-bold text-destructive hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <PhoneCall className="h-4 w-4" aria-hidden />
            {hotline.name} {hotline.number}
          </a>
        ))}
      </div>

      <button
        type="button"
        onClick={handleUnlock}
        disabled={remaining > 0}
        className={`
          w-full flex items-center justify-center gap-2 rounded-xl px-4 py-3
          text-sm font-bold transition-all duration-haven ease-haven
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background
          ${remaining > 0
            ? 'bg-muted text-muted-foreground cursor-not-allowed border border-border'
            : 'bg-destructive text-destructive-foreground hover:shadow-lift active:scale-95 shadow-soft'
          }
        `}
      >
        {remaining > 0 ? (
          <>
            <Lock className="h-4 w-4" aria-hidden />
            請等待 <span className="tabular-nums">{remaining}</span> 秒後才能查看
          </>
        ) : (
          <>
            <Unlock className="h-4 w-4" aria-hidden />
            我已確認安全，查看內容
          </>
        )}
      </button>
    </div>
  );
}
