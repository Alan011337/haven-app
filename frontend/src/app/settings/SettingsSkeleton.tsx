import Skeleton, { SkeletonLines } from '@/components/ui/Skeleton';

export function SettingsSkeleton() {
  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)]">
      <section className="overflow-hidden rounded-[3.1rem] border border-white/54 bg-white/70 p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] xl:gap-8">
          <div className="space-y-5">
            <Skeleton className="h-4 w-28 rounded-full" variant="shimmer" />
            <Skeleton className="h-14 w-full max-w-3xl rounded-[2rem]" variant="shimmer" />
            <SkeletonLines lines={3} className="max-w-2xl" />
            <Skeleton className="h-24 w-full max-w-3xl rounded-[2rem]" variant="shimmer" />
            <div className="flex flex-wrap gap-3">
              <Skeleton className="h-11 w-36 rounded-full" variant="shimmer" />
              <Skeleton className="h-11 w-28 rounded-full" variant="shimmer" />
            </div>
          </div>

          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="rounded-[2.6rem] border border-white/54 bg-white/74 p-6 shadow-soft">
              <Skeleton className="h-5 w-32 rounded-full" variant="shimmer" />
              <Skeleton className="mt-4 h-12 w-3/4 rounded-[1.5rem]" variant="shimmer" />
              <SkeletonLines lines={4} className="mt-5" />
              <div className="mt-6 grid gap-3 md:grid-cols-2">
                <Skeleton className="h-24 rounded-[1.5rem]" variant="shimmer" />
                <Skeleton className="h-24 rounded-[1.5rem]" variant="shimmer" />
              </div>
            </div>
            <div className="space-y-4">
              <Skeleton className="h-40 rounded-[2.2rem]" variant="shimmer" />
              <Skeleton className="h-40 rounded-[2.2rem]" variant="shimmer" />
              <Skeleton className="h-40 rounded-[2.2rem]" variant="shimmer" />
            </div>
          </div>
        </div>
      </section>

      <div className="rounded-[2.4rem] border border-white/54 bg-white/72 p-4 shadow-soft">
        <div className="grid gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 rounded-[1.65rem]" variant="shimmer" />
          ))}
        </div>
      </div>

      <div className="grid gap-5">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="rounded-[2.8rem] border border-white/54 bg-white/74 p-5 shadow-soft md:p-7"
          >
            <div className="space-y-5">
              <div className="space-y-3">
                <Skeleton className="h-4 w-24 rounded-full" variant="shimmer" />
                <Skeleton className="h-10 w-72 rounded-[1.4rem]" variant="shimmer" />
                <SkeletonLines lines={2} className="max-w-2xl" />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <Skeleton className="h-28 rounded-[1.7rem]" variant="shimmer" />
                <Skeleton className="h-28 rounded-[1.7rem]" variant="shimmer" />
              </div>

              <Skeleton className="h-40 rounded-[1.9rem]" variant="shimmer" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
