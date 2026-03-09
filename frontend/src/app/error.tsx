'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { logClientError } from '@/lib/safe-error-log';
import { GlassCard } from '@/components/haven/GlassCard';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logClientError('Haven ErrorBoundary', error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-auth-gradient px-4 relative overflow-hidden">
      {/* Decorative orbs */}
      <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-destructive/5 blur-hero-orb animate-float pointer-events-none" aria-hidden />
      <div className="absolute bottom-1/4 right-1/4 w-48 h-48 rounded-full bg-primary/5 blur-hero-orb-sm animate-float-delayed pointer-events-none" aria-hidden />

      <GlassCard className="w-full max-w-md p-10 text-center animate-scale-in relative">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-destructive/30 to-transparent" aria-hidden />

        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-destructive/15 to-destructive/5 ring-4 ring-destructive/10" aria-hidden>
          <AlertCircle className="h-7 w-7 text-destructive" />
        </div>
        <h1 className="mb-2 text-title font-art font-bold text-card-foreground tracking-tight">
          發生了一些問題
        </h1>
        <p className="mb-8 text-body text-muted-foreground leading-relaxed">
          系統遇到未預期的錯誤，請重試或回到首頁。
        </p>
        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={reset}
            className="w-full inline-flex items-center justify-center gap-2 rounded-button bg-gradient-to-b from-primary to-primary/90 border-t border-t-white/30 px-5 py-3 text-sm font-semibold text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.98]"
          >
            <RefreshCw className="w-4 h-4" />
            重試
          </button>
          <Link
            href="/"
            className="w-full inline-flex items-center justify-center gap-2 rounded-button border border-border/60 bg-card/80 backdrop-blur-sm px-5 py-3 text-sm font-medium text-foreground transition-all duration-haven ease-haven hover:bg-card hover:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.98]"
          >
            <Home className="w-4 h-4" />
            回到首頁
          </Link>
        </div>
      </GlassCard>
    </div>
  );
}
