'use client';

import { CloudOff, AlertCircle } from 'lucide-react';
import { useOfflineQueueStatus } from '@/hooks/useOfflineQueueStatus';
import { startReplay } from '@/lib/offline-queue/queue';

export default function OfflineQueueBanner() {
  const { pendingCount, failedCount } = useOfflineQueueStatus();

  if (pendingCount === 0 && failedCount === 0) return null;

  const handleRetry = () => {
    void startReplay();
  };

  const parts: string[] = [];
  if (pendingCount > 0) parts.push(`${pendingCount} 則待同步`);
  if (failedCount > 0) parts.push(`${failedCount} 則同步失敗`);

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2.5 px-4 py-2.5 text-sm bg-gradient-to-r from-muted to-muted/50 border-b border-border text-foreground animate-slide-up-fade"
    >
      {pendingCount > 0 && (
        <span className="icon-badge !w-7 !h-7" aria-hidden>
          <CloudOff className="w-3.5 h-3.5 text-muted-foreground" />
        </span>
      )}
      {failedCount > 0 && (
        <span className="icon-badge !w-7 !h-7 !bg-gradient-to-br !from-destructive/12 !to-destructive/4 !border-destructive/8" aria-hidden>
          <AlertCircle className="w-3.5 h-3.5 text-destructive" />
        </span>
      )}
      <span className="flex-1 font-medium tabular-nums">{parts.join('，')}</span>
      {failedCount > 0 && (
        <button
          type="button"
          onClick={handleRetry}
          className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-border bg-card text-sm font-medium text-foreground hover:bg-muted/80 transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          重試
        </button>
      )}
    </div>
  );
}
