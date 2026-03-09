/**
 * Client-only store for appearance preferences driven by server/data.
 * Used by Dynamic Background: latest journal mood_label for gradient theme.
 * P2-A-2: cardGlowEnabled — Glow 可關閉（設定/flag）.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type AppearanceState = {
  latestMoodLabel: string | null;
  setLatestMoodLabel: (label: string | null) => void;
  /** When false, card reveal glow is disabled (DoD: Glow 可關閉). */
  cardGlowEnabled: boolean;
  setCardGlowEnabled: (enabled: boolean) => void;
  /** P2-A-5: Haptic 設定開關 + 強度. */
  hapticsEnabled: boolean;
  hapticStrength: 'light' | 'medium';
  setHapticsEnabled: (enabled: boolean) => void;
  setHapticStrength: (strength: 'light' | 'medium') => void;
  /** P2-A-6: 音效 mute toggle. */
  soundEnabled: boolean;
  setSoundEnabled: (enabled: boolean) => void;
};

export const useAppearanceStore = create<AppearanceState>()(
  persist(
    (set) => ({
      latestMoodLabel: null,
      setLatestMoodLabel: (label) => set({ latestMoodLabel: label }),
      cardGlowEnabled: true,
      setCardGlowEnabled: (enabled) => set({ cardGlowEnabled: enabled }),
      hapticsEnabled: true,
      hapticStrength: 'medium',
      setHapticsEnabled: (enabled) => set({ hapticsEnabled: enabled }),
      setHapticStrength: (strength) => set({ hapticStrength: strength }),
      soundEnabled: true,
      setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),
    }),
    {
      name: 'haven-appearance',
      partialize: (s) => ({
        cardGlowEnabled: s.cardGlowEnabled,
        hapticsEnabled: s.hapticsEnabled,
        hapticStrength: s.hapticStrength,
        soundEnabled: s.soundEnabled,
      }),
    }
  )
);
