export type HomeTimelineStage = 'loading' | 'deferred' | 'empty' | 'ready';

export function resolveHomeTimelineStage({
  mounted,
  loading,
  unavailable,
  itemCount,
}: {
  mounted: boolean;
  loading: boolean;
  unavailable: boolean;
  itemCount: number;
}): HomeTimelineStage {
  if (!mounted || loading) {
    return 'loading';
  }
  if (itemCount > 0) {
    return 'ready';
  }
  if (unavailable) {
    return 'deferred';
  }
  return 'empty';
}
