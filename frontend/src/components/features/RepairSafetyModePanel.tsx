'use client';

import { PhoneCall, ShieldAlert } from 'lucide-react';
import { CRISIS_HOTLINES } from '@/lib/safety-policy';

interface RepairSafetyModePanelProps {
  onReset: () => void;
}

export default function RepairSafetyModePanel({ onReset }: RepairSafetyModePanelProps) {
  return (
    <div className="rounded-card border-2 border-destructive/40 bg-destructive/10 p-6">
      <div className="flex items-start gap-3">
        <span className="icon-badge !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden>
          <ShieldAlert className="h-4 w-4 text-destructive" />
        </span>
        <div className="flex-1">
          <h3 className="text-base font-art font-bold text-destructive">已進入安全模式</h3>
          <p className="text-body text-foreground mt-1">
            系統偵測到高風險語句。修復流程已暫停，並停用刺激性互動內容。請先確認雙方安全。
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {CRISIS_HOTLINES.map((hotline) => (
          <a
            key={hotline.number}
            href={hotline.href}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-semibold text-destructive hover:bg-destructive/10 transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <PhoneCall className="h-4 w-4" aria-hidden />
            {hotline.name} {hotline.number}
          </a>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onReset}
          className="rounded-full border border-input px-5 py-2 text-body text-foreground hover:bg-muted/60 transition-colors"
        >
          關閉流程並返回
        </button>
        <a
          href="/settings"
          className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground border-t border-t-white/30 px-5 py-2 text-body font-medium shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          前往設定頁
        </a>
      </div>
    </div>
  );
}
