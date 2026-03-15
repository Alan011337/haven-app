export default function NotificationsSkeleton() {
  return (
    <div className="space-y-8 md:space-y-10" aria-busy="true" aria-live="polite">
      {/* Title + subtitle */}
      <div className="space-y-3">
        <div className="h-10 w-36 animate-pulse rounded-[1.5rem] bg-muted/50" aria-hidden />
        <div className="h-4 w-52 animate-pulse rounded-full bg-muted/30" aria-hidden />
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-2">
        <div className="h-9 w-16 animate-pulse rounded-button bg-white/50" aria-hidden />
        <div className="h-9 w-20 animate-pulse rounded-button bg-white/50" aria-hidden />
        <div className="h-9 w-9 animate-pulse rounded-button bg-white/50" aria-hidden />
      </div>

      {/* Feed items */}
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-[88px] animate-pulse rounded-[1.5rem] bg-white/50"
            aria-hidden
          />
        ))}
      </div>
    </div>
  );
}
