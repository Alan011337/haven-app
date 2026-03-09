/**
 * P2-A: Mood theme for dynamic background. Single source: mood_label -> bg + optional overlay for contrast.
 * Server feature flag or NEXT_PUBLIC_DYNAMIC_BG_ENABLED controls visibility.
 */
export type MoodTheme = {
  bgGradient: string;
  accent?: string;
  /** 0–1; when set, add overlay for readability (e.g. dark gradient). */
  overlayOpacity?: number;
};

/** Map mood_label (partial match key) to theme. Semantic tokens only (ART-DIRECTION). */
export const MOOD_THEME_MAP: Record<string, MoodTheme> = {
  calm: { bgGradient: 'from-chart-2/25 via-chart-2/10 to-chart-2/5' },
  peaceful: { bgGradient: 'from-chart-2/25 via-chart-2/10 to-chart-2/5' },
  serene: { bgGradient: 'from-chart-3/20 via-muted to-chart-3/10' },
  平靜: { bgGradient: 'from-chart-2/25 via-chart-2/10 to-chart-2/5' },
  寧靜: { bgGradient: 'from-chart-3/20 via-muted to-chart-3/10' },
  happy: { bgGradient: 'from-chart-4/25 via-chart-5/10 to-chart-4/5' },
  joy: { bgGradient: 'from-chart-5/25 via-chart-4/10 to-chart-5/5' },
  開心: { bgGradient: 'from-chart-4/25 via-chart-5/10 to-chart-4/5' },
  快樂: { bgGradient: 'from-chart-5/25 via-chart-4/10 to-chart-5/5' },
  sad: { bgGradient: 'from-chart-3/15 via-muted to-chart-3/10', overlayOpacity: 0.03 },
  melancholy: { bgGradient: 'from-muted via-chart-3/10 to-chart-1/10', overlayOpacity: 0.03 },
  憂鬱: { bgGradient: 'from-chart-3/15 via-muted to-chart-3/10', overlayOpacity: 0.03 },
  低落: { bgGradient: 'from-muted via-chart-3/10 to-chart-1/10', overlayOpacity: 0.03 },
  energetic: { bgGradient: 'from-chart-4/30 via-depth-3/15 to-chart-4/10' },
  熱烈: { bgGradient: 'from-chart-4/30 via-depth-3/15 to-chart-4/10' },
  anxious: { bgGradient: 'from-chart-4/15 via-muted to-chart-4/10' },
  焦慮: { bgGradient: 'from-chart-4/15 via-muted to-chart-4/10' },
  grateful: { bgGradient: 'from-chart-1/20 via-chart-1/10 to-chart-1/5' },
  感恩: { bgGradient: 'from-chart-1/20 via-chart-1/10 to-chart-1/5' },
};

/** Legacy: gradient-only lookup (uses MOOD_THEME_MAP). */
export const MOOD_TO_GRADIENT: Record<string, string> = Object.fromEntries(
  Object.entries(MOOD_THEME_MAP).map(([k, v]) => [k, v.bgGradient])
);

const DEFAULT_GRADIENT = 'from-muted via-background to-muted';

export function getThemeForMood(moodLabel: string | null | undefined): MoodTheme | null {
  if (!moodLabel || typeof moodLabel !== 'string') return null;
  const normalized = moodLabel.trim().toLowerCase();
  for (const [key, theme] of Object.entries(MOOD_THEME_MAP)) {
    if (normalized.includes(key.toLowerCase())) return theme;
  }
  return null;
}

/**
 * Resolve mood_label to gradient class string. Uses partial match (includes) for flexibility.
 */
export function getGradientForMood(moodLabel: string | null | undefined): string {
  const theme = getThemeForMood(moodLabel);
  return theme?.bgGradient ?? DEFAULT_GRADIENT;
}
