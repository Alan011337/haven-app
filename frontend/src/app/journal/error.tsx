'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import Button from '@/components/ui/Button';
import { logClientError } from '@/lib/safe-error-log';
import { JournalShell, JournalStatePanel } from '@/app/journal/JournalPrimitives';

export default function JournalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logClientError('journal-route-failed', error);
  }, [error]);

  return (
    <JournalShell>
      <JournalStatePanel
        eyebrow="書房離線中"
        title="Journal 書房暫時沒有順利展開"
        description="這比較像是頁面層的失敗，而不是你的內容消失了。重新整理後，Haven 會再把這一頁帶回來。"
        tone="error"
        actions={
          <>
            <Button
              leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
              onClick={reset}
            >
              重新載入
            </Button>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              回首頁
            </Link>
          </>
        }
      />
    </JournalShell>
  );
}
