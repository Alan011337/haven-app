'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { fetchDegradationStatus, type DegradationStatus } from '@/lib/degradation';
import { getAdaptiveIntervalMs } from '@/lib/polling-policy';

const POLL_INTERVAL_MS = 60_000;
const INITIAL_POLL_DELAY_MS = 1_500;
const LOCAL_LOOPBACK_INITIAL_POLL_DELAY_MS = 12_000;

function getInitialPollDelayMs(): number {
  if (typeof window === 'undefined') {
    return INITIAL_POLL_DELAY_MS;
  }
  const hostname = window.location.hostname;
  if (hostname === '127.0.0.1' || hostname === 'localhost') {
    return LOCAL_LOOPBACK_INITIAL_POLL_DELAY_MS;
  }
  return INITIAL_POLL_DELAY_MS;
}

export default function DegradationBanner() {
  const [state, setState] = useState<DegradationStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const schedulePoll = (waitMs: number) => {
      timer = setTimeout(poll, waitMs);
    };
    const poll = async () => {
      const result = await fetchDegradationStatus();
      if (mounted) setState(result);
      if (!mounted) return;
      const nextInterval = getAdaptiveIntervalMs(POLL_INTERVAL_MS, { hiddenMultiplier: 3 });
      schedulePoll(nextInterval === false ? 10_000 : nextInterval);
    };
    schedulePoll(getInitialPollDelayMs());
    return () => {
      mounted = false;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!state || state.status !== 'degraded' || Object.keys(state.features).length === 0) {
    return null;
  }

  const messages = Object.values(state.features).map((f) => f.fallback);
  const copy = messages.length === 1
    ? messages[0]
    : '部分功能暫時延遲，請稍後再試或重新整理。';

  return (
    <div
      role="alert"
      className="flex items-center gap-2.5 px-4 py-2.5 text-sm bg-gradient-to-r from-primary/10 to-primary/5 border-b border-border text-foreground animate-slide-up-fade"
    >
      <span className="icon-badge !w-7 !h-7" aria-hidden>
        <AlertCircle className="w-3.5 h-3.5" />
      </span>
      <span className="flex-1 font-medium">{copy}</span>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground text-xs font-semibold border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <RefreshCw className="w-3 h-3" aria-hidden />
        重新整理
      </button>
    </div>
  );
}
