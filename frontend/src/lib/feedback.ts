/**
 * P2-A: Haptic + Audio feedback for ritual moments (draw card, unlock, submit success).
 * Haptic: via hapticsService (web no-op when unsupported; future Capacitor plug-in).
 * Audio: Web Audio API generated tones (no asset files); respects user motion/sound prefs when possible.
 */

import { hapticsService } from '@/services/hapticsService';

import type { HapticStrength } from '@/services/hapticsService';

export type { HapticStrength };

let audioContext: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioContext) {
    try {
      audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    } catch {
      return null;
    }
  }
  return audioContext;
}

/** Light paper-like sweep (draw card). Optional: load /public/audio/v1/draw.mp3 when available; fallback: procedural tone. */
export function playDrawSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(180, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.06);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.06);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.07);
  } catch {
    // ignore
  }
}

/** Short chime (unlock / reveal). Optional: load /public/audio/v1/unlock.mp3 when available; fallback: procedural tone. */
export function playUnlockSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;
  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(640, ctx.currentTime);
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.05);
    osc.frequency.setValueAtTime(720, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.26);
  } catch {
    // ignore
  }
}

const COOLDOWN_DRAW_MS = 180;
const COOLDOWN_UNLOCK_MS = 280;
let lastDrawAt = 0;
let lastUnlockAt = 0;

export type FeedbackOptions = {
  hapticsEnabled?: boolean;
  hapticStrength?: HapticStrength;
  /** P2-A-6: when false, skip audio (mute). */
  soundEnabled?: boolean;
};

export const feedback = {
  /** Call after successful card draw. Options from useAppearanceStore. */
  onDrawSuccess(opts?: FeedbackOptions): void {
    hapticsService.trigger('draw', {
      enabled: opts?.hapticsEnabled !== false,
      strength: opts?.hapticStrength ?? 'medium',
    });
    if (opts?.soundEnabled !== false) {
      const now = typeof performance !== 'undefined' ? performance.now() : 0;
      if (now - lastDrawAt >= COOLDOWN_DRAW_MS) {
        lastDrawAt = now;
        playDrawSound();
      }
    }
  },
  /** Call when answer is submitted and unlock/reveal happens. */
  onUnlockSuccess(opts?: FeedbackOptions): void {
    hapticsService.trigger('unlock', {
      enabled: opts?.hapticsEnabled !== false,
      strength: opts?.hapticStrength ?? 'medium',
    });
    if (opts?.soundEnabled !== false) {
      const now = typeof performance !== 'undefined' ? performance.now() : 0;
      if (now - lastUnlockAt >= COOLDOWN_UNLOCK_MS) {
        lastUnlockAt = now;
        playUnlockSound();
      }
    }
  },
  /** Optional: short tap (e.g. button submit). */
  onTap(opts?: FeedbackOptions): void {
    hapticsService.trigger('tap', {
      enabled: opts?.hapticsEnabled !== false,
      strength: opts?.hapticStrength ?? 'medium',
    });
  },
};
