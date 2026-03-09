'use client';

import { AlertTriangle, PhoneCall, X } from 'lucide-react';

interface PartnerSafetyBannerProps {
  severeCount: number;
  onDismiss: () => void;
}

export default function PartnerSafetyBanner({ severeCount, onDismiss }: PartnerSafetyBannerProps) {
  const countLabel = severeCount > 1 ? `${severeCount} 則` : '一則';

  return (
    <div className="relative mb-6 overflow-hidden rounded-card border border-border bg-destructive/5 p-4 shadow-soft">
      <div className="absolute right-0 top-0 h-20 w-20 translate-x-1/3 -translate-y-1/3 rounded-full bg-destructive/10 blur-2xl" aria-hidden />

      <button
        type="button"
        onClick={onDismiss}
        className="absolute right-3 top-3 rounded-full border border-border bg-card/90 p-1 text-destructive transition-colors duration-haven-fast ease-haven hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="關閉安全提示"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>

      <div className="relative flex items-start gap-3 pr-10">
        <span className="icon-badge !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8 mt-0.5" aria-hidden>
          <AlertTriangle className="h-4 w-4 text-destructive" />
        </span>

        <div className="space-y-2">
          <p className="text-sm font-art font-bold text-destructive">安全提示：先確認彼此狀態</p>
          <p className="text-sm leading-relaxed text-foreground">
            目前有 {countLabel} 伴侶日記屬於高風險情緒。建議先降低刺激、確認安全，再進行深度溝通。
          </p>

          <div className="flex flex-wrap gap-2 pt-1">
            <a
              href="tel:1925"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <PhoneCall className="h-3.5 w-3.5" aria-hidden />
              安心專線 1925
            </a>
            <a
              href="tel:113"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <PhoneCall className="h-3.5 w-3.5" aria-hidden />
              保護專線 113
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
