import type { Journal } from '@/types';

export type SafetyBand = 'normal' | 'elevated' | 'severe';

export function normalizeSafetyTier(input: unknown): number {
  const value = Number(input ?? 0);
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 3) return 3;
  return Math.floor(value);
}

export function resolveSafetyBand(input: unknown): SafetyBand {
  const tier = normalizeSafetyTier(input);
  if (tier >= 2) return 'severe';
  if (tier === 1) return 'elevated';
  return 'normal';
}

export function getJournalSafetyBand(journal: Pick<Journal, 'safety_tier'>): SafetyBand {
  return resolveSafetyBand(journal.safety_tier);
}
