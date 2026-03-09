'use client';

type SkeletonProps = {
  className?: string;
  /** 'shimmer' (default) — luxury wave; 'pulse' — simple pulse fallback. */
  variant?: 'shimmer' | 'pulse';
};

export default function Skeleton({ className = '', variant = 'shimmer' }: SkeletonProps) {
  const animClass = variant === 'pulse' ? 'animate-pulse bg-muted' : 'skeleton-shimmer';
  return (
    <div
      className={`rounded-card ${animClass} ${className}`.trim()}
      aria-hidden="true"
    />
  );
}

/** Multi-line skeleton for content placeholders. */
export function SkeletonLines({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-3 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 ? 'w-3/5' : 'w-full'}`}
        />
      ))}
    </div>
  );
}

/** Card-shaped skeleton with header + body. */
export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-card border border-foreground/5 bg-card/50 backdrop-blur-sm p-6 space-y-4 shadow-soft ${className}`} aria-hidden="true">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-2/5" />
          <Skeleton className="h-3 w-1/4" />
        </div>
      </div>
      <SkeletonLines lines={3} />
    </div>
  );
}
