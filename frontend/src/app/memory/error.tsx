'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { logClientError } from '@/lib/safe-error-log';
import { GlassCard } from '@/components/haven/GlassCard';

export default function MemoryError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logClientError('MemoryErrorBoundary', error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <GlassCard className="w-full max-w-md p-8 text-center animate-scale-in relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-destructive/30 to-transparent" aria-hidden />
        <div
          className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-destructive/15 to-destructive/5 ring-4 ring-destructive/10 text-destructive"
          aria-hidden
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-7 w-7"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h1 className="mb-2 text-title font-art font-bold text-card-foreground tracking-tight">回憶長廊載入失敗</h1>
        <p className="mb-6 text-body text-muted-foreground">
          無法載入回憶內容，請重試或返回首頁。
        </p>
        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={reset}
            className="w-full rounded-button bg-gradient-to-b from-primary to-primary/90 border-t border-t-white/30 px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-95"
          >
            重試
          </button>
          <Link
            href="/"
            className="w-full rounded-button border border-border/60 bg-card/80 backdrop-blur-sm px-4 py-2.5 text-sm font-medium text-foreground transition-all duration-haven ease-haven hover:bg-card hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-95"
          >
            返回首頁
          </Link>
        </div>
      </GlassCard>
    </div>
  );
}
