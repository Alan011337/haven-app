'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import { logClientError } from '@/lib/safe-error-log';
import { MemoryShell, MemoryStatePanel } from './MemoryPrimitives';

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
    <MemoryShell>
      <div className="flex min-h-[70vh] items-center justify-center">
        <div className="w-full max-w-2xl">
          <MemoryStatePanel
            tone="error"
            eyebrow="回憶長廊離線中"
            title="這條回憶長廊暫時沒有順利展開。"
            description="不是你們的回憶消失了，而是這次載入失敗。你可以再試一次，或先回到首頁，晚一點再一起回來。"
            action={
              <div className="flex flex-wrap gap-3">
                <Button onClick={reset}>重新展開回憶長廊</Button>
                <Link
                  href="/"
                  className="inline-flex items-center justify-center rounded-button border border-border/70 bg-card/82 px-5 py-3 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
                >
                  回首頁
                </Link>
              </div>
            }
          />
        </div>
      </div>
    </MemoryShell>
  );
}
