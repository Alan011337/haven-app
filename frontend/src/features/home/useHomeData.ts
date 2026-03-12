'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import {
  usePartnerStatus,
  useJournals,
  usePartnerJournals,
  useGamificationSummary,
  useOnboardingQuest,
  useSyncNudges,
  useFirstDelight,
} from '@/hooks/queries';
import { queryKeys } from '@/lib/query-keys';
import { getJournalSafetyBand } from '@/lib/safety';
import { logClientError } from '@/lib/safe-error-log';
import {
  invalidateHomeHeaderQueries,
  sortJournalsDesc,
} from '@/features/home/home-data-utils';
import { buildHomeBootstrapPlan, type HomeTab } from '@/lib/home-bootstrap-plan';
import {
  acknowledgeFirstDelight,
  deliverSyncNudge,
  markNotificationsRead,
  type FirstDelightResponse,
  type GamificationSummaryResponse,
  type OnboardingQuestResponse,
  type SyncNudgeItem,
  type SyncNudgesResponse,
} from '@/services/api-client';

export const PARTNER_SAFETY_BANNER_DISMISSED_KEY = 'partner_safety_banner_dismissed_id';

export const DEFAULT_GAMIFICATION_SUMMARY: GamificationSummaryResponse = {
  has_partner_context: false,
  streak_days: 0,
  best_streak_days: 0,
  streak_eligible_today: false,
  level: 1,
  level_points_total: 0,
  level_points_current: 0,
  level_points_target: 100,
  love_bar_percent: 0,
  level_title: 'Warm Starter',
  anti_cheat_enabled: true,
};

export const DEFAULT_ONBOARDING_QUEST: OnboardingQuestResponse = {
  enabled: false,
  has_partner_context: false,
  kill_switch_active: false,
  completed_steps: 0,
  total_steps: 7,
  progress_percent: 0,
  steps: [],
};

export const DEFAULT_SYNC_NUDGES: SyncNudgesResponse = {
  enabled: false,
  has_partner_context: false,
  kill_switch_active: false,
  nudge_cooldown_hours: 18,
  nudges: [],
};

export const DEFAULT_FIRST_DELIGHT: FirstDelightResponse = {
  enabled: false,
  has_partner_context: false,
  kill_switch_active: false,
  delivered: false,
  eligible: false,
  reason: 'disabled',
  dedupe_key: null,
  title: null,
  description: null,
  metadata: {},
};

const VALID_TABS: ReadonlySet<HomeTab> = new Set(['mine', 'partner', 'card']);

function tabFromSearchParams(searchParams: URLSearchParams): HomeTab {
  const tab = searchParams.get('tab');
  return tab && VALID_TABS.has(tab as HomeTab) ? (tab as HomeTab) : 'mine';
}

