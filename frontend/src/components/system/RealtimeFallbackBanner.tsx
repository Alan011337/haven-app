'use client';

import { useEffect, useState, type ReactElement } from 'react';
import { WifiOff } from 'lucide-react';
import { REALTIME_FALLBACK_EVENT, type RealtimeFallbackDetail } from '@/lib/realtime-policy';

export default function RealtimeFallbackBanner(): ReactElement | null {
  const [active, setActive] = useState(false);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<RealtimeFallbackDetail>).detail;
      if (!detail) return;
      setActive(Boolean(detail.active));
    };
    window.addEventListener(REALTIME_FALLBACK_EVENT, handler as EventListener);
    return () => {
      window.removeEventListener(REALTIME_FALLBACK_EVENT, handler as EventListener);
    };
  }, []);

  if (!active) {
    return null;
  }

  return (
    <div
      role="status"
      className="flex items-center gap-2.5 px-4 py-2.5 text-sm bg-amber-500/10 border-b border-amber-500/30 text-amber-900"
    >
      <span className="icon-badge !w-7 !h-7 bg-amber-500/15" aria-hidden>
        <WifiOff className="w-3.5 h-3.5 text-amber-700" />
      </span>
      <span className="flex-1 font-medium">
        即時連線中斷，已切換為同步模式（輪詢/手動刷新）。
      </span>
    </div>
  );
}
