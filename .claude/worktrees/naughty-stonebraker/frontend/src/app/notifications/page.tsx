'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Bell,
  BookOpen,
  Check,
  CheckCheck,
  Clock3,
  MailWarning,
  MessageCircleMore,
  RefreshCw,
} from 'lucide-react';

import Sidebar from '@/components/layout/Sidebar';
import {
  NotificationFilters,
  NotificationDailyStatsItem,
  fetchNotificationStats,
  fetchNotifications,
  markNotificationRead,
  markNotificationsRead,
  NotificationEventItem,
  NotificationStats,
  retryNotification,
} from '@/services/api-client';

const formatTime = (value: string) =>
  new Date(value).toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

const getTitle = (item: NotificationEventItem) => {
  if (item.action_type === 'JOURNAL') return '伴侶新增了日記';
  return '伴侶更新了卡片回覆';
};

const getDescription = (item: NotificationEventItem) => {
  if (item.status === 'QUEUED') return '通知已排入佇列，稍後會自動送達。';
  if (item.status === 'FAILED') return '通知投遞失敗，可稍後重試。';
  if (item.status === 'THROTTLED') return '同類通知在冷卻時間內已被節流。';
  if (item.action_type === 'JOURNAL') return '前往伴侶心聲查看最新內容。';
  return '前往每日共感或牌組查看新回覆。';
};

