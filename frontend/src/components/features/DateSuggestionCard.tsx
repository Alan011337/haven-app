'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import { Calendar } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import { HOME_OPTIONAL_AUTO_RETRY_DELAY_MS, HOME_OPTIONAL_DATA_TIMEOUT_MS } from '@/lib/home-performance';
import { fetchDateSuggestions, type DateSuggestionPublic } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import Skeleton from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';

export default function DateSuggestionCard({ className }: { className?: string }) {
  const [data, setData] = useState<DateSuggestionPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const autoRetriedRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadFailed(false);
    try {
      const res = await fetchDateSuggestions({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS });
      setData(res);
    } catch (e) {
      setData(null);
      setLoadFailed(true);
      logClientError('date-suggestions-fetch-failed', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loadFailed || autoRetriedRef.current) return;
    autoRetriedRef.current = true;
    const timer = window.setTimeout(() => {
      void load();
    }, HOME_OPTIONAL_AUTO_RETRY_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [load, loadFailed]);

  if (loading) {
    return (
      <GlassCard className={cn('p-6 md:p-8 relative overflow-hidden', className)}>
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
        <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
          <span className="icon-badge">
            <Calendar className="w-5 h-5 text-primary" aria-hidden />
          </span>
          本週約會提案
        </h3>
        <div className="space-y-2.5 mt-3">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </GlassCard>
    );
  }

  if (!data || !data.suggested) {
    if (loadFailed) {
      return (
        <GlassCard className={cn('p-6 md:p-8 relative overflow-hidden', className)}>
          <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
          <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
            <span className="icon-badge">
              <Calendar className="w-5 h-5 text-primary" aria-hidden />
            </span>
            本週約會提案
          </h3>
          <p className="text-sm text-muted-foreground/80 leading-relaxed">
            提案資料還在同步，剛剛這次沒有成功載入。這不代表目前沒有可用提案。
          </p>
          <button
            type="button"
            onClick={() => {
              autoRetriedRef.current = true;
              void load();
            }}
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-border bg-white/82 px-4 py-2 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-0.5 hover:shadow-lift"
          >
            <Calendar className="h-4 w-4" aria-hidden />
            重新同步提案
          </button>
        </GlassCard>
      );
    }

    return (
      <GlassCard className={cn('p-6 md:p-8 relative overflow-hidden', className)}>
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
        <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
          <span className="icon-badge animate-breathe">
            <Calendar className="w-5 h-5 text-primary" aria-hidden />
          </span>
          本週約會提案
        </h3>
        <p className="text-sm text-muted-foreground/70 leading-relaxed">
          暫無新提案，繼續寫下你們的心願，系統會在合適的時機送上靈感。
        </p>
        <Link
          href="/blueprint"
          className="inline-flex items-center gap-1.5 mt-3 text-sm text-primary/80 hover:text-primary transition-colors duration-haven"
          aria-label="前往藍圖與願望清單"
        >
          看看願望清單 <span aria-hidden>&rarr;</span>
        </Link>
      </GlassCard>
    );
  }

  const suggestions = data.suggestions ?? [];

  return (
    <GlassCard className={cn('p-6 md:p-8 relative overflow-hidden', className)}>
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" aria-hidden />
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Calendar className="w-5 h-5 text-primary" aria-hidden />
        </span>
        本週約會提案
      </h3>
      <p className="text-body text-foreground mb-4 leading-relaxed animate-slide-up-fade">{data.message}</p>
      {suggestions.length > 0 && (
        <ul className="mb-4 space-y-2 animate-slide-up-fade-1 rounded-2xl bg-white/30 border border-white/40 p-3">
          {suggestions.slice(0, 5).map((idea, i) => (
            <li key={i} className="flex items-start gap-3 group">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary tabular-nums">
                {i + 1}
              </span>
              <span className="text-body text-foreground/85 group-hover:text-foreground transition-colors duration-haven">
                {idea}
              </span>
            </li>
          ))}
        </ul>
      )}
      <Link
        href="/blueprint"
        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-6 py-2.5 text-body font-semibold border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="前往藍圖與願望清單"
      >
        看看願望清單
      </Link>
    </GlassCard>
  );
}
