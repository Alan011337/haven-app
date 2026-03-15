export default function AnalysisSkeleton() {
  return (
    <div
      className="space-y-8 md:space-y-10 animate-slide-up-fade"
      aria-busy="true"
      aria-live="polite"
    >
      {/* Title + subtitle */}
      <div className="space-y-3">
        <div className="h-10 w-36 animate-pulse rounded-[1.5rem] bg-muted/50" aria-hidden />
        <div className="h-4 w-56 animate-pulse rounded-full bg-muted/30" aria-hidden />
      </div>

      {/* Relationship Pulse */}
      <div className="h-40 animate-pulse rounded-[2rem] bg-white/60 shadow-soft" aria-hidden />

      {/* Connection Rhythm */}
      <div className="h-44 animate-pulse rounded-[2rem] bg-white/55 shadow-soft" aria-hidden />

      {/* Conversation Landscape */}
      <div className="h-32 animate-pulse rounded-[2rem] bg-white/50 shadow-soft" aria-hidden />
    </div>
  );
}
