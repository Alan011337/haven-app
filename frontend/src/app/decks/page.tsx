'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import { GlassCard } from '@/components/haven/GlassCard';

function DecksLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <GlassCard className="rounded-[2rem] border-white/55 bg-white/78 p-6 md:p-8">
          <div className="space-y-4">
            <div className="h-4 w-28 animate-pulse rounded-full bg-muted" aria-hidden />
            <div className="h-14 w-2/3 animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
            <div className="h-5 w-full animate-pulse rounded-full bg-muted" aria-hidden />
            <div className="h-5 w-4/5 animate-pulse rounded-full bg-muted" aria-hidden />
          </div>
        </GlassCard>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_360px]">
          <GlassCard className="rounded-[2rem] border-white/55 bg-white/78 p-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="h-28 animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
              <div className="h-28 animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
              <div className="h-28 animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
            </div>
          </GlassCard>
          <GlassCard className="rounded-[2rem] border-white/55 bg-white/78 p-6">
            <div className="space-y-3">
              <div className="h-4 w-24 animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-10 w-full animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
              <div className="h-24 w-full animate-pulse rounded-[1.5rem] bg-muted" aria-hidden />
            </div>
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <div className="h-[22rem] animate-pulse rounded-[2rem] bg-white/72 shadow-soft" aria-hidden />
          </div>
          <div className="lg:col-span-5">
            <div className="h-[18rem] animate-pulse rounded-[2rem] bg-white/72 shadow-soft" aria-hidden />
          </div>
          <div className="lg:col-span-5">
            <div className="h-[18rem] animate-pulse rounded-[2rem] bg-white/72 shadow-soft" aria-hidden />
          </div>
          <div className="lg:col-span-7">
            <div className="h-[22rem] animate-pulse rounded-[2rem] bg-white/72 shadow-soft" aria-hidden />
          </div>
        </div>
      </div>
    </div>
  );
}

const DecksPageContent = dynamic(
  () => import('./DecksPageContent').then((m) => m.default),
  {
    loading: () => <DecksLoadingSkeleton />,
  },
);

export default function DecksPage() {
  return (
    <Suspense fallback={<DecksLoadingSkeleton />}>
      <DecksPageContent />
    </Suspense>
  );
}
