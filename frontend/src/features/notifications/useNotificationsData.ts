'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { logClientError } from '@/lib/safe-error-log';
import { buildAdaptiveRefetchInterval } from '@/lib/polling-policy';
import {
  fetchNotificationStats,
  fetchNotifications,
  markNotificationRead,
  markNotificationsRead,
  retryNotification,
  type NotificationDailyStatsItem,
  type NotificationEventItem,
  type NotificationFilters,
} from '@/services/api-client';

const NOTIFICATIONS_STALE_MS = 30_000;
const NOTIFICATIONS_POLL_MS = 20_000;
const notificationsRefetchInterval = buildAdaptiveRefetchInterval(NOTIFICATIONS_POLL_MS, {
  hiddenMultiplier: 4,
});

type NotificationActionFilter =
  | 'ALL'
  | 'JOURNAL'
  | 'CARD'
  | 'COOLDOWN_STARTED'
  | 'MEDIATION_INVITE';

export const formatTime = (value: string) =>
  new Date(value).toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

export const getTitle = (item: NotificationEventItem) => {
  if (item.action_type === 'JOURNAL') return '伴侶新增了日記';
  if (item.action_type === 'MEDIATION_INVITE') return '調解模式邀請';
  if (item.action_type === 'COOLDOWN_STARTED') return '伴侶啟動了冷卻';
  return '伴侶更新了卡片回覆';
};

export const getDescription = (item: NotificationEventItem) => {
  if (item.status === 'QUEUED') return '通知已排入佇列，稍後會自動送達。';
  if (item.status === 'FAILED') return '通知投遞失敗，可稍後重試。';
  if (item.status === 'THROTTLED') return '同類通知在冷卻時間內已被節流。';
  if (item.action_type === 'JOURNAL') return '前往伴侶心聲查看最新內容。';
  if (item.action_type === 'MEDIATION_INVITE') return '填寫三題換位思考，可查看彼此心聲與下次 SOP。';
  if (item.action_type === 'COOLDOWN_STARTED') return '伴侶需要暫停一下，建議稍後再好好聊。';
  return '前往每日共感或牌組查看新回覆。';
};

export const getActionLink = (item: NotificationEventItem): string => {
  if (item.action_type === 'JOURNAL') return '/?tab=partner';
  if (item.action_type === 'MEDIATION_INVITE') return '/mediation';
  if (item.action_type === 'COOLDOWN_STARTED') return '/settings';
  return '/?tab=card';
};

