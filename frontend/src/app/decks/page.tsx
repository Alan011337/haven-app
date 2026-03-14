'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';

function DecksLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.18),transparent_22%),radial-gradient(circle_at_top_right,rgba(210,223,214,0.25),transparent_26%),linear-gradient(180deg,#faf7f2_0%,#f5f2ec_52%,#f2efe8_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-8 md:space-y-10">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <div className="h-10 w-20 animate-pulse rounded-full bg-muted/40" aria-hidden />
          <div className="h-10 w-28 animate-pulse rounded-full bg-muted/40" aria-hidden />
        </div>

        {/* Page title */}
        <div className="space-y-3">
          <div className="h-10 w-44 animate-pulse rounded-[1.5rem] bg-muted/60" aria-hidden />
          <div className="h-4 w-56 animate-pulse rounded-full bg-muted/40" aria-hidden />
        </div>

        {/* Filter row */}
        <div className="flex gap-2">
          <div className="h-10 w-16 animate-pulse rounded-full bg-muted/40" aria-hidden />
          <div className="h-10 w-20 animate-pulse rounded-full bg-muted/40" aria-hidden />
          <div className="h-10 w-24 animate-pulse rounded-full bg-muted/40" aria-hidden />
          <div className="h-10 w-20 animate-pulse rounded-full bg-muted/40" aria-hidden />
        </div>

        {/* Deck grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <div className="sm:col-span-2">
            <div className="h-44 animate-pulse rounded-[2rem] bg-white/60 shadow-soft" aria-hidden />
          </div>
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div key={i}>
              <div className="h-44 animate-pulse rounded-[2rem] bg-white/60 shadow-soft" aria-hidden />
            </div>
          ))}
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
