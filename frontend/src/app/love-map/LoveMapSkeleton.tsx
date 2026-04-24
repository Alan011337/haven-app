'use client';

import { GlassCard } from '@/components/haven/GlassCard';

export default function LoveMapSkeleton() {
  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)] animate-slide-up-fade" aria-live="polite" aria-busy="true">
      <GlassCard className="overflow-hidden rounded-[3.1rem] border-white/54 bg-white/84 p-6 md:p-8 xl:p-10">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <div className="space-y-4">
              <div className="h-4 w-36 animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-16 w-4/5 animate-pulse rounded-[1.6rem] bg-muted" aria-hidden />
              <div className="h-5 w-full animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-5 w-3/4 animate-pulse rounded-full bg-muted" aria-hidden />
            </div>
            <div className="h-24 animate-pulse rounded-[1.9rem] bg-white/76 shadow-soft" aria-hidden />
            <div className="grid gap-3 md:grid-cols-3">
              <div className="h-28 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft" aria-hidden />
              <div className="h-28 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft" aria-hidden />
              <div className="h-28 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft" aria-hidden />
            </div>
            <div className="h-12 w-56 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
          </div>

          <div className="space-y-4">
            <div className="h-56 animate-pulse rounded-[2.3rem] bg-white/76 shadow-soft" aria-hidden />
            <div className="h-64 animate-pulse rounded-[2.3rem] bg-white/76 shadow-soft" aria-hidden />
          </div>
        </div>
      </GlassCard>

      <GlassCard className="overflow-hidden rounded-[2rem] border-white/54 bg-white/72 p-3">
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <div
              key={index}
              className="h-20 min-w-[12rem] flex-1 animate-pulse rounded-[1.35rem] bg-white/76 shadow-soft"
              aria-hidden
            />
          ))}
        </div>
      </GlassCard>

      {Array.from({ length: 4 }).map((_, index) => (
        <GlassCard
          key={index}
          className="overflow-hidden rounded-[2.8rem] border-white/52 bg-white/82 p-6 md:p-8 xl:p-10"
        >
          <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)] xl:gap-10">
            <div className="space-y-4">
              <div className="h-4 w-24 animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-12 w-4/5 animate-pulse rounded-[1.4rem] bg-muted" aria-hidden />
              <div className="h-5 w-full animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-5 w-5/6 animate-pulse rounded-full bg-muted" aria-hidden />
            </div>

            <div className="space-y-4">
              <div className="h-48 animate-pulse rounded-[2rem] bg-white/76 shadow-soft" aria-hidden />
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="h-56 animate-pulse rounded-[2rem] bg-white/76 shadow-soft" aria-hidden />
                <div className="h-56 animate-pulse rounded-[2rem] bg-white/76 shadow-soft" aria-hidden />
              </div>
            </div>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}
