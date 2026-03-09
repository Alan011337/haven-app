// frontend/src/app/decks/loading.tsx — Segment loading UI for /decks (Haven tokens only)

import { GlassCard } from '@/components/haven/GlassCard';

export default function DecksLoading() {
  return (
    <div
      className="flex min-h-[60vh] items-center justify-center bg-background px-4 py-16"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="w-full max-w-2xl space-y-6 animate-slide-up-fade">
        <GlassCard className="p-8 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
          <div className="mb-6 h-10 w-48 animate-pulse rounded-card bg-muted" aria-hidden />
          <div className="space-y-3">
            <div className="h-5 w-3/4 animate-pulse rounded-card bg-muted" aria-hidden />
            <div className="h-5 w-full animate-pulse rounded-card bg-muted" aria-hidden />
            <div className="h-5 w-5/6 animate-pulse rounded-card bg-muted" aria-hidden />
          </div>
        </GlassCard>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-card bg-muted"
              aria-hidden
            />
          ))}
        </div>
      </div>
    </div>
  );
}