const getActionLink = (item: NotificationEventItem) =>
  item.action_type === 'JOURNAL' ? '/?tab=partner' : '/?tab=card';

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationEventItem[]>([]);
  const [stats, setStats] = useState<NotificationStats | null>(null);
  const [hoveredDay, setHoveredDay] = useState<NotificationDailyStatsItem | null>(null);
  const [statsWindowDays, setStatsWindowDays] = useState<7 | 30>(7);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [actionFilter, setActionFilter] = useState<'ALL' | 'JOURNAL' | 'CARD'>('ALL');
  const [statusFilter, setStatusFilter] = useState<
    'ALL' | 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED'
  >('ALL');
  const [errorReasonInput, setErrorReasonInput] = useState('');
  const [errorReasonFilter, setErrorReasonFilter] = useState('');

  const unreadCount = useMemo(() => items.filter((item) => !item.is_read).length, [items]);

  const load = useCallback(
    async (opts?: {
      silent?: boolean;
      unreadOnly?: boolean;
      actionType?: 'ALL' | 'JOURNAL' | 'CARD';
      statusType?: 'ALL' | 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED';
      windowDays?: 7 | 30;
      errorReason?: string;
    }) => {
      const silent = Boolean(opts?.silent);
      const unreadOnly = opts?.unreadOnly ?? onlyUnread;
      const targetActionFilter = opts?.actionType ?? actionFilter;
      const targetStatusFilter = opts?.statusType ?? statusFilter;
      const targetWindowDays = opts?.windowDays ?? statsWindowDays;
      const targetErrorReason = opts?.errorReason ?? errorReasonFilter;
      const requestFilters: NotificationFilters = {
        unread_only: unreadOnly,
        action_type: targetActionFilter === 'ALL' ? undefined : targetActionFilter,
        status: targetStatusFilter === 'ALL' ? undefined : targetStatusFilter,
        error_reason: targetErrorReason || undefined,
      };
      if (silent) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      try {
        const [rows, statsData] = await Promise.all([
          fetchNotifications({
            limit: 50,
            ...requestFilters,
          }),
          fetchNotificationStats({
            window_days: targetWindowDays,
            ...requestFilters,
          }),
        ]);
        setItems(rows);
        setStats(statsData);
      } catch (error) {
        console.error('載入通知失敗', error);
      } finally {
        if (silent) {
          setRefreshing(false);
        } else {
          setLoading(false);
        }
      }
    },
    [actionFilter, errorReasonFilter, onlyUnread, statsWindowDays, statusFilter],
  );

  useEffect(() => {
    void load({ unreadOnly: false, actionType: 'ALL', statusType: 'ALL' });
  }, [load]);

  const handleRefresh = async () => {
    await load({ silent: true });
  };

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

  const focusedDay = hoveredDay ?? stats?.window_daily?.[stats.window_daily.length - 1] ?? null;

  const handleMarkAllRead = async () => {
    try {
      await markNotificationsRead(actionFilter === 'ALL' ? undefined : actionFilter.toLowerCase() as 'journal' | 'card');
      await load({
        silent: true,
        unreadOnly: onlyUnread,
        actionType: actionFilter,
        statusType: statusFilter,
      });
    } catch (error) {
      console.error('標記已讀失敗', error);
    }
  };

  const handleToggleUnread = () => {
    setOnlyUnread((prev) => !prev);
  };

  const handleMarkOneRead = async (notificationId: string) => {
    try {
      await markNotificationRead(notificationId);
      setItems((prev) =>
        prev.map((item) =>
          item.id === notificationId
            ? {
                ...item,
                is_read: true,
                read_at: new Date().toISOString(),
              }
            : item,
        ),
      );
    } catch (error) {
      console.error('單筆通知已讀失敗', error);
    }
  };

  const handleActionFilterChange = (nextFilter: 'ALL' | 'JOURNAL' | 'CARD') => {
    setActionFilter(nextFilter);
  };

  const handleStatusFilterChange = (nextFilter: 'ALL' | 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED') => {
    setStatusFilter(nextFilter);
  };

  const handleErrorReasonFilterChange = (value: string) => {
    setErrorReasonInput(value);
  };

  const handleResetFilters = () => {
    setOnlyUnread(false);
    setActionFilter('ALL');
    setStatusFilter('ALL');
    setErrorReasonInput('');
    setErrorReasonFilter('');
  };

  const handleWindowDaysChange = (nextWindow: 7 | 30) => {
    setHoveredDay(null);
    setStatsWindowDays(nextWindow);
  };

  const handleRetryDelivery = async (notificationId: string) => {
    try {
      setRetryingId(notificationId);
      await retryNotification(notificationId);
      await load({
        silent: true,
        unreadOnly: onlyUnread,
        actionType: actionFilter,
        statusType: statusFilter,
      });
    } catch (error) {
      console.error('重送通知失敗', error);
    } finally {
      setRetryingId(null);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setErrorReasonFilter(errorReasonInput.trim());
    }, 350);
    return () => window.clearTimeout(timer);
  }, [errorReasonInput]);

  useEffect(() => {
    if (!loading) {
      void load({
        silent: true,
        unreadOnly: onlyUnread,
        actionType: actionFilter,
        statusType: statusFilter,
        windowDays: statsWindowDays,
        errorReason: errorReasonFilter,
      });
    }
  }, [actionFilter, errorReasonFilter, load, loading, onlyUnread, statsWindowDays, statusFilter]);

  useEffect(() => {
    if (loading) {
      return;
    }
    const timer = setInterval(() => {
      void load({
        silent: true,
        unreadOnly: onlyUnread,
        actionType: actionFilter,
        statusType: statusFilter,
        windowDays: statsWindowDays,
        errorReason: errorReasonFilter,
      });
    }, 20000);
    return () => clearInterval(timer);
  }, [actionFilter, errorReasonFilter, load, loading, onlyUnread, statsWindowDays, statusFilter]);

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />

      <main className="flex-1 md:ml-64 p-4 md:p-8 w-full">
        <div className="max-w-4xl mx-auto space-y-6">
          <header className="bg-white rounded-3xl border border-slate-100 p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                <Bell className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-800">通知中心</h1>
                <p className="text-sm text-slate-500">追蹤通知投遞、狀態與已讀進度</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden">
                {(['ALL', 'JOURNAL', 'CARD'] as const).map((key) => (
                  <button
                    key={key}
                    onClick={() => handleActionFilterChange(key)}
                    className={`px-3 py-1.5 text-xs font-bold tracking-wide ${
                      actionFilter === key
                        ? 'bg-slate-900 text-white'
                        : 'bg-white text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    {key === 'ALL' ? '全部' : key === 'JOURNAL' ? '日記' : '卡片'}
                  </button>
                ))}
              </div>

              <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden">
                {(['ALL', 'QUEUED', 'SENT', 'FAILED', 'THROTTLED'] as const).map((key) => (
                  <button
                    key={key}
                    onClick={() => handleStatusFilterChange(key)}
                    className={`px-3 py-1.5 text-xs font-bold tracking-wide ${
                      statusFilter === key
                        ? 'bg-slate-900 text-white'
                        : 'bg-white text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    {key === 'ALL' ? '全部狀態' : key}
                  </button>
                ))}
              </div>

              <button
                onClick={handleToggleUnread}
                className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
                  onlyUnread
                    ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                    : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                僅看未讀
              </button>
              <input
                value={errorReasonInput}
                onChange={(event) => handleErrorReasonFilterChange(event.target.value)}
                placeholder="錯誤原因關鍵字"
                className="px-3 py-1.5 rounded-lg text-sm border border-slate-200 text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
              <button
                onClick={handleResetFilters}
                className="px-3 py-1.5 rounded-lg text-sm font-semibold border border-slate-200 text-slate-600 hover:bg-slate-50"
              >
                清除篩選
              </button>
              <button
                onClick={handleMarkAllRead}
                className="px-3 py-1.5 rounded-lg text-sm font-semibold border border-slate-200 text-slate-600 hover:bg-slate-50 inline-flex items-center gap-1.5"
              >
                <CheckCheck className="w-4 h-4" />
                全部已讀
              </button>
              <button
                onClick={handleRefresh}
                className="px-3 py-1.5 rounded-lg text-sm font-semibold bg-slate-900 text-white hover:bg-slate-800 inline-flex items-center gap-1.5"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                重新整理
              </button>
            </div>
          </header>

          <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
            <article className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">通知健康分數</p>
              <p className="mt-2 text-2xl font-bold text-slate-800">{healthScore}</p>
              <p className="mt-1 text-xs text-slate-400">SENT 高、FAILED 低，分數越高越穩定</p>
            </article>

            <article className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">投遞成功率</p>
              <p className="mt-2 text-2xl font-bold text-slate-800">{deliveryRate}%</p>
              <p className="mt-1 text-xs text-slate-400">
                SENT {stats?.sent_count ?? 0} / TOTAL {stats?.total_count ?? 0}
              </p>
            </article>

            <article className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">待送與佇列</p>
              <p className="mt-2 text-2xl font-bold text-sky-700">{stats?.queued_count ?? 0}</p>
              <p className="mt-1 text-xs text-slate-400">未讀 {stats?.unread_count ?? 0}</p>
            </article>

            <article className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">失敗與節流</p>
              <p className="mt-2 text-2xl font-bold text-rose-700">
                {(stats?.failed_count ?? 0) + (stats?.throttled_count ?? 0)}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                FAILED {stats?.failed_count ?? 0} / THROTTLED {stats?.throttled_count ?? 0}
              </p>
            </article>

            <article className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-slate-500">近 24 小時</p>
              <p className="mt-2 text-2xl font-bold text-slate-800">{stats?.recent_24h_count ?? 0}</p>
              <p className="mt-1 text-xs text-slate-400">
                失敗 {stats?.recent_24h_failed_count ?? 0}
                {stats?.last_event_at ? ` · 最後事件 ${formatTime(stats.last_event_at)}` : ''}
              </p>
            </article>
          </section>

          <section className="bg-white rounded-3xl border border-slate-100 shadow-sm p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-800">通知趨勢</h2>
                <p className="text-xs text-slate-500">
                  最近 {stats?.window_days ?? statsWindowDays} 天，觀察送達與失敗節奏
                </p>
              </div>
              <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden">
                {([7, 30] as const).map((window) => (
                  <button
                    key={window}
                    onClick={() => handleWindowDaysChange(window)}
                    className={`px-3 py-1.5 text-xs font-bold tracking-wide ${
                      statsWindowDays === window
                        ? 'bg-slate-900 text-white'
                        : 'bg-white text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    {window} 天
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-4 overflow-x-auto">
              <div className="min-w-[420px]">
                <div className="h-28 flex items-end gap-1">
                  {(stats?.window_daily ?? []).map((day) => {
                    const barHeight = Math.max(4, Math.round((day.total_count / trendMax) * 100));
                    const hasData = day.total_count > 0;
                    return (
                      <div key={day.date} className="group flex-1 flex flex-col items-center">
                        <div
                          className="w-full rounded-md bg-slate-100 overflow-hidden flex flex-col-reverse cursor-pointer transition-shadow hover:shadow-sm"
                          style={{ height: `${barHeight}%` }}
                          title={`${day.date}｜總計 ${day.total_count}，SENT ${day.sent_count}，FAILED ${day.failed_count}，THROTTLED ${day.throttled_count}，QUEUED ${day.queued_count}`}
                          onMouseEnter={() => setHoveredDay(day)}
                          onMouseLeave={() => setHoveredDay(null)}
                        >
                          {hasData && (
                            <>
                              {day.queued_count > 0 && (
                                <div
                                  className="bg-sky-300"
                                  style={{ height: `${(day.queued_count / day.total_count) * 100}%` }}
                                />
                              )}
                              {day.throttled_count > 0 && (
                                <div
                                  className="bg-amber-300"
                                  style={{ height: `${(day.throttled_count / day.total_count) * 100}%` }}
                                />
                              )}
                              {day.failed_count > 0 && (
                                <div
                                  className="bg-rose-300"
                                  style={{ height: `${(day.failed_count / day.total_count) * 100}%` }}
                                />
                              )}
                              {day.sent_count > 0 && (
                                <div
                                  className="bg-emerald-300"
                                  style={{ height: `${(day.sent_count / day.total_count) * 100}%` }}
                                />
                              )}
                            </>
                          )}
                        </div>
                        <span className="mt-1 text-[10px] text-slate-400">
                          {day.date.slice(5)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-slate-500">
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-300" />SENT</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded bg-rose-300" />FAILED</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded bg-amber-300" />THROTTLED</span>
              <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded bg-sky-300" />QUEUED</span>
            </div>

            <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-3">
              <article className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs font-semibold text-slate-600">
                  {hoveredDay ? `${focusedDay?.date} 詳細` : '最近一天（預設）詳細'}
                </p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600">
                  <p>總計：{focusedDay?.total_count ?? 0}</p>
                  <p>SENT：{focusedDay?.sent_count ?? 0}</p>
                  <p>FAILED：{focusedDay?.failed_count ?? 0}</p>
                  <p>THROTTLED：{focusedDay?.throttled_count ?? 0}</p>
                  <p>QUEUED：{focusedDay?.queued_count ?? 0}</p>
                </div>
              </article>

              <article className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs font-semibold text-slate-600">失敗原因 Top N（視窗內）</p>
                {stats?.window_top_failure_reasons?.length ? (
                  <ul className="mt-2 space-y-1">
                    {stats.window_top_failure_reasons.map((item) => (
                      <li key={item.reason}>
                        <button
                          onClick={() => {
                            setStatusFilter('FAILED');
                            setErrorReasonInput(item.reason);
                            setErrorReasonFilter(item.reason);
                          }}
                          className="w-full text-left flex items-center justify-between text-xs text-slate-600 hover:text-slate-900"
                        >
                          <span className="truncate pr-2">{item.reason}</span>
                          <span className="font-semibold text-slate-800">{item.count}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs text-slate-400">目前視窗內沒有 FAILED 事件</p>
                )}
              </article>
            </div>
          </section>

          <section className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between text-sm text-slate-500">
              <span>共 {items.length} 筆通知</span>
              <span>未讀 {unreadCount} 筆</span>
            </div>

            {loading ? (
              <div className="p-10 text-center text-slate-400">載入通知中...</div>
            ) : items.length === 0 ? (
              <div className="p-12 text-center text-slate-400 space-y-2">
                <p className="font-medium">目前沒有通知</p>
                <p className="text-sm">有新活動時會顯示在這裡</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {items.map((item) => {
                  const itemIcon = item.action_type === 'JOURNAL' ? BookOpen : MessageCircleMore;
                  const ItemIcon = itemIcon;
                  return (
                    <li key={item.id} className={`px-6 py-4 ${item.is_read ? 'bg-white' : 'bg-indigo-50/40'}`}>
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center mt-0.5">
                          <ItemIcon className="w-4 h-4" />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="text-sm font-semibold text-slate-800">{getTitle(item)}</h3>
                            {!item.is_read && <span className="w-2 h-2 rounded-full bg-indigo-500" />}
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                                item.status === 'SENT'
                                  ? 'bg-emerald-100 text-emerald-700'
                                  : item.status === 'QUEUED'
                                    ? 'bg-sky-100 text-sky-700'
                                  : item.status === 'FAILED'
                                    ? 'bg-rose-100 text-rose-700'
                                    : 'bg-amber-100 text-amber-700'
                              }`}
                            >
                              {item.status}
                            </span>
                          </div>
                          <p className="text-sm text-slate-500 mt-1">{getDescription(item)}</p>

                          <div className="mt-3 flex items-center justify-between gap-3">
                            <div className="inline-flex items-center gap-1 text-xs text-slate-400">
                              <Clock3 className="w-3.5 h-3.5" />
                              {formatTime(item.created_at)}
                            </div>

                            <div className="flex items-center gap-2">
                              {!item.is_read && (
                                <button
                                  onClick={() => void handleMarkOneRead(item.id)}
                                  className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-800"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                  已讀
                                </button>
                              )}
                              {(item.status === 'FAILED' || item.status === 'THROTTLED') && (
                                <button
                                  onClick={() => void handleRetryDelivery(item.id)}
                                  disabled={retryingId === item.id}
                                  className={`inline-flex items-center gap-1 text-xs font-semibold ${
                                    retryingId === item.id
                                      ? 'text-slate-400 cursor-not-allowed'
                                      : 'text-indigo-600 hover:text-indigo-700'
                                  }`}
                                >
                                  <RefreshCw className={`w-3.5 h-3.5 ${retryingId === item.id ? 'animate-spin' : ''}`} />
                                  重送通知
                                </button>
                              )}
                              <Link
                                href={getActionLink(item)}
                                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                              >
                                前往查看
                              </Link>
                            </div>
                          </div>

                          {item.status === 'FAILED' && item.error_message && (
                            <div className="mt-2 inline-flex items-center gap-1.5 text-xs text-rose-600 bg-rose-50 px-2 py-1 rounded-md border border-rose-100">
                              <MailWarning className="w-3.5 h-3.5" />
                              {item.error_message}
                            </div>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
