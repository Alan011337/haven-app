'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import Button from '@/components/ui/Button';
import { logClientError } from '@/lib/safe-error-log';
import { SettingsShell, SettingsStatePanel } from '@/app/settings/SettingsPrimitives';

interface SettingsErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function SettingsError({ error, reset }: SettingsErrorProps) {
  useEffect(() => {
    logClientError('settings-route-failed', error);
  }, [error]);

  return (
    <SettingsShell>
      <SettingsStatePanel
        tone="error"
        eyebrow="設定中心離線中"
        title="這一頁暫時沒有順利打開"
        description="這裡本來應該是你們調整 Haven 節奏與信任邊界的地方。重新整理後，我們會把設定中心帶回來。"
        actions={
          <>
            <Button
              leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
              onClick={reset}
            >
              重新載入頁面
            </Button>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-white/56 bg-white/78 px-4 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift focus-ring-premium"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              回首頁
            </Link>
          </>
        }
      />
    </SettingsShell>
  );
}
