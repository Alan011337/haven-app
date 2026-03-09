// frontend/src/app/loading.tsx — App Router root loading UI (Haven tokens only)

import { GlassCard } from '@/components/haven/GlassCard';

export default function Loading() {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-auth-gradient px-4 py-16 relative overflow-hidden"
      aria-live="polite"
      aria-busy="true"
    >
      {/* Breathing orb */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-72 h-72 rounded-full bg-primary/6 blur-hero-orb animate-breathe pointer-events-none" aria-hidden />

      <div className="w-full max-w-md space-y-6 animate-page-enter">
        <GlassCard className="p-8 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
          <div className="mb-6 h-12 w-12 skeleton-shimmer rounded-2xl" aria-hidden />
          <div className="space-y-3">
            <div className="h-5 w-3/4 skeleton-shimmer rounded-xl" aria-hidden />
            <div className="h-5 w-full skeleton-shimmer rounded-xl" aria-hidden />
            <div className="h-5 w-5/6 skeleton-shimmer rounded-xl" aria-hidden />
          </div>
        </GlassCard>
        <div className="flex gap-3 animate-page-enter-delay-1">
          <div className="h-12 flex-1 skeleton-shimmer rounded-button" aria-hidden />
          <div className="h-12 flex-1 skeleton-shimmer rounded-button" aria-hidden />
        </div>
      </div>
    </div>
  );
}
