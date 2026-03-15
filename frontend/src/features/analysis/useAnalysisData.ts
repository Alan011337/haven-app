'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/use-auth';
import { useGamificationSummary } from '@/hooks/queries/useHomeQueries';
import { useJournals } from '@/hooks/queries/useJournals';
import { useDeckCardCounts } from '@/hooks/queries/useDeckCardCounts';
import { useDeckHistorySummaryQuery } from '@/hooks/queries/useDeckHistoryQueries';
import { fetchWeeklyReport } from '@/services/api-client';
import { memoryService } from '@/services/memoryService';

/** Stale times — analysis data is retrospective, changes slowly. */
const WEEKLY_REPORT_STALE_MS = 120_000;
const RELATIONSHIP_REPORT_STALE_MS = 300_000;

export interface MoodEntry {
  label: string;
  count: number;
}

export interface CategoryEntry {
  category: string;
  answered: number;
  total: number;
}

export function useAnalysisData() {
  const { user } = useAuth();
  const enabled = !!user;

  // ── Reuse existing hooks ──
  const gamification = useGamificationSummary(enabled);
  const journals = useJournals(enabled);
  const deckCardCounts = useDeckCardCounts();
  const deckSummary = useDeckHistorySummaryQuery(undefined, {});

  // ── New queries (existing fetch functions, page-local query keys) ──
  const weeklyReport = useQuery({
    queryKey: ['weeklyReport'] as const,
    queryFn: fetchWeeklyReport,
    staleTime: WEEKLY_REPORT_STALE_MS,
    enabled,
  });

  const relationshipReport = useQuery({
    queryKey: ['relationshipReport', 'month'] as const,
    queryFn: () => memoryService.getReport('month'),
    staleTime: RELATIONSHIP_REPORT_STALE_MS,
    enabled,
  });

  // ── Derived: mood distribution from recent journals ──
  const moodDistribution = useMemo<MoodEntry[]>(() => {
    const entries = journals.data ?? [];
    const recent = entries.slice(0, 20);
    const counts = new Map<string, number>();
    for (const j of recent) {
      if (j.mood_label) {
        const label = j.mood_label.trim();
        counts.set(label, (counts.get(label) ?? 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([label, count]) => ({ label, count }))
      .sort((a, b) => b.count - a.count);
  }, [journals.data]);

  const moodDateRange = useMemo<{ from: string; to: string } | null>(() => {
    const entries = journals.data ?? [];
    const recent = entries.slice(0, 20).filter((j) => j.mood_label);
    if (recent.length < 3) return null;
    const dates = recent.map((j) => j.created_at).sort();
    return {
      from: new Date(dates[0]).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' }),
      to: new Date(dates[dates.length - 1]).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' }),
    };
  }, [journals.data]);

  // ── Derived: category exploration from deck stats ──
  // useDeckCardCounts returns Record<string, DeckCardCount>
  const categoryExploration = useMemo<{
    explored: number;
    total: number;
    categories: CategoryEntry[];
  }>(() => {
    const countsMap = deckCardCounts.data ?? {};
    const entries = Object.values(countsMap);
    const explored = entries.filter((c) => c.answered_cards > 0).length;
    return {
      explored,
      total: entries.length,
      categories: entries.map((c) => ({
        category: c.category,
        answered: c.answered_cards,
        total: c.total_cards,
      })),
    };
  }, [deckCardCounts.data]);

  // ── Global empty check ──
  const isFullyEmpty = useMemo(() => {
    const noReport =
      !relationshipReport.data?.emotion_trend_summary &&
      !relationshipReport.data?.health_suggestion;
    const noWeekly =
      !weeklyReport.data || weeklyReport.data.daily_sync_days_filled === 0;
    const noGamification =
      !gamification.data || gamification.data.streak_days === 0;
    const noDecks = !deckSummary.data || deckSummary.data.total_records === 0;
    const noMoods = moodDistribution.length < 3;
    return noReport && noWeekly && noGamification && noDecks && noMoods;
  }, [
    relationshipReport.data,
    weeklyReport.data,
    gamification.data,
    deckSummary.data,
    moodDistribution,
  ]);

  // ── Loading states ──
  const isLoading =
    weeklyReport.isLoading ||
    relationshipReport.isLoading ||
    gamification.isLoading ||
    journals.isLoading ||
    deckCardCounts.isLoading ||
    deckSummary.isLoading;

  return {
    // Raw data
    weeklyReport: weeklyReport.data ?? null,
    weeklyReportLoading: weeklyReport.isLoading,

    relationshipReport: relationshipReport.data ?? null,
    relationshipReportLoading: relationshipReport.isLoading,

    gamification: gamification.data ?? null,
    gamificationLoading: gamification.isLoading,

    deckSummary: deckSummary.data ?? null,
    deckSummaryLoading: deckSummary.isLoading,

    // Derived
    moodDistribution,
    moodDateRange,
    categoryExploration,
    isFullyEmpty,
    isLoading,
  };
}
