/**
 * P2-A11: Haptic feedback service — single API for ritual events.
 * Web: uses navigator.vibrate when available; no-op otherwise (no throw).
 * Future: Capacitor Haptics can be plugged in here without changing call sites.
 */

export type HapticStrength = 'light' | 'medium';

export type HapticsOptions = {
  enabled?: boolean;
  strength?: HapticStrength;
};

const HAPTIC_DRAW_MS = 15;
const HAPTIC_UNLOCK_MS = 20;
const HAPTIC_TAP_MS = 10;

function strengthScale(baseMs: number, strength: HapticStrength): number {
  return strength === 'light' ? Math.round(baseMs * 0.6) : baseMs;
}

function vibrate(ms: number): void {
  if (typeof navigator === 'undefined') return;
  try {
    if (navigator.vibrate) {
      navigator.vibrate(ms);
    }
  } catch {
    // no-op: unsupported or permission; do not throw
  }
}

export type HapticEvent = 'draw' | 'unlock' | 'tap';

/**
 * Trigger haptic feedback for a ritual event.
 * Respects options.enabled; when false or unsupported, does nothing (no error).
 */
export function triggerHaptic(
  event: HapticEvent,
  options?: HapticsOptions
): void {
  const enabled = options?.enabled !== false;
  if (!enabled) return;

  const strength = options?.strength ?? 'medium';
  switch (event) {
    case 'draw':
      vibrate(strengthScale(HAPTIC_DRAW_MS, strength));
      break;
    case 'unlock':
      vibrate(strengthScale(HAPTIC_UNLOCK_MS, strength));
      break;
    case 'tap':
      vibrate(strengthScale(HAPTIC_TAP_MS, strength));
      break;
    default:
      break;
  }
}

export const hapticsService = {
  trigger: triggerHaptic,
};
