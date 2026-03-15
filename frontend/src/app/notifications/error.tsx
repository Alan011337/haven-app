'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import Button from '@/components/ui/Button';
import { NotificationsShell, NotificationsStatePanel } from '@/app/notifications/NotificationsPrimitives';
import { logClientError } from '@/lib/safe-error-log';

interface NotificationsErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function NotificationsError({ error, reset }: NotificationsErrorProps) {
  useEffect(() => {
    logClientError('NotificationsErrorBoundary', error);
  }, [error]);

  return (
    <NotificationsShell>
      <NotificationsStatePanel
        tone="error"
        eyebrow="Notifications Route"
        title="通知中心暫時沒有順利打開"
        description="這裡應該是一個 calm 而清楚的關係脈動入口，而不是空白頁。重新整理後，我們會把它帶回來。"
        actions={
          <>
            <Button
              leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
              onClick={reset}
            >
              再試一次
            </Button>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/76 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              回首頁
            </Link>
          </>
        }
      />
    </NotificationsShell>
  );
}
