import Skeleton from '@/components/ui/Skeleton';

export default function SettingsSkeleton() {
  return (
    <div className="space-y-8 md:space-y-10">
      {/* Appearance skeleton */}
      <div className="rounded-[2rem] border border-white/50 bg-white/70 p-6 shadow-soft md:p-8">
        <Skeleton className="mb-5 h-6 w-32 rounded-lg" variant="shimmer" aria-hidden />
        <div className="space-y-5">
          <Skeleton className="h-12 w-full rounded-lg" variant="shimmer" aria-hidden />
          <Skeleton className="h-12 w-full rounded-lg" variant="shimmer" aria-hidden />
          <Skeleton className="h-12 w-full rounded-lg" variant="shimmer" aria-hidden />
        </div>
      </div>
      {/* Child component skeletons */}
      <Skeleton className="h-32 w-full rounded-[2rem]" variant="shimmer" aria-hidden />
      <Skeleton className="h-48 w-full rounded-[2rem]" variant="shimmer" aria-hidden />
      <Skeleton className="h-40 w-full rounded-[2rem]" variant="shimmer" aria-hidden />
      <Skeleton className="h-28 w-full rounded-[2rem]" variant="shimmer" aria-hidden />
      <Skeleton className="h-28 w-full rounded-[2rem]" variant="shimmer" aria-hidden />
    </div>
  );
}
