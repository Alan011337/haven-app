'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Calendar } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import { HOME_OPTIONAL_DATA_TIMEOUT_MS } from '@/lib/home-performance';
import { fetchDateSuggestions, type DateSuggestionPublic } from '@/services/api-client';
import { logClientError } from '@/lib/safe-error-log';
import { cn } from '@/lib/utils';

export default function DateSuggestionCard({ className }: { className?: string }) {
  const [data, setData] = useState<DateSuggestionPublic | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await fetchDateSuggestions({ timeout: HOME_OPTIONAL_DATA_TIMEOUT_MS });
      setData(res);
    } catch (e) {
      logClientError('date-suggestions-fetch-failed', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading || !data) {
    return null;
  }
  if (!data.suggested) {
    return null;
  }

  const suggestions = data.suggestions ?? [];

  return (
    <GlassCard className={cn('p-6 md:p-8 relative overflow-hidden', className)}>
      <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Calendar className="w-5 h-5 text-primary" aria-hidden />
        </span>
        本週約會提案
      </h3>
      <p className="text-body text-foreground mb-4 animate-slide-up-fade">{data.message}</p>
      {suggestions.length > 0 && (
        <ul className="mb-4 space-y-1.5 animate-slide-up-fade-1">
          {suggestions.slice(0, 5).map((idea, i) => (
            <li key={i} className="list-item-premium text-body text-muted-foreground">{idea}</li>
          ))}
        </ul>
      )}
      <Link
        href="/blueprint"
        className="inline-flex items-center gap-2 rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2.5 text-body font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="前往藍圖與願望清單"
      >
        看看願望清單
      </Link>
    </GlassCard>
  );
}
