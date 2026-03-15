'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import { logClientError } from '@/lib/safe-error-log';

export default function NotificationsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logClientError('NotificationsErrorBoundary', error);
  }, [error]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)]">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.72),transparent_62%)]"
        aria-hidden
      />
      <div className="relative flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="space-y-2">
            <h1 className="font-art text-xl font-medium text-card-foreground">
              通知載入失敗
            </h1>
            <p className="text-sm text-muted-foreground">
              無法載入通知內容，請重試或返回首頁。
            </p>
          </div>
          <div className="flex flex-col items-center gap-3">
            <Button onClick={reset}>重試</Button>
            <Link
              href="/"
              className="inline-flex items-center justify-center rounded-button border border-border/70 bg-card/82 px-5 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
            >
              返回首頁
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
