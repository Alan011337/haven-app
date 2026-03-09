'use client';

import { AlertTriangle, PhoneCall, X } from 'lucide-react';

interface PartnerSafetyBannerProps {
  severeCount: number;
  onDismiss: () => void;
}

export default function PartnerSafetyBanner({ severeCount, onDismiss }: PartnerSafetyBannerProps) {
  const countLabel = severeCount > 1 ? `${severeCount} 則` : '一則';

  return (
    <div className="relative mb-6 overflow-hidden rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50 to-white p-4 shadow-sm">
      <div className="absolute right-0 top-0 h-20 w-20 translate-x-1/3 -translate-y-1/3 rounded-full bg-rose-100/80 blur-2xl" />

      <button
        type="button"
        onClick={onDismiss}
        className="absolute right-3 top-3 rounded-full border border-rose-200 bg-white/90 p-1 text-rose-500 transition-colors hover:bg-rose-100"
        aria-label="關閉安全提示"
      >
        <X className="h-4 w-4" />
      </button>

      <div className="relative flex items-start gap-3 pr-10">
        <div className="mt-0.5 rounded-xl bg-rose-100 p-2 text-rose-600">
          <AlertTriangle className="h-5 w-5" />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-bold text-rose-700">安全提示：先確認彼此狀態</p>
          <p className="text-sm leading-relaxed text-rose-700/90">
            目前有 {countLabel} 伴侶日記屬於高風險情緒。建議先降低刺激、確認安全，再進行深度溝通。
          </p>

          <div className="flex flex-wrap gap-2 pt-1">
            <a
              href="tel:1925"
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-bold text-rose-700 hover:bg-rose-100 transition-colors"
            >
              <PhoneCall className="h-3.5 w-3.5" />
              安心專線 1925
            </a>
            <a
              href="tel:113"
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-700 hover:bg-amber-100 transition-colors"
            >
              <PhoneCall className="h-3.5 w-3.5" />
              保護專線 113
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
