/**
 * TanStack Query key factory. Single source of truth for cache keys.
 * Web and native must use the same keys for consistency if they share cache later.
 */

export const queryKeys = {
  partnerStatus: () => ['partnerStatus'] as const,
  journals: () => ['journals'] as const,
  journalDetail: (journalId: string) => ['journalDetail', journalId] as const,
  partnerJournals: () => ['partnerJournals'] as const,
  gamificationSummary: () => ['gamificationSummary'] as const,
  onboardingQuest: () => ['onboardingQuest'] as const,
  syncNudges: () => ['syncNudges'] as const,
  firstDelight: () => ['firstDelight'] as const,
  deckHistory: (category: string, range: string, sort: string, q: string) =>
    ['deckHistory', category, range, sort, q] as const,
  deckHistoryInfinite: (category: string, revealedFrom: string, revealedTo: string) =>
    ['deckHistoryInfinite', category, revealedFrom, revealedTo] as const,
  deckHistorySummary: (category: string, revealedFrom: string, revealedTo: string) =>
    ['deckHistorySummary', category, revealedFrom, revealedTo] as const,
  notifications: (params?: { limit?: number; offset?: number; [key: string]: unknown }) =>
    ['notifications', params ?? {}] as const,
  notificationStats: (params?: { window_days?: number; [key: string]: unknown }) =>
    ['notificationStats', params ?? {}] as const,
  user: () => ['user'] as const,
  featureFlags: () => ['featureFlags'] as const,
  loveMapCards: () => ['loveMapCards'] as const,
  loveMapNotes: () => ['loveMapNotes'] as const,
  loveMapSystem: () => ['loveMapSystem'] as const,
  mediationStatus: () => ['mediationStatus'] as const,
  blueprint: () => ['blueprint'] as const,
  cooldownStatus: () => ['cooldownStatus'] as const,
  dailySyncStatus: () => ['dailySyncStatus'] as const,
  dailyStatus: () => ['dailyStatus'] as const,
  deckCardCounts: () => ['deckCardCounts'] as const,
} as const;
