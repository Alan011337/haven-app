'use client';

import Link from 'next/link';
import { ArrowLeft, RefreshCw } from 'lucide-react';

export default function SettingsError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]"
        aria-hidden
      />
      <div className="relative mx-auto max-w-3xl space-y-8 px-4 py-6 pb-24 sm:px-6 lg:px-8 md:space-y-10">
        <Link
          href="/"
          className="inline-flex items-center gap-[var(--space-inline)] rounded-button border border-white/60 bg-white/74 px-4 py-2.5 type-label text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
          aria-label="返回首頁"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          回首頁
        </Link>

        <div className="animate-slide-up-fade">
          <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
            設定載入失敗
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground md:text-base">
            發生了一些問題，請稍後再試。
          </p>
        </div>

        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-b from-primary to-primary/90 px-6 py-3 font-medium text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium active:scale-[0.97]"
        >
          <RefreshCw className="h-4 w-4" aria-hidden />
          重新載入
        </button>
      </div>
    </div>
  );
}
