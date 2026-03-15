'use client';

import { useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import Button from '@/components/ui/Button';
import { logClientError } from '@/lib/safe-error-log';
import {
  AnalysisLinkAction,
  AnalysisShell,
  AnalysisStatePanel,
} from '@/app/analysis/AnalysisPrimitives';

export default function AnalysisError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logClientError('analysis-route-failed', error);
  }, [error]);

  return (
    <AnalysisShell>
      <AnalysisStatePanel
        tone="error"
        eyebrow="Analysis Route"
        title="這一頁的洞察暫時沒有順利展開"
        description="這比較像是頁面層的失敗，而不是你們沒有資料。重新嘗試後，Haven 會再把理解中心帶回來。"
        actions={
          <>
            <Button
              leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
              onClick={reset}
            >
              重新載入頁面
            </Button>
            <AnalysisLinkAction href="/" label="回首頁" />
            <AnalysisLinkAction href="/memory" label="改從回憶長廊進入" />
          </>
        }
      />
    </AnalysisShell>
  );
}
