'use client';

export default function MemorySkeleton() {
  return (
    <div className="space-y-8 md:space-y-10 animate-slide-up-fade" aria-live="polite" aria-busy="true">
      {/* Title skeleton */}
      <div className="space-y-3">
        <div className="h-10 w-40 animate-pulse rounded-[1.5rem] bg-muted/50" aria-hidden />
        <div className="h-4 w-56 animate-pulse rounded-full bg-muted/30" aria-hidden />
      </div>
      {/* Time Capsule skeleton */}
      <div className="h-28 animate-pulse rounded-[2rem] bg-white/60 shadow-soft" aria-hidden />
      {/* Toggle skeleton */}
      <div className="flex gap-2">
        <div className="h-9 w-20 animate-pulse rounded-button bg-white/50" aria-hidden />
        <div className="h-9 w-20 animate-pulse rounded-button bg-white/50" aria-hidden />
      </div>
      {/* Feed skeletons */}
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-[1.5rem] bg-white/50" aria-hidden />
        ))}
      </div>
      {/* Report skeleton */}
      <div className="h-28 animate-pulse rounded-[2rem] bg-white/50 shadow-soft" aria-hidden />
    </div>
  );
}
