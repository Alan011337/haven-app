'use client';

import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  Bell,
  BookOpen,
  Check,
  CheckCheck,
  Clock,
  Clock3,
  HandHeart,
  MailWarning,
  MessageCircleMore,
  Pause,
  RefreshCw,
  TrendingUp,
  Zap,
} from 'lucide-react';

import { GlassCard } from '@/components/haven/GlassCard';
import {
  useNotificationsData,
  formatTime,
  getTitle,
  getDescription,
  getActionLink,
} from '@/features/notifications/useNotificationsData';

export default function NotificationsPageContent() {
  const {
    items,
    stats,
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
  } = useNotificationsData();

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-page-enter">
      <GlassCard role="banner" className="p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-primary/15 to-primary/5 border border-primary/10 flex items-center justify-center text-primary" aria-hidden>
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-title font-art font-bold text-card-foreground tracking-tight">通知中心</h1>
            <p className="text-caption text-muted-foreground">追蹤通知投遞、狀態與已讀進度</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center rounded-button border border-border overflow-hidden">
            {(['ALL', 'JOURNAL', 'CARD'] as const).map((key) => (
              <button
                key={key}
                onClick={() => handleActionFilterChange(key)}
                className={`px-3 py-1.5 text-xs font-bold tracking-wide focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                  actionFilter === key
                    ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground shadow-satin-button'
                    : 'bg-card text-muted-foreground hover:bg-muted border-border'
                }`}
              >
                {key === 'ALL' ? '全部' : key === 'JOURNAL' ? '日記' : '卡片'}
              </button>
            ))}
          </div>

          <div className="flex items-center rounded-button border border-border overflow-hidden">
            {(['ALL', 'QUEUED', 'SENT', 'FAILED', 'THROTTLED'] as const).map((key) => (
              <button
                key={key}
                onClick={() => handleStatusFilterChange(key)}
                className={`px-3 py-1.5 text-xs font-bold tracking-wide focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                  statusFilter === key
                    ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground shadow-satin-button'
                    : 'bg-card text-muted-foreground hover:bg-muted border-border'
                }`}
              >
                {key === 'ALL' ? '全部狀態' : key}
              </button>
            ))}
          </div>

          <button
            onClick={handleToggleUnread}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors duration-haven-fast ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              onlyUnread
                ? 'bg-primary/10 text-primary border border-primary/30'
                : 'bg-card text-muted-foreground border border-border hover:bg-muted'
            }`}
          >
            僅看未讀
          </button>
          <input
            value={errorReasonInput}
            onChange={(e) => handleErrorReasonFilterChange(e.target.value)}
            placeholder="錯誤原因關鍵字"
            aria-label="錯誤原因關鍵字篩選"
            className="px-3 py-1.5 rounded-lg text-caption border border-border bg-background text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button
            onClick={handleResetFilters}
            className="px-3 py-1.5 rounded-lg text-caption font-semibold border border-border text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            清除篩選
          </button>
          <button
            onClick={handleMarkAllRead}
            className="px-3 py-1.5 rounded-lg text-caption font-semibold border border-border text-muted-foreground hover:bg-muted inline-flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <CheckCheck className="w-4 h-4" />
            全部已讀
          </button>
          <button
            onClick={handleRefresh}
            className="px-3.5 py-1.5 rounded-button text-caption font-semibold bg-gradient-to-b from-primary to-primary/90 border-t border-t-white/30 text-primary-foreground shadow-satin-button hover:shadow-lift transition-all duration-haven ease-haven inline-flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.98]"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            重新整理
          </button>
        </div>
      </GlassCard>

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3 animate-page-enter-delay-1">
        <GlassCard role="article" className="p-5 animate-stagger-up">
          <span className="icon-badge mb-2"><Activity className="w-4 h-4" /></span>
          <p className="text-caption font-semibold tracking-wider uppercase text-muted-foreground/70">健康分數</p>
          <p className="mt-2 text-title font-bold text-card-foreground tabular-nums">{healthScore}</p>
          <p className="mt-1 text-caption text-muted-foreground/80">分數越高越穩定</p>
        </GlassCard>

        <GlassCard role="article" className="p-5 animate-stagger-up-1">
          <span className="icon-badge mb-2"><TrendingUp className="w-4 h-4" /></span>
          <p className="text-caption font-semibold tracking-wider uppercase text-muted-foreground/70">投遞成功率</p>
          <p className="mt-2 text-title font-bold text-card-foreground tabular-nums">{deliveryRate}%</p>
          <p className="mt-1 text-caption text-muted-foreground/80 tabular-nums">
            SENT {stats?.sent_count ?? 0} / TOTAL {stats?.total_count ?? 0}
          </p>
        </GlassCard>

        <GlassCard role="article" className="p-5 animate-stagger-up-2">
          <span className="icon-badge mb-2"><Clock className="w-4 h-4" /></span>
          <p className="text-caption font-semibold tracking-wider uppercase text-muted-foreground/70">待送佇列</p>
          <p className="mt-2 text-title font-bold text-primary tabular-nums">{stats?.queued_count ?? 0}</p>
          <p className="mt-1 text-caption text-muted-foreground/80 tabular-nums">未讀 {stats?.unread_count ?? 0}</p>
        </GlassCard>

        <GlassCard role="article" className="p-5 animate-stagger-up-3">
          <span className="icon-badge mb-2"><AlertTriangle className="w-4 h-4" /></span>
          <p className="text-caption font-semibold tracking-wider uppercase text-muted-foreground/70">失敗與節流</p>
          <p className="mt-2 text-title font-bold text-destructive tabular-nums">
            {(stats?.failed_count ?? 0) + (stats?.throttled_count ?? 0)}
          </p>
          <p className="mt-1 text-caption text-muted-foreground/80 tabular-nums">
            FAILED {stats?.failed_count ?? 0} / THROTTLED {stats?.throttled_count ?? 0}
          </p>
        </GlassCard>

        <GlassCard role="article" className="p-5 animate-stagger-up-4">
          <span className="icon-badge mb-2"><Zap className="w-4 h-4" /></span>
          <p className="text-caption font-semibold tracking-wider uppercase text-muted-foreground/70">近 24 小時</p>
          <p className="mt-2 text-title font-bold text-card-foreground tabular-nums">{stats?.recent_24h_count ?? 0}</p>
          <p className="mt-1 text-caption text-muted-foreground/80 tabular-nums">
            失敗 {stats?.recent_24h_failed_count ?? 0}
            {stats?.last_event_at ? ` · 最後事件 ${formatTime(stats.last_event_at)}` : ''}
          </p>
        </GlassCard>
      </section>

      <GlassCard role="region" aria-label="通知趨勢" className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-body font-art font-bold text-card-foreground tracking-tight">通知趨勢</h2>
            <p className="text-caption text-muted-foreground">
              最近 {stats?.window_days ?? statsWindowDays} 天，觀察送達與失敗節奏
            </p>
          </div>
          <div className="flex items-center rounded-button border border-border overflow-hidden">
            {([7, 30] as const).map((window) => (
              <button
                key={window}
                onClick={() => handleWindowDaysChange(window)}
                className={`px-3 py-1.5 text-caption font-bold tracking-wide focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                  statsWindowDays === window
                    ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground shadow-satin-button'
                    : 'bg-background text-muted-foreground hover:bg-muted'
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
                      className="w-full rounded-lg bg-muted/60 overflow-hidden flex flex-col-reverse cursor-pointer transition-shadow duration-haven ease-haven hover:shadow-lift"
                      style={{ height: `${barHeight}%` }}
                      title={`${day.date}｜總計 ${day.total_count}，SENT ${day.sent_count}，FAILED ${day.failed_count}，THROTTLED ${day.throttled_count}，QUEUED ${day.queued_count}`}
                      onMouseEnter={() => setHoveredDay(day)}
                      onMouseLeave={() => setHoveredDay(null)}
                    >
                      {hasData && (
                        <>
                          {day.queued_count > 0 && (
                            <div
                              className="bg-chart-3"
                              style={{ height: `${(day.queued_count / day.total_count) * 100}%` }}
                              aria-hidden
                            />
                          )}
                          {day.throttled_count > 0 && (
                            <div
                              className="bg-chart-4"
                              style={{ height: `${(day.throttled_count / day.total_count) * 100}%` }}
                              aria-hidden
                            />
                          )}
                          {day.failed_count > 0 && (
                            <div
                              className="bg-destructive"
                              style={{ height: `${(day.failed_count / day.total_count) * 100}%` }}
                              aria-hidden
                            />
                          )}
                          {day.sent_count > 0 && (
                            <div
                              className="bg-chart-2"
                              style={{ height: `${(day.sent_count / day.total_count) * 100}%` }}
                              aria-hidden
                            />
                          )}
                        </>
                      )}
                    </div>
                    <span className="mt-1 text-caption text-muted-foreground tabular-nums">{day.date.slice(5)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-4 text-caption text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-chart-2" aria-hidden />SENT
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-destructive" aria-hidden />FAILED
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-chart-4" aria-hidden />THROTTLED
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-chart-3" aria-hidden />QUEUED
          </span>
        </div>

        <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-3">
          <article className="stat-box">
            <p className="text-caption font-art font-semibold text-card-foreground tracking-tight">
              {focusedDay ? `${focusedDay?.date} 詳細` : '最近一天（預設）詳細'}
            </p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-caption text-muted-foreground tabular-nums">
              <p>總計：{focusedDay?.total_count ?? 0}</p>
              <p>SENT：{focusedDay?.sent_count ?? 0}</p>
              <p>FAILED：{focusedDay?.failed_count ?? 0}</p>
              <p>THROTTLED：{focusedDay?.throttled_count ?? 0}</p>
              <p>QUEUED：{focusedDay?.queued_count ?? 0}</p>
            </div>
          </article>

          <article className="stat-box">
            <p className="text-caption font-art font-semibold text-card-foreground tracking-tight">失敗原因 Top N（視窗內）</p>
            {stats?.window_top_failure_reasons?.length ? (
              <ul className="mt-2 space-y-1">
                {stats.window_top_failure_reasons.map((item) => (
                  <li key={item.reason}>
                    <button
                      onClick={() => setStatusAndErrorReason('FAILED', item.reason)}
                      className="w-full text-left flex items-center justify-between text-caption text-muted-foreground hover:text-card-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                    >
                      <span className="truncate pr-2">{item.reason}</span>
                      <span className="font-semibold text-card-foreground tabular-nums">{item.count}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-caption text-muted-foreground">目前視窗內沒有 FAILED 事件</p>
            )}
          </article>
        </div>
      </GlassCard>

      <GlassCard role="region" aria-label="通知列表" className="overflow-hidden animate-page-enter-delay-2">
        <div className="px-6 py-4 border-b border-border/60 flex items-center justify-between text-caption text-muted-foreground/80 font-medium">
          <span className="tabular-nums">共 {items.length} 筆通知</span>
          <span className="tabular-nums">未讀 {unreadCount} 筆</span>
        </div>

        {loading ? (
          <div className="p-10 text-center text-body text-muted-foreground animate-breathe" role="status">載入通知中...</div>
        ) : items.length === 0 ? (
          <div className="p-14 text-center text-muted-foreground space-y-2" role="status">
            <span className="icon-badge !w-14 !h-14 !rounded-2xl mx-auto mb-4" aria-hidden>
              <Bell className="w-6 h-6" />
            </span>
            <p className="text-body font-art font-semibold text-foreground">目前沒有通知</p>
            <p className="text-caption">有新活動時會顯示在這裡</p>
          </div>
        ) : (
          <ul className="divide-y divide-border/50">
            {items.map((item, idx) => {
              const ItemIcon =
                item.action_type === 'JOURNAL'
                  ? BookOpen
                  : item.action_type === 'MEDIATION_INVITE'
                    ? HandHeart
                    : item.action_type === 'COOLDOWN_STARTED'
                      ? Pause
                      : MessageCircleMore;
              const stagger = idx < 6 ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}` : '';
              return (
                <li
                  key={item.id}
                  className={`px-6 py-4 transition-colors duration-haven-fast ease-haven ${stagger} ${item.is_read ? 'bg-card hover:bg-muted/20 border-l-2 border-l-transparent' : 'bg-primary/[0.03] hover:bg-primary/[0.06] border-l-2 border-l-primary/25 hover:border-l-primary/40'}`}
                >
                  <div className="flex items-start gap-3">
                    <span className={`icon-badge mt-0.5 ${item.is_read ? '!bg-muted/60 !text-muted-foreground !border-border' : ''}`} aria-hidden>
                      <ItemIcon className="w-4 h-4" />
                    </span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-body font-semibold text-card-foreground">{getTitle(item)}</h3>
                        {!item.is_read && (
                          <span className="w-2 h-2 rounded-full bg-primary" aria-hidden />
                        )}
                        <span
                          className={`text-caption px-2 py-0.5 rounded-full font-semibold ${
                            item.status === 'SENT'
                              ? 'bg-accent/20 text-accent'
                              : item.status === 'QUEUED'
                                ? 'bg-primary/20 text-primary'
                                : item.status === 'FAILED'
                                  ? 'bg-destructive/20 text-destructive'
                                  : 'bg-primary/20 text-primary'
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                      <p className="text-body text-muted-foreground mt-1">{getDescription(item)}</p>

                      <div className="mt-3 flex items-center justify-between gap-3">
                        <div className="inline-flex items-center gap-1 text-caption text-muted-foreground tabular-nums">
                          <Clock3 className="w-3.5 h-3.5" />
                          {formatTime(item.created_at)}
                        </div>

                        <div className="flex items-center gap-2">
                          {!item.is_read && (
                            <button
                              onClick={() => void handleMarkOneRead(item.id)}
                              className="inline-flex items-center gap-1 text-caption font-semibold text-muted-foreground hover:text-card-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                            >
                              <Check className="w-3.5 h-3.5" />
                              已讀
                            </button>
                          )}
                          {(item.status === 'FAILED' || item.status === 'THROTTLED') && (
                            <button
                              onClick={() => void handleRetryDelivery(item.id)}
                              disabled={retryingId === item.id}
                              className={`inline-flex items-center gap-1 text-caption font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                                retryingId === item.id
                                  ? 'text-muted-foreground cursor-not-allowed'
                                  : 'text-primary hover:opacity-90'
                              }`}
                            >
                              <RefreshCw
                                className={`w-3.5 h-3.5 ${retryingId === item.id ? 'animate-spin' : ''}`}
                              />
                              重送通知
                            </button>
                          )}
                          <Link
                            href={getActionLink(item)}
                            className="text-caption font-semibold text-primary hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
                          >
                            前往查看
                          </Link>
                        </div>
                      </div>

                      {item.status === 'FAILED' && item.error_message && (
                        <div className="mt-2 inline-flex items-center gap-1.5 text-caption text-destructive bg-destructive/10 px-2 py-1 rounded-md border border-destructive/20" role="alert">
                          <MailWarning className="w-3.5 h-3.5" aria-hidden />
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
      </GlassCard>
    </div>
  );
}