export function useNotificationsData() {
  const queryClient = useQueryClient();
  const [hoveredDay, setHoveredDay] = useState<NotificationDailyStatsItem | null>(null);
  const [statsWindowDays, setStatsWindowDays] = useState<7 | 30>(7);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [actionFilter, setActionFilter] = useState<NotificationActionFilter>('ALL');
  const [statusFilter, setStatusFilter] = useState<
    'ALL' | 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED'
  >('ALL');
  const [errorReasonInput, setErrorReasonInput] = useState('');
  const [errorReasonFilter, setErrorReasonFilter] = useState('');

  const listFilters: NotificationFilters = useMemo(
    () => ({
      unread_only: onlyUnread,
      action_type: actionFilter === 'ALL' ? undefined : actionFilter,
      status: statusFilter === 'ALL' ? undefined : statusFilter,
      error_reason: errorReasonFilter || undefined,
    }),
    [actionFilter, errorReasonFilter, onlyUnread, statusFilter],
  );

  const listQuery = useQuery({
    queryKey: queryKeys.notifications({ limit: 50, ...listFilters }),
    queryFn: () => fetchNotifications({ limit: 50, ...listFilters }),
    staleTime: NOTIFICATIONS_STALE_MS,
    refetchInterval: notificationsRefetchInterval,
  });

  const statsQuery = useQuery({
    queryKey: queryKeys.notificationStats({
      window_days: statsWindowDays,
      ...listFilters,
    }),
    queryFn: () =>
      fetchNotificationStats({ window_days: statsWindowDays, ...listFilters }),
    staleTime: NOTIFICATIONS_STALE_MS,
    refetchInterval: notificationsRefetchInterval,
  });

  const items = listQuery.data ?? [];
  const stats = statsQuery.data ?? null;
  const loading = listQuery.isLoading || statsQuery.isLoading;
  const refreshing =
    (listQuery.isFetching || statsQuery.isFetching) && !listQuery.isLoading && !statsQuery.isLoading;
  const listError = listQuery.isError;
  const statsError = statsQuery.isError;
  const hasDiagnosticsData = Boolean(statsQuery.data);

  const unreadCount = useMemo(
    () => (listQuery.data ?? []).filter((item) => !item.is_read).length,
    [listQuery.data],
  );

  const handleRefresh = useCallback(async () => {
    await Promise.all([listQuery.refetch(), statsQuery.refetch()]);
  }, [listQuery, statsQuery]);

  const deliveryRate = useMemo(() => {
    if (!stats || stats.total_count <= 0) return 0;
    return Math.round((stats.sent_count / stats.total_count) * 100);
  }, [stats]);

  const healthScore = useMemo(() => {
    if (!stats || stats.total_count <= 0) return 100;
    const weighted =
      stats.sent_count * 1 +
      stats.queued_count * 0.7 +
      stats.throttled_count * 0.4 +
      stats.failed_count * 0;
    return Math.max(0, Math.min(100, Math.round((weighted / stats.total_count) * 100)));
  }, [stats]);

  const trendMax = useMemo(() => {
    const windowDaily = stats?.window_daily ?? [];
    const maxCount = Math.max(...windowDaily.map((item) => item.total_count), 0);
    return Math.max(maxCount, 1);
  }, [stats]);

  const focusedDay: NotificationDailyStatsItem | null =
    hoveredDay ?? stats?.window_daily?.[stats.window_daily.length - 1] ?? null;

  const handleMarkAllRead = useCallback(async () => {
    try {
      const scopedActionType =
        actionFilter === 'JOURNAL'
          ? 'journal'
          : actionFilter === 'CARD'
            ? 'card'
            : undefined;

      if (
        actionFilter !== 'ALL' &&
        actionFilter !== 'JOURNAL' &&
        actionFilter !== 'CARD'
      ) {
        return;
      }

      await markNotificationsRead(scopedActionType);
      await queryClient.invalidateQueries({ queryKey: queryKeys.notifications() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.notificationStats() });
    } catch (error) {
      logClientError('notifications-mark-all-read-failed', error);
    }
  }, [actionFilter, queryClient]);

  const handleToggleUnread = useCallback(() => {
    setOnlyUnread((prev) => !prev);
  }, []);

  const handleMarkOneRead = useCallback(
    async (notificationId: string) => {
      try {
        await markNotificationRead(notificationId);
        await queryClient.invalidateQueries({ queryKey: queryKeys.notifications() });
        await queryClient.invalidateQueries({ queryKey: queryKeys.notificationStats() });
      } catch (error) {
        logClientError('notifications-mark-one-read-failed', error);
      }
    },
    [queryClient],
  );

  const handleActionFilterChange = useCallback((nextFilter: NotificationActionFilter) => {
    setActionFilter(nextFilter);
  }, []);

  const handleStatusFilterChange = useCallback(
    (nextFilter: 'ALL' | 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED') => {
      setStatusFilter(nextFilter);
    },
    [],
  );

  const handleErrorReasonFilterChange = useCallback((value: string) => {
    setErrorReasonInput(value);
  }, []);

  const handleResetFilters = useCallback(() => {
    setOnlyUnread(false);
    setActionFilter('ALL');
    setStatusFilter('ALL');
    setErrorReasonInput('');
    setErrorReasonFilter('');
  }, []);

  const handleWindowDaysChange = useCallback((nextWindow: 7 | 30) => {
    setHoveredDay(null);
    setStatsWindowDays(nextWindow);
  }, []);

  const handleRetryDelivery = useCallback(
    async (notificationId: string) => {
      try {
        setRetryingId(notificationId);
        await retryNotification(notificationId);
        await queryClient.invalidateQueries({ queryKey: queryKeys.notifications() });
        await queryClient.invalidateQueries({ queryKey: queryKeys.notificationStats() });
      } catch (error) {
        logClientError('notifications-retry-failed', error);
      } finally {
        setRetryingId(null);
      }
    },
    [queryClient],
  );

  const setStatusAndErrorReason = useCallback(
    (status: 'ALL' | 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED', reason: string) => {
      setStatusFilter(status);
      setErrorReasonInput(reason);
      setErrorReasonFilter(reason);
    },
    [],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setErrorReasonFilter(errorReasonInput.trim());
    }, 350);
    return () => window.clearTimeout(timer);
  }, [errorReasonInput]);

  const load = useCallback(async () => {
    await Promise.all([listQuery.refetch(), statsQuery.refetch()]);
  }, [listQuery, statsQuery]);

  return {
    items,
    stats,
    listError,
    statsError,
    hasDiagnosticsData,
    hoveredDay,
    setHoveredDay,
    statsWindowDays,
    loading,
    refreshing,
    retryingId,
    onlyUnread,
    actionFilter,
    statusFilter,
    errorReasonInput,
    unreadCount,
    deliveryRate,
    healthScore,
    trendMax,
    focusedDay,
    load,
    handleRefresh,
    handleMarkAllRead,
    handleToggleUnread,
    handleMarkOneRead,
    handleActionFilterChange,
    handleStatusFilterChange,
    handleErrorReasonFilterChange,
    handleResetFilters,
    handleWindowDaysChange,
    handleRetryDelivery,
    setStatusAndErrorReason,
  };
}
