'use client';

import { useFeatureFlags } from '@/hooks/queries';
import { getThemeForMood } from '@/lib/mood-background';
import { useAppearanceStore } from '@/stores/useAppearanceStore';

/** P2-A8: Default off; enable via env or server feature flag. */
const ENV_DYNAMIC_BG =
  typeof process.env.NEXT_PUBLIC_DYNAMIC_BG_ENABLED !== 'undefined'
    ? process.env.NEXT_PUBLIC_DYNAMIC_BG_ENABLED === 'true'
    : false;

/**
 * P2-A-3: Mood dynamic background. Single apply point (layout).
 * DoD: mood_label → bg; no mood → default; flag off → immediate; overlay for contrast; no flash (prefers-reduced-motion via globals.css).
 * Off when: NEXT_PUBLIC_DYNAMIC_BG_ENABLED=false or server flag off or no mood_label.
 */
export default function DynamicBackgroundWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: flags } = useFeatureFlags(ENV_DYNAMIC_BG);
  const latestMoodLabel = useAppearanceStore((s) => s.latestMoodLabel);
  const serverEnabled = !!flags?.flags?.dynamic_background_enabled;
  const enabled =
    ENV_DYNAMIC_BG && serverEnabled && !!latestMoodLabel?.trim();
  const theme = getThemeForMood(latestMoodLabel ?? undefined);
  const gradientClass = theme?.bgGradient;
  const overlayOpacity = theme?.overlayOpacity ?? 0;

  return (
    <div
      className={`min-h-screen transition-[background] duration-haven ease-haven ${
        enabled && gradientClass ? `bg-gradient-to-br ${gradientClass}` : 'bg-background'
      }`}
    >
      {overlayOpacity > 0 && enabled && (
        <div
          className="pointer-events-none fixed inset-0 z-0 bg-white dark:bg-black"
          style={{ opacity: overlayOpacity }}
          aria-hidden
        />
      )}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
