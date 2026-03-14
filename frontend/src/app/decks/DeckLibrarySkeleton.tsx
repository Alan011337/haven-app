import { GlassCard } from '@/components/haven/GlassCard';

export default function DeckLibrarySkeleton() {
  return (
    <div
      className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(214,181,136,0.16),transparent_24%),radial-gradient(circle_at_88%_8%,rgba(234,240,234,0.5),transparent_28%),linear-gradient(180deg,#fbf8f3_0%,#f5f0e8_54%,#f1ece4_100%)] px-4 py-6 sm:px-6 lg:px-8"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="mx-auto max-w-[1540px] space-y-[clamp(1.5rem,3vw,2.75rem)] animate-slide-up-fade">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="h-11 w-32 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
          <div className="h-11 w-36 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
        </div>

        <GlassCard className="overflow-hidden rounded-[3rem] border-white/50 bg-white/82 p-6 md:p-8 xl:p-10">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.08fr)_320px]">
            <div className="space-y-5">
              <div className="h-10 w-40 animate-pulse rounded-full bg-white/80" aria-hidden />
              <div className="h-4 w-28 animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="h-16 w-4/5 animate-pulse rounded-[1.8rem] bg-muted" aria-hidden />
              <div className="h-5 w-full animate-pulse rounded-full bg-muted" aria-hidden />
              <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
                <div className="h-28 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft" aria-hidden />
                <div className="h-28 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft" aria-hidden />
                <div className="h-28 animate-pulse rounded-[1.7rem] bg-white/76 shadow-soft" aria-hidden />
              </div>
            </div>

            <div className="h-[30rem] animate-pulse rounded-[2.7rem] bg-white/76 shadow-soft" aria-hidden />

            <div className="space-y-4">
              <div className="h-48 animate-pulse rounded-[2.1rem] bg-white/76 shadow-soft" aria-hidden />
              <div className="h-48 animate-pulse rounded-[2.1rem] bg-white/76 shadow-soft" aria-hidden />
            </div>
          </div>
        </GlassCard>

        <GlassCard className="overflow-hidden rounded-[2.35rem] border-white/54 bg-white/82 p-5 md:p-6">
          <div className="space-y-4">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
              <div className="space-y-3">
                <div className="h-4 w-24 animate-pulse rounded-full bg-muted" aria-hidden />
                <div className="h-10 w-96 max-w-full animate-pulse rounded-[1.4rem] bg-muted" aria-hidden />
                <div className="h-5 w-[32rem] max-w-full animate-pulse rounded-full bg-muted" aria-hidden />
              </div>
              <div className="h-12 w-28 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
            </div>
            <div className="flex flex-wrap gap-2">
              <div className="h-10 w-24 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
              <div className="h-10 w-28 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
              <div className="h-10 w-28 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
              <div className="h-10 w-32 animate-pulse rounded-full bg-white/76 shadow-soft" aria-hidden />
              <div className="h-11 w-36 animate-pulse rounded-full bg-white/76 shadow-soft xl:ml-auto" aria-hidden />
            </div>
          </div>
        </GlassCard>

        <div className="space-y-4">
          <div className="space-y-3">
            <div className="h-4 w-28 animate-pulse rounded-full bg-muted" aria-hidden />
            <div className="h-10 w-80 max-w-full animate-pulse rounded-[1.4rem] bg-muted" aria-hidden />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="h-[20rem] animate-pulse rounded-[2.3rem] bg-white/76 shadow-soft" aria-hidden />
            <div className="h-[20rem] animate-pulse rounded-[2.3rem] bg-white/76 shadow-soft" aria-hidden />
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-3">
            <div className="h-4 w-24 animate-pulse rounded-full bg-muted" aria-hidden />
            <div className="h-10 w-72 max-w-full animate-pulse rounded-[1.4rem] bg-muted" aria-hidden />
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div className="h-[18rem] animate-pulse rounded-[2rem] bg-white/76 shadow-soft" aria-hidden />
            <div className="h-[18rem] animate-pulse rounded-[2rem] bg-white/76 shadow-soft" aria-hidden />
            <div className="h-[18rem] animate-pulse rounded-[2rem] bg-white/76 shadow-soft" aria-hidden />
          </div>
        </div>
      </div>
    </div>
  );
}
