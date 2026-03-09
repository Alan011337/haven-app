// frontend/src/app/memory/loading.tsx — Skeleton for 回憶長廊 (haven-ui §7)

export default function MemoryLoading() {
  return (
    <div className="min-h-screen bg-muted/40 pb-24" aria-live="polite" aria-busy="true">
      {/* Header skeleton */}
      <header className="sticky top-0 z-10 bg-card/80 backdrop-blur-2xl border-b border-border/60 px-4 py-4 flex items-center gap-2 shadow-soft relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
        <div className="h-10 w-10 animate-pulse rounded-button bg-muted" aria-hidden />
        <div className="flex-1 h-7 w-32 animate-pulse rounded-card bg-muted" aria-hidden />
        <div className="h-10 w-20 animate-pulse rounded-button bg-muted" aria-hidden />
      </header>

      <main className="p-4 max-w-2xl mx-auto space-y-6">
        {/* Time capsule block */}
        <section>
          <div className="h-5 w-24 animate-pulse rounded-card bg-muted mb-2" aria-hidden />
          <div className="h-24 w-full animate-pulse rounded-card bg-muted" aria-hidden />
        </section>
        {/* Report block */}
        <section>
          <div className="h-5 w-32 animate-pulse rounded-card bg-muted mb-2" aria-hidden />
          <div className="h-28 w-full animate-pulse rounded-card bg-muted" aria-hidden />
        </section>
        {/* Feed/calendar block */}
        <section>
          <div className="h-5 w-16 animate-pulse rounded-card bg-muted mb-2" aria-hidden />
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 w-full animate-pulse rounded-card bg-muted" aria-hidden />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
