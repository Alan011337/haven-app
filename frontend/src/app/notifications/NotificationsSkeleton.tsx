'use client';

import Skeleton, { SkeletonLines } from '@/components/ui/Skeleton';

export function NotificationsSkeleton() {
  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)]" aria-hidden="true">
      <section className="overflow-hidden rounded-[3.1rem] border border-white/56 bg-white/72 p-6 shadow-lift backdrop-blur-xl md:p-8 xl:p-10">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)] xl:gap-8">
          <div className="space-y-6">
            <div className="space-y-4">
              <Skeleton className="h-8 w-44 rounded-full" />
              <Skeleton className="h-16 w-4/5 rounded-[2rem]" />
              <SkeletonLines lines={3} className="max-w-3xl" />
            </div>

            <div className="rounded-[2rem] border border-white/56 bg-white/70 p-4 shadow-soft">
              <Skeleton className="h-20 w-full rounded-[1.5rem]" />
            </div>

            <div className="flex flex-wrap gap-3">
              <Skeleton className="h-11 w-40 rounded-full" />
              <Skeleton className="h-11 w-32 rounded-full" />
            </div>
          </div>

          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="rounded-[2.8rem] border border-white/56 bg-white/74 p-6 shadow-soft">
              <Skeleton className="h-10 w-56 rounded-full" />
              <Skeleton className="mt-5 h-12 w-3/4 rounded-[1.25rem]" />
              <SkeletonLines lines={4} className="mt-5" />
              <div className="mt-6 flex gap-3">
                <Skeleton className="h-10 w-28 rounded-full" />
                <Skeleton className="h-10 w-32 rounded-full" />
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-[2.25rem] border border-white/56 bg-white/74 p-5 shadow-soft">
                <Skeleton className="h-6 w-28 rounded-full" />
                <Skeleton className="mt-4 h-9 w-24 rounded-[1rem]" />
                <SkeletonLines lines={3} className="mt-4" />
              </div>
              <div className="rounded-[2.25rem] border border-white/56 bg-white/74 p-5 shadow-soft">
                <Skeleton className="h-6 w-32 rounded-full" />
                <Skeleton className="mt-4 h-9 w-28 rounded-[1rem]" />
                <SkeletonLines lines={2} className="mt-4" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[2.65rem] border border-white/56 bg-white/76 p-5 shadow-soft backdrop-blur-xl md:p-6">
        <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
          <div className="space-y-3">
            <Skeleton className="h-6 w-28 rounded-full" />
            <Skeleton className="h-8 w-40 rounded-[1rem]" />
            <SkeletonLines lines={2} />
          </div>
          <div className="rounded-[2rem] border border-white/56 bg-white/72 p-4 shadow-soft">
            <div className="flex flex-wrap gap-3">
              {Array.from({ length: 7 }).map((_, index) => (
                <Skeleton key={index} className="h-9 w-28 rounded-full" />
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-8">
        <div className="space-y-6">
          {Array.from({ length: 3 }).map((_, sectionIndex) => (
            <section key={sectionIndex} className="space-y-4">
              <div className="flex items-end justify-between gap-3">
                <div className="space-y-2">
                  <Skeleton className="h-5 w-28 rounded-full" />
                  <Skeleton className="h-8 w-52 rounded-[1rem]" />
                </div>
                <Skeleton className="h-8 w-16 rounded-full" />
              </div>

              <div className="space-y-4">
                {sectionIndex === 0 ? (
                  <div className="rounded-[2.8rem] border border-white/56 bg-white/72 p-6 shadow-soft">
                    <Skeleton className="h-10 w-48 rounded-full" />
                    <Skeleton className="mt-4 h-12 w-3/5 rounded-[1rem]" />
                    <SkeletonLines lines={3} className="mt-4" />
                  </div>
                ) : null}
                {Array.from({ length: sectionIndex === 2 ? 3 : 2 }).map((_, rowIndex) => (
                  <div key={rowIndex} className="rounded-[2rem] border border-white/56 bg-white/72 p-5 shadow-soft">
                    <div className="flex gap-4">
                      <Skeleton className="h-12 w-12 rounded-[1.2rem]" />
                      <div className="flex-1 space-y-3">
                        <Skeleton className="h-6 w-36 rounded-full" />
                        <SkeletonLines lines={2} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, railIndex) => (
            <div key={railIndex} className="rounded-[2.25rem] border border-white/56 bg-white/74 p-5 shadow-soft">
              <Skeleton className="h-6 w-32 rounded-full" />
              <SkeletonLines lines={3} className="mt-4" />
              <Skeleton className="mt-5 h-28 w-full rounded-[1.5rem]" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default NotificationsSkeleton;