export function useHomeData() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const activeTab: HomeTab = tabFromSearchParams(searchParams);
  const initialHomeBootstrapPlan = buildHomeBootstrapPlan(activeTab, false);

  const { data: partnerStatus, refetch: refetchPartnerStatus } = usePartnerStatus();
  const journalsQuery = useJournals(initialHomeBootstrapPlan.loadMineJournals);
  const partnerJournalsQuery = usePartnerJournals(initialHomeBootstrapPlan.loadPartnerJournals);
  const criticalTabDataReady =
    activeTab === 'mine'
      ? journalsQuery.isFetched
      : activeTab === 'partner'
        ? partnerJournalsQuery.isFetched
        : true;
  const homeBootstrapPlan = buildHomeBootstrapPlan(
    activeTab,
    criticalTabDataReady,
  );
  const gamificationQuery = useGamificationSummary(homeBootstrapPlan.loadHeaderEnhancements);
  const onboardingQuery = useOnboardingQuest(homeBootstrapPlan.loadHeaderEnhancements);
  const syncNudgesQuery = useSyncNudges(homeBootstrapPlan.loadHeaderEnhancements);
  const firstDelightQuery = useFirstDelight(homeBootstrapPlan.loadHeaderEnhancements);

  const [partnerReadAtVersion, setPartnerReadAtVersion] = useState(0);
  const statusRefreshInFlightRef = useRef<Promise<void> | null>(null);
  const loadDataInFlightRef = useRef<Promise<void> | null>(null);


  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab === null) return;
    if (VALID_TABS.has(tab as HomeTab)) return;
    const params = new URLSearchParams(searchParams);
    params.delete('tab');
    const href = params.toString() ? `${pathname}?${params.toString()}` : pathname;
    router.replace(href, { scroll: false });
  }, [pathname, router, searchParams]);

  const savingsScore = partnerStatus?.current_score ?? 0;
  const hasNewPartnerContent = useMemo(() => {
    if (!partnerStatus) return false;
    if (activeTab === 'partner') return false;
    if (Number(partnerStatus.unread_notification_count ?? 0) > 0) return true;
    if (partnerStatus.latest_journal_at && typeof localStorage !== 'undefined') {
      const lastRead = localStorage.getItem('partner_last_read_at');
      const latestTime = new Date(partnerStatus.latest_journal_at).getTime();
      const lastReadTime = lastRead ? new Date(lastRead).getTime() : 0;
      if (latestTime > lastReadTime) return true;
    }
    return false;
  // Intentionally omit full deps: partnerReadAtVersion is the trigger for "partner read" recompute; adding partnerStatus.latest_journal_at etc. would not change behavior.
  // eslint-disable-next-line react-hooks/exhaustive-deps -- partnerReadAtVersion forces recompute when partner read timestamp updated
  }, [partnerStatus, activeTab, partnerReadAtVersion]);

  const gamificationSummary: GamificationSummaryResponse = useMemo(() => {
    const data = gamificationQuery.data;
    if (!data) return DEFAULT_GAMIFICATION_SUMMARY;
    return {
      ...DEFAULT_GAMIFICATION_SUMMARY,
      ...data,
      love_bar_percent: Math.max(
        0,
        Math.min(100, Number(data.love_bar_percent ?? DEFAULT_GAMIFICATION_SUMMARY.love_bar_percent)),
      ),
    };
  }, [gamificationQuery.data]);
  const onboardingQuest: OnboardingQuestResponse = useMemo(() => {
    const data = onboardingQuery.data;
    if (!data) return DEFAULT_ONBOARDING_QUEST;
    return {
      ...DEFAULT_ONBOARDING_QUEST,
      ...data,
      progress_percent: Math.max(
        0,
        Math.min(100, Number(data.progress_percent ?? DEFAULT_ONBOARDING_QUEST.progress_percent)),
      ),
      steps: Array.isArray(data.steps) ? data.steps : DEFAULT_ONBOARDING_QUEST.steps,
    };
  }, [onboardingQuery.data]);
  const syncNudges: SyncNudgesResponse = useMemo(() => {
    const data = syncNudgesQuery.data;
    if (!data) return DEFAULT_SYNC_NUDGES;
    return {
      ...DEFAULT_SYNC_NUDGES,
      ...data,
      nudges: Array.isArray(data.nudges) ? data.nudges : DEFAULT_SYNC_NUDGES.nudges,
    };
  }, [syncNudgesQuery.data]);
  const firstDelight: FirstDelightResponse = useMemo(() => {
    const data = firstDelightQuery.data;
    if (!data) return DEFAULT_FIRST_DELIGHT;
    return {
      ...DEFAULT_FIRST_DELIGHT,
      ...data,
      metadata:
        data.metadata && typeof data.metadata === 'object' && !Array.isArray(data.metadata)
          ? data.metadata
          : DEFAULT_FIRST_DELIGHT.metadata,
    };
  }, [firstDelightQuery.data]);

  const myJournals = useMemo(() => sortJournalsDesc(journalsQuery.data), [journalsQuery.data]);

  const partnerJournals = useMemo(
    () => sortJournalsDesc(partnerJournalsQuery.data),
    [partnerJournalsQuery.data],
  );
  const mineTimelineUnavailable = journalsQuery.isError && myJournals.length === 0;
  const partnerTimelineUnavailable =
    partnerJournalsQuery.isError && partnerJournals.length === 0;

  const loading =
    (activeTab === 'mine' && journalsQuery.isLoading) ||
    (activeTab === 'partner' && partnerJournalsQuery.isLoading);

  const [partnerSafetyBanner, setPartnerSafetyBanner] = useState<{
    latestSevereId: string;
    severeCount: number;
  } | null>(null);

  const checkStatus = useCallback(async () => {
    if (statusRefreshInFlightRef.current) {
      await statusRefreshInFlightRef.current;
      return;
    }
    const task = (async () => {
      try {
        await refetchPartnerStatus();
      } catch (error) {
        logClientError('home-status-check-failed', error);
      }
    })();
    statusRefreshInFlightRef.current = task;
    try {
      await task;
    } finally {
      statusRefreshInFlightRef.current = null;
    }
  }, [refetchPartnerStatus]);

  useEffect(() => {
    const data = partnerJournalsQuery.data;
    if (!Array.isArray(data) || data.length === 0 || activeTab !== 'partner') return;
    const sorted = sortJournalsDesc(data);
    const newestDate = sorted[0].created_at;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('partner_last_read_at', newestDate);
      queueMicrotask(() => setPartnerReadAtVersion((v) => v + 1));
    }
    const severeJournals = sorted.filter((item) => getJournalSafetyBand(item) === 'severe');
    if (severeJournals.length > 0) {
      const latestSevereId = severeJournals[0].id;
      const dismissedId =
        typeof localStorage !== 'undefined'
          ? localStorage.getItem(PARTNER_SAFETY_BANNER_DISMISSED_KEY)
          : null;
      if (dismissedId === latestSevereId) {
        setPartnerSafetyBanner(null);
      } else {
        setPartnerSafetyBanner({ latestSevereId, severeCount: severeJournals.length });
      }
    } else {
      setPartnerSafetyBanner(null);
    }
  }, [activeTab, partnerJournalsQuery.data]);

  const loadData = useCallback(async () => {
    if (loadDataInFlightRef.current) {
      await loadDataInFlightRef.current;
      return;
    }
    const task = (async () => {
      // ✅ 使用 AuthContext 檢查用戶是否登入，而不是 localStorage
      // AuthContext 會在應用初始化時自動驗證令牌（通過 /users/me API）
      await checkStatus();
      // Invalidate header queries so useQuery refetches in background (avoids blocking on 4 refetches)
      await invalidateHomeHeaderQueries(queryClient);

      if (activeTab === 'card') {
        try {
          await markNotificationsRead('card');
          await refetchPartnerStatus();
        } catch (error) {
          logClientError('home-mark-card-notifications-read-failed', error);
        }
        return;
      }

      if (activeTab === 'mine') {
        await queryClient.invalidateQueries({ queryKey: queryKeys.journals() });
      } else if (activeTab === 'partner') {
        await queryClient.invalidateQueries({ queryKey: queryKeys.partnerJournals() });
        await refetchPartnerStatus();
        try {
          await markNotificationsRead('journal');
        } catch (err) {
          logClientError('home-mark-journal-notifications-read-failed', err);
        }
      }
    })();
    loadDataInFlightRef.current = task;
    try {
      await task;
    } finally {
      loadDataInFlightRef.current = null;
    }
  }, [
    activeTab,
    checkStatus,
    queryClient,
    refetchPartnerStatus,
  ]);

  const nextOnboardingStep = onboardingQuest.steps.find((step) => !step.completed);
  const primarySyncNudge = syncNudges.nudges.find((item: SyncNudgeItem) => item.eligible);
  const showFirstDelightCard =
    firstDelight.enabled && firstDelight.eligible && Boolean(firstDelight.dedupe_key);
  const previousTabRef = useRef<HomeTab | null>(null);

  useEffect(() => {
    if (previousTabRef.current === activeTab) {
      return;
    }
    previousTabRef.current = activeTab;
    if (activeTab !== 'partner' && activeTab !== 'card') {
      return;
    }
    const notificationScope = activeTab === 'partner' ? 'journal' : 'card';
    void (async () => {
      try {
        await markNotificationsRead(notificationScope);
        await refetchPartnerStatus();
      } catch (error) {
        logClientError(`home-mark-${notificationScope}-notifications-read-failed`, error);
      }
    })();
  }, [activeTab, refetchPartnerStatus]);

  const acknowledgeSyncNudge = useCallback(async () => {
    if (!primarySyncNudge) return;
    try {
      await deliverSyncNudge(primarySyncNudge.nudge_type, {
        dedupe_key: primarySyncNudge.dedupe_key,
        source: 'home_header',
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.syncNudges() });
    } catch (error) {
      logClientError('home-sync-nudge-acknowledge-failed', error);
    }
  }, [primarySyncNudge, queryClient]);

  const acknowledgeFirstDelightCard = useCallback(async () => {
    if (!firstDelight.dedupe_key) return;
    try {
      await acknowledgeFirstDelight({
        dedupe_key: firstDelight.dedupe_key,
        source: 'home_header',
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.firstDelight() });
    } catch (error) {
      logClientError('home-first-delight-acknowledge-failed', error);
    }
  }, [firstDelight.dedupe_key, queryClient]);

  const handleDismissPartnerSafetyBanner = useCallback(() => {
    setPartnerSafetyBanner((current) => {
      if (current) {
        localStorage.setItem(PARTNER_SAFETY_BANNER_DISMISSED_KEY, current.latestSevereId);
      }
      return null;
    });
  }, []);

  const handleTabChange = useCallback(
    (tab: HomeTab) => {
      const params = new URLSearchParams(searchParams);
      if (tab === 'mine') {
        params.delete('tab');
      } else {
        params.set('tab', tab);
      }
      const query = params.toString();
      const href = query ? `${pathname}?${query}` : pathname;
      router.push(href, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const getTabStyle = useCallback(
    (tabName: string) => {
      const isActive = activeTab === tabName;
      const baseStyle =
        'relative flex items-center gap-2 rounded-[1.15rem] px-5 py-3 text-sm font-medium transition-all duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';

      if (isActive) {
        return `${baseStyle} border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(250,246,240,0.82))] text-card-foreground shadow-soft`;
      }

      return `${baseStyle} border border-transparent text-muted-foreground hover:border-white/55 hover:bg-white/60 hover:text-card-foreground`;
    },
    [activeTab],
  );

  return {
    activeTab,
    myJournals,
    partnerJournals,
    loading,
    mineTimelineUnavailable,
    partnerTimelineUnavailable,
    savingsScore,
    gamificationSummary,
    onboardingQuest,
    syncNudges,
    firstDelight,
    hasNewPartnerContent,
    partnerSafetyBanner,
    nextOnboardingStep,
    primarySyncNudge,
    showFirstDelightCard,
    secondaryContentReady: homeBootstrapPlan.loadMineSecondaryCards,
    loadData,
    handleTabChange,
    getTabStyle,
    handleDismissPartnerSafetyBanner,
    acknowledgeSyncNudge,
    acknowledgeFirstDelightCard,
  };
}
