'use client';

import { GlassCard } from '@/components/haven/GlassCard';
import Skeleton, { SkeletonLines } from '@/components/ui/Skeleton';

export function AnalysisSkeleton() {
  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)]">
      <GlassCard className="overflow-hidden rounded-[3rem] border-white/56 bg-white/76 p-6 md:p-8 xl:p-10">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] xl:gap-8">
          <div className="space-y-6">
            <div className="space-y-4">
              <Skeleton className="h-8 w-44 rounded-full" />
              <Skeleton className="h-14 w-4/5" />
              <SkeletonLines lines={3} className="max-w-2xl" />
            </div>
            <Skeleton className="h-24 w-full rounded-[1.8rem]" />
            <div className="flex flex-wrap gap-3">
              <Skeleton className="h-10 w-28 rounded-full" />
              <Skeleton className="h-10 w-28 rounded-full" />
              <Skeleton className="h-10 w-36 rounded-full" />
            </div>
            <div className="flex flex-wrap gap-3">
              <Skeleton className="h-12 w-40 rounded-full" />
              <Skeleton className="h-12 w-36 rounded-full" />
            </div>
          </div>

          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
            <GlassCard className="rounded-[2.8rem] border-white/56 bg-white/78 p-6 md:p-8">
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-3">
                    <Skeleton className="h-6 w-32 rounded-full" />
                    <Skeleton className="h-12 w-3/4" />
                    <SkeletonLines lines={2} className="w-full" />
                  </div>
                  <Skeleton className="h-14 w-14 rounded-[1.6rem]" />
                </div>
                <div className="grid gap-5 md:grid-cols-[180px_minmax(0,1fr)]">
                  <div className="space-y-2">
                    <Skeleton className="h-16 w-28" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                  <div className="space-y-4">
                    <Skeleton className="h-3 w-full rounded-full" />
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Skeleton className="h-20 rounded-[1.5rem]" />
                      <Skeleton className="h-20 rounded-[1.5rem]" />
                      <Skeleton className="h-20 rounded-[1.5rem]" />
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>

            <div className="space-y-4">
              <GlassCard className="rounded-[2.2rem] border-white/56 bg-white/78 p-5">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="mt-3 h-8 w-1/2" />
                <SkeletonLines lines={2} className="mt-4" />
              </GlassCard>
              <GlassCard className="rounded-[2.2rem] border-white/56 bg-white/78 p-5">
                <Skeleton className="h-5 w-24" />
                <SkeletonLines lines={3} className="mt-4" />
              </GlassCard>
            </div>
          </div>
        </div>
      </GlassCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-8">
        <div className="space-y-8">
          <GlassCard className="rounded-[2.4rem] border-white/54 bg-white/78 p-6">
            <Skeleton className="h-8 w-52" />
            <SkeletonLines lines={2} className="mt-4 max-w-2xl" />
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <Skeleton className="h-40 rounded-[1.8rem]" />
              <Skeleton className="h-40 rounded-[1.8rem]" />
              <Skeleton className="h-40 rounded-[1.8rem]" />
              <Skeleton className="h-40 rounded-[1.8rem]" />
            </div>
          </GlassCard>

          <GlassCard className="rounded-[2.4rem] border-white/54 bg-white/78 p-6">
            <Skeleton className="h-8 w-40" />
            <SkeletonLines lines={2} className="mt-4 max-w-2xl" />
            <div className="mt-5 grid gap-4 lg:grid-cols-3">
              <Skeleton className="h-44 rounded-[1.8rem]" />
              <Skeleton className="h-44 rounded-[1.8rem]" />
              <Skeleton className="h-44 rounded-[1.8rem]" />
            </div>
          </GlassCard>
        </div>

        <div className="space-y-4">
          <GlassCard className="rounded-[2.2rem] border-white/54 bg-white/78 p-5">
            <Skeleton className="h-6 w-36" />
            <div className="mt-4 flex flex-wrap gap-2">
              <Skeleton className="h-8 w-24 rounded-full" />
              <Skeleton className="h-8 w-28 rounded-full" />
              <Skeleton className="h-8 w-20 rounded-full" />
              <Skeleton className="h-8 w-24 rounded-full" />
            </div>
          </GlassCard>
          <GlassCard className="rounded-[2.2rem] border-white/54 bg-white/78 p-5">
            <Skeleton className="h-6 w-32" />
            <div className="mt-4 space-y-3">
              <Skeleton className="h-16 rounded-[1.4rem]" />
              <Skeleton className="h-16 rounded-[1.4rem]" />
              <Skeleton className="h-16 rounded-[1.4rem]" />
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
