'use client';

import Link from 'next/link';
import { PhoneCall, ShieldAlert } from 'lucide-react';
import Button from '@/components/ui/Button';
import { CRISIS_HOTLINES } from '@/lib/safety-policy';

interface RepairSafetyModePanelProps {
  onReset: () => void;
}

export default function RepairSafetyModePanel({ onReset }: RepairSafetyModePanelProps) {
  return (
    <div className="rounded-[1.5rem] border-2 border-destructive/40 bg-destructive/10 p-6">
      <div className="flex items-start gap-3">
        <span
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-destructive/12 to-destructive/4 border border-destructive/8"
          aria-hidden
        >
          <ShieldAlert className="h-4 w-4 text-destructive" />
        </span>
        <div className="flex-1">
          <h3 className="text-base font-art font-bold text-destructive">已進入安全模式</h3>
          <p className="text-sm text-foreground mt-1 leading-relaxed">
            系統偵測到高風險語句。修復流程已暫停，並停用刺激性互動內容。請先確認雙方安全。
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {CRISIS_HOTLINES.map((hotline) => (
          <a
            key={hotline.number}
            href={hotline.href}
            className="inline-flex items-center gap-2 rounded-button border border-border bg-card px-3 py-2 text-sm font-semibold text-destructive hover:bg-destructive/10 transition-colors duration-haven ease-haven focus-ring-premium"
          >
            <PhoneCall className="h-4 w-4" aria-hidden />
            {hotline.name} {hotline.number}
          </a>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button variant="outline" size="sm" onClick={onReset}>
          關閉流程並返回
        </Button>
        <Link
          href="/settings"
          className="inline-flex items-center rounded-button border border-white/60 bg-white/74 px-4 py-2 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
        >
          前往設定頁
        </Link>
      </div>
    </div>
  );
}
