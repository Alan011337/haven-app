'use client';

import { AlertTriangle, Check, CheckCheck, Compass, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import {
  NotificationFeaturedCard,
  NotificationLinkAction,
  NotificationPulseRow,
  NotificationRetryAction,
  NotificationsCover,
  NotificationsDiagnosticsRail,
  NotificationsFocusBar,
  NotificationsOverviewCard,
  NotificationsSection,
  NotificationsStatePanel,
  NotificationsTrendCard,
} from '@/app/notifications/NotificationsPrimitives';
import { NotificationsSkeleton } from '@/app/notifications/NotificationsSkeleton';
import {
  useNotificationsData,
  formatTime,
  getActionLink,
  getDescription,
  getTitle,
} from '@/features/notifications/useNotificationsData';
import type { NotificationEventItem } from '@/services/api-client';

const ACTION_OPTIONS = [
  { key: 'ALL', label: '全部訊號' },
  { key: 'MEDIATION_INVITE', label: '調解邀請' },
  { key: 'COOLDOWN_STARTED', label: '冷卻提醒' },
  { key: 'JOURNAL', label: '日記更新' },
  { key: 'CARD', label: '卡片回覆' },
] as const;

const STATUS_OPTIONS = [
  { key: 'ALL', label: '全部狀態' },
  { key: 'QUEUED', label: '排程中' },
  { key: 'SENT', label: '已送達' },
  { key: 'FAILED', label: '需要補送' },
  { key: 'THROTTLED', label: '節奏放緩' },
] as const;

type NotificationLane = 'attention' | 'unread' | 'archive';

function getNotificationPriority(item: NotificationEventItem, lane: NotificationLane) {
  let score = 0;

  if (lane === 'attention') {
    score += item.status === 'FAILED' ? 420 : 320;
  } else if (lane === 'unread') {
    score += 210;
  } else {
    score += 100;
  }

  if (!item.is_read) {
    score += 48;
  }

  if (item.action_type === 'MEDIATION_INVITE') {
    score += 92;
  } else if (item.action_type === 'COOLDOWN_STARTED') {
    score += 76;
  } else if (item.action_type === 'JOURNAL') {
    score += 58;
  } else {
    score += 42;
  }

  if (item.status === 'QUEUED') {
    score += 16;
  }

  if (item.error_message?.trim()) {
    score += 24;
  }

  const createdAtMs = new Date(item.created_at).getTime();
  const ageHours = Number.isFinite(createdAtMs)
    ? Math.max(0, (Date.now() - createdAtMs) / (1000 * 60 * 60))
    : 999;

  if (ageHours <= 3) {
    score += 48;
  } else if (ageHours <= 24) {
    score += 34;
  } else if (ageHours <= 72) {
    score += 18;
  } else if (ageHours <= 168) {
    score += 8;
  }

  return score;
}

function sortNotificationsByPriority(
  items: NotificationEventItem[],
  lane: NotificationLane,
) {
  return [...items].sort((left, right) => {
    const priorityDelta =
      getNotificationPriority(right, lane) - getNotificationPriority(left, lane);
    if (priorityDelta !== 0) {
      return priorityDelta;
    }
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });
}

function getActionLabel(actionType: NotificationEventItem['action_type']) {
  if (actionType === 'JOURNAL') return '日記更新';
  if (actionType === 'MEDIATION_INVITE') return '調解邀請';
  if (actionType === 'COOLDOWN_STARTED') return '冷卻提醒';
  return '卡片回覆';
}

function getActionFilterLabel(actionFilter: (typeof ACTION_OPTIONS)[number]['key']) {
  if (actionFilter === 'ALL') return '全部訊號';
  if (actionFilter === 'MEDIATION_INVITE') return '調解邀請';
  if (actionFilter === 'COOLDOWN_STARTED') return '冷卻提醒';
  if (actionFilter === 'JOURNAL') return '日記更新';
  return '卡片回覆';
}

function getSectionSupport(item: NotificationEventItem) {
  if (item.status === 'FAILED') return '這則提醒沒有順利送達，值得你先替它補上最後一步。';
  if (item.status === 'THROTTLED') return '系統替你們放慢節奏，等下一個合適時刻再把它送出去。';
  if (!item.is_read) return '它還保持著剛抵達的狀態，適合現在就溫柔接住。';
  if (item.action_type === 'JOURNAL') return '這份更新已經安穩落下，留在這裡等你回望。';
  if (item.action_type === 'MEDIATION_INVITE') return '它比較像一扇還敞開著的門，等你們準備好一起走進去。';
  return '先收到、先放好，等你方便時再慢慢回到它。';
}

function getFeaturedEyebrow(item: NotificationEventItem) {
  if (item.status === 'FAILED' || item.status === 'THROTTLED') return 'Needs Care';
  if (!item.is_read) return 'Unread Now';
  return 'Quiet Archive';
}

function buildBadges(item: NotificationEventItem) {
  const badges = [getActionLabel(item.action_type)];
  if (item.status === 'FAILED') badges.push('需要補送');
  if (item.status === 'THROTTLED') badges.push('節奏已放緩');
  if (!item.is_read) badges.push('尚未閱讀');
  return badges;
}

export default function NotificationsPageContent() {
  const {
    items,
    stats,
    listError,
    statsError,
    hasDiagnosticsData,
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

  const attentionItems = sortNotificationsByPriority(
    items.filter((item) => item.status === 'FAILED' || item.status === 'THROTTLED'),
    'attention',
  );
  const attentionIds = new Set(attentionItems.map((item) => item.id));
  const unreadPulseItems = sortNotificationsByPriority(
    items.filter((item) => !item.is_read && !attentionIds.has(item.id)),
    'unread',
  );
  const archiveItems = sortNotificationsByPriority(
    items.filter((item) => !attentionIds.has(item.id) && item.is_read),
    'archive',
  );
  const featuredItem = attentionItems[0] ?? unreadPulseItems[0] ?? archiveItems[0] ?? null;
  const featuredId = featuredItem?.id ?? null;
  const featuredInAttention = featuredId ? attentionItems.some((item) => item.id === featuredId) : false;
  const featuredInUnread = featuredId ? unreadPulseItems.some((item) => item.id === featuredId) : false;
  const featuredInArchive = featuredId ? archiveItems.some((item) => item.id === featuredId) : false;
  const attentionRows = attentionItems.filter((item) => item.id !== featuredId);
  const unreadRows = unreadPulseItems.filter((item) => item.id !== featuredId);
  const archiveRows = archiveItems.filter((item) => item.id !== featuredId);
  const hasActiveAttention = attentionItems.length > 0;
  const hasUnreadPulse = unreadPulseItems.length > 0;
  const hasFiltersApplied =
    onlyUnread || actionFilter !== 'ALL' || statusFilter !== 'ALL' || errorReasonInput.trim().length > 0;
  const supportsBulkReadForAction =
    actionFilter === 'ALL' || actionFilter === 'JOURNAL' || actionFilter === 'CARD';
  const canBulkMarkAllRead =
    unreadCount > 0 &&
    supportsBulkReadForAction &&
    statusFilter === 'ALL' &&
    errorReasonInput.trim().length === 0;
  const lastEventLabel = stats?.last_event_at ? formatTime(stats.last_event_at) : '今天還很安靜';
  const topFailureReasons = stats?.window_top_failure_reasons ?? [];
  const showInitialSkeleton = loading && items.length === 0 && !hasDiagnosticsData;
  const bulkReadSupportMessage =
    unreadCount > 0 && !canBulkMarkAllRead
      ? actionFilter === 'MEDIATION_INVITE' || actionFilter === 'COOLDOWN_STARTED'
        ? `你現在聚焦在「${getActionFilterLabel(actionFilter)}」。為了避免一次把超出眼前範圍的提醒也標成已讀，批次整理先交給單則處理。`
        : statusFilter !== 'ALL' || errorReasonInput.trim().length > 0
          ? '你現在正在看更窄的狀態或錯誤原因。批次標記已讀會超出這組焦點，所以 Haven 先保守停用它。'
          : null
      : null;

  const pulse = listError && statsError
    ? '這一刻的脈動還沒有完整回來。你仍然在對的位置，重新整理後我們會把真正重要的訊號帶回來。'
    : hasActiveAttention
      ? `目前有 ${attentionItems.length} 則提醒需要你優先接手，讓 Haven 幫你把最需要照看的訊號放到最前面。`
      : hasUnreadPulse
        ? `現在有 ${unreadPulseItems.length} 則新的關係訊號剛剛抵達。它們不是催促，而是溫柔提醒你們此刻正在發生什麼。`
        : archiveItems.length > 0
          ? '現在一切相對平穩。這裡保留的是最近被接住的提醒，讓你回來時能重新找到對的節奏。'
          : '現在是一段平靜的留白。當新的日記、卡片回覆或提醒出現時，這裡會用更溫柔的方式接住它。';

  if (showInitialSkeleton) {
    return <NotificationsSkeleton />;
  }

  const renderNotificationActions = (item: NotificationEventItem) => (
    <>
      {!item.is_read ? (
        <Button
          size="sm"
          variant="outline"
          leftIcon={<Check className="h-4 w-4" aria-hidden />}
          onClick={() => void handleMarkOneRead(item.id)}
          aria-label="標記這則通知為已讀"
        >
          標記已讀
        </Button>
      ) : null}
      {item.status === 'FAILED' || item.status === 'THROTTLED' ? (
        <NotificationRetryAction
          loading={retryingId === item.id}
          onClick={() => void handleRetryDelivery(item.id)}
        />
      ) : null}
      <NotificationLinkAction href={getActionLink(item)} />
    </>
  );

  return (
    <div className="space-y-[clamp(1.5rem,3vw,2.75rem)] animate-page-enter">
      <NotificationsCover
        eyebrow="Notifications"
        title="每一則提醒，都應該讓你更靠近真正重要的事。"
        description="這裡不是系統告警箱，而是 Haven 幫你整理好的關係脈動。需要補送的、剛剛抵達的、已經安穩落下的，都有各自合適的位置。"
        pulse={pulse}
        highlights={
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant={hasActiveAttention ? 'warning' : 'metadata'} size="md" className={hasActiveAttention ? '' : 'border-white/54 bg-white/72'}>
              需要照看 {attentionItems.length}
            </Badge>
            <Badge variant={unreadCount > 0 ? 'default' : 'metadata'} size="md" className={unreadCount > 0 ? '' : 'border-white/54 bg-white/72'}>
              尚未閱讀 {unreadCount}
            </Badge>
            <Badge variant="metadata" size="md" className="border-white/54 bg-white/72">
              最後事件 {lastEventLabel}
            </Badge>
            {hasFiltersApplied ? (
              <Badge variant="outline" size="md" className="border-white/54 bg-white/66">
                已套用焦點篩選
              </Badge>
            ) : null}
          </div>
        }
        actions={
          <>
            {canBulkMarkAllRead ? (
              <Button
                size="lg"
                leftIcon={<CheckCheck className="h-4 w-4" aria-hidden />}
                onClick={() => void handleMarkAllRead()}
                aria-label={
                  actionFilter === 'ALL'
                    ? '將目前可批次整理的通知全部標記為已讀'
                    : `將${getActionFilterLabel(actionFilter)}通知全部標記為已讀`
                }
              >
                全部標記為已讀
              </Button>
            ) : (
              <Button
                size="lg"
                loading={refreshing}
                leftIcon={!refreshing ? <RefreshCw className="h-4 w-4" aria-hidden /> : undefined}
                onClick={() => void handleRefresh()}
                aria-label="重新整理通知中心"
                >
                  重新整理
                </Button>
            )}
            {canBulkMarkAllRead ? (
              <Button
                size="lg"
                variant="outline"
                loading={refreshing}
                leftIcon={!refreshing ? <RefreshCw className="h-4 w-4" aria-hidden /> : undefined}
                onClick={() => void handleRefresh()}
                aria-label="重新整理通知中心"
              >
                同步最新脈動
              </Button>
            ) : hasFiltersApplied ? (
              <Button
                size="lg"
                variant="outline"
                onClick={handleResetFilters}
                aria-label="清除目前焦點篩選"
              >
                放寬焦點
              </Button>
            ) : null}
          </>
        }
        featured={
          featuredItem ? (
            <NotificationFeaturedCard
              actionType={featuredItem.action_type}
              status={featuredItem.status}
              eyebrow={getFeaturedEyebrow(featuredItem)}
              title={getTitle(featuredItem)}
              description={getDescription(featuredItem)}
              timeLabel={formatTime(featuredItem.created_at)}
              badges={buildBadges(featuredItem)}
              unread={!featuredItem.is_read}
              support={getSectionSupport(featuredItem)}
              errorMessage={featuredItem.status === 'FAILED' ? featuredItem.error_message : null}
              actions={renderNotificationActions(featuredItem)}
            />
          ) : (
            <NotificationsStatePanel
              tone="quiet"
              eyebrow="Quiet Pulse"
              title="現在沒有需要你即刻處理的提醒"
              description="通知區會在新的日記、卡片回覆或系統需要你接手的時刻重新亮起。現在這裡保持平靜，也是一種好消息。"
            />
          )
        }
        aside={
          <>
            <NotificationsOverviewCard
              eyebrow="Pulse Snapshot"
              title="先看見現在的狀態"
              description="Haven 先替你整理出最需要注意的方向，讓你不用從一長串提醒裡自己找重點。"
            >
              <div className="grid gap-3 sm:grid-cols-3 2xl:grid-cols-1">
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">需要照看</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{attentionItems.length}</p>
                  <p className="mt-1 type-caption text-muted-foreground">FAILED 與 THROTTLED 會先被帶到最前面。</p>
                </div>
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">未讀訊號</p>
                  <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{unreadCount}</p>
                  <p className="mt-1 type-caption text-muted-foreground">還沒接住的提醒，保持在剛抵達的溫度。</p>
                </div>
                <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">最後事件</p>
                  <p className="mt-2 text-lg font-semibold text-card-foreground tabular-nums">{lastEventLabel}</p>
                  <p className="mt-1 type-caption text-muted-foreground">讓你知道這片脈動最後一次被點亮是在什麼時候。</p>
                </div>
              </div>
            </NotificationsOverviewCard>

            {statsError && !hasDiagnosticsData ? (
              <NotificationsStatePanel
                tone="error"
                eyebrow="Delivery Diagnostics"
                title="診斷摘要暫時沒有回來"
                description="主要通知列表仍可使用。重新整理後，我們會把送達率與近期健康分數帶回來。"
                actions={
                  <Button
                    variant="outline"
                    leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                    onClick={() => void handleRefresh()}
                  >
                    重新整理摘要
                  </Button>
                }
              />
            ) : (
              <NotificationsOverviewCard
                eyebrow="Delivery Tone"
                title="安穩度與送達節奏"
                description="診斷資料仍在，只是退到後方，安靜地支持你理解這些提醒目前有多穩定。"
              >
                <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-1">
                  <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                    <div className="flex items-center gap-2 text-card-foreground">
                      <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
                      <p className="type-caption uppercase tracking-[0.18em] text-primary/76">健康分數</p>
                    </div>
                    <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{healthScore}</p>
                    <p className="mt-1 type-caption text-muted-foreground">越高表示越多提醒已穩定抵達。</p>
                  </div>
                  <div className="rounded-[1.65rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                    <div className="flex items-center gap-2 text-card-foreground">
                      <Compass className="h-4 w-4 text-primary" aria-hidden />
                      <p className="type-caption uppercase tracking-[0.18em] text-primary/76">送達率</p>
                    </div>
                    <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{deliveryRate}%</p>
                    <p className="mt-1 type-caption text-muted-foreground">
                      已送達 {stats?.sent_count ?? 0} / 全部 {stats?.total_count ?? 0}
                    </p>
                  </div>
                </div>
              </NotificationsOverviewCard>
            )}
          </>
        }
      />

      <NotificationsFocusBar
        eyebrow="Focus Bar"
        title="選一種現在想處理的節奏"
        description="篩選不需要堆滿頁面頂端。把它們留在這裡，讓你能更 calm 地收窄視野，再回到真正重要的提醒。"
      >
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              size="sm"
              variant={onlyUnread ? 'primary' : 'outline'}
              onClick={handleToggleUnread}
              aria-pressed={onlyUnread}
              aria-label="切換僅看未讀"
            >
              僅看未讀
            </Button>
            <Badge variant="metadata" size="md" className="border-white/54 bg-white/72">
              目前可見 {items.length} 則
            </Badge>
            <Badge variant="metadata" size="md" className="border-white/54 bg-white/72">
              未讀 {unreadCount}
            </Badge>
            {hasFiltersApplied ? (
              <Button size="sm" variant="ghost" onClick={handleResetFilters} aria-label="清除所有通知篩選">
                清除篩選
              </Button>
            ) : null}
          </div>

          {bulkReadSupportMessage ? (
            <div className="rounded-[1.4rem] border border-white/56 bg-white/68 px-4 py-3 text-sm text-muted-foreground shadow-soft">
              {bulkReadSupportMessage}
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_320px]">
            <div className="space-y-2">
              <p className="type-caption uppercase tracking-[0.18em] text-primary/76">訊號類型</p>
              <div className="flex flex-wrap gap-2">
                {ACTION_OPTIONS.map((option) => (
                  <Button
                    key={option.key}
                    size="sm"
                    variant={actionFilter === option.key ? 'primary' : 'outline'}
                    onClick={() => handleActionFilterChange(option.key)}
                    aria-pressed={actionFilter === option.key}
                    aria-label={`篩選 ${option.label}`}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <p className="type-caption uppercase tracking-[0.18em] text-primary/76">投遞狀態</p>
              <div className="flex flex-wrap gap-2">
                {STATUS_OPTIONS.map((option) => (
                  <Button
                    key={option.key}
                    size="sm"
                    variant={statusFilter === option.key ? 'primary' : 'outline'}
                    onClick={() => handleStatusFilterChange(option.key)}
                    aria-pressed={statusFilter === option.key}
                    aria-label={`篩選 ${option.label}`}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>

            <Input
              id="notifications-error-reason"
              label="錯誤原因關鍵字"
              value={errorReasonInput}
              onChange={(event) => handleErrorReasonFilterChange(event.target.value)}
              placeholder="例如 endpoint、timeout、push"
              helperText="用關鍵字縮小補送需求。"
            />
          </div>
        </div>
      </NotificationsFocusBar>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-8">
        <div className="space-y-8">
          {listError ? (
            <NotificationsStatePanel
              tone="error"
              eyebrow="Notifications Feed"
              title="通知列表暫時沒有順利回來"
              description="這不是空白，而是資料載入失敗。重新整理後，我們會把需要照看與尚未閱讀的提醒帶回來。"
              actions={
                <>
                  <Button
                    leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                    loading={refreshing}
                    onClick={() => void handleRefresh()}
                  >
                    重新整理列表
                  </Button>
                  {hasFiltersApplied ? (
                    <Button variant="outline" onClick={handleResetFilters}>
                      清除篩選後再試
                    </Button>
                  ) : null}
                </>
              }
            />
          ) : items.length === 0 ? (
            <NotificationsStatePanel
              tone="quiet"
              eyebrow="Quiet Pulse"
              title={hasFiltersApplied ? '目前沒有符合這組焦點的提醒' : '目前沒有新的通知'}
              description={
                hasFiltersApplied
                  ? '你已經把範圍縮得很精準了。放寬條件後，可以重新看到其他已讀、未讀或需要補送的提醒。'
                  : '現在是一段平靜的空檔。當伴侶更新日記、回覆卡片，或系統需要你接住某個訊號時，這裡會再亮起來。'
              }
              actions={
                hasFiltersApplied ? (
                  <Button variant="outline" onClick={handleResetFilters}>
                    清除篩選
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <>
              <NotificationsSection
                eyebrow="Needs Care"
                title="先處理需要你照看的提醒"
                description="把可能影響送達、需要補送，或正在節流中的提醒拉到前面，讓你先穩住真正急迫的地方。"
                count={attentionItems.length}
              >
                <div className="space-y-4">
                  {!attentionItems.length ? (
                    <NotificationsStatePanel
                      tone="quiet"
                      eyebrow="Needs Care"
                      title="目前沒有需要補送或節流中的提醒"
                      description="這一區維持安靜，代表通知系統正平穩運作，沒有急著要你接手的投遞問題。"
                    />
                  ) : attentionRows.length ? (
                    attentionRows.map((item) => (
                      <NotificationPulseRow
                        key={item.id}
                        actionType={item.action_type}
                        status={item.status}
                        title={getTitle(item)}
                        description={getDescription(item)}
                        timeLabel={formatTime(item.created_at)}
                        unread={!item.is_read}
                        support={getSectionSupport(item)}
                        errorMessage={item.status === 'FAILED' ? item.error_message : null}
                        actions={renderNotificationActions(item)}
                      />
                    ))
                  ) : featuredInAttention ? (
                    <NotificationsStatePanel
                      tone="quiet"
                      eyebrow="Needs Care"
                      title="最需要你先接住的一則，已經放在上方"
                      description="這一區目前沒有第二則同樣急迫的提醒。你可以先處理首頁聚焦的那一則，再回來看看是否需要同步最新狀態。"
                    />
                  ) : null}
                </div>
              </NotificationsSection>

              <NotificationsSection
                eyebrow="Unread Now"
                title="剛剛抵達、還沒被接住的訊號"
                description="這些提醒不是壓力，而是讓你重新進入 Haven 的柔和入口。它們保留著剛抵達時最清楚的脈動。"
                count={unreadPulseItems.length}
              >
                <div className="space-y-4">
                  {!unreadPulseItems.length ? (
                    <NotificationsStatePanel
                      tone="quiet"
                      eyebrow="Unread Now"
                      title="目前沒有新的未讀提醒"
                      description="如果新的日記、卡片回覆或邀請抵達，這裡會先亮起來，幫你用更 calm 的順序重新進入對話。"
                    />
                  ) : unreadRows.length ? (
                    unreadRows.map((item) => (
                      <NotificationPulseRow
                        key={item.id}
                        actionType={item.action_type}
                        status={item.status}
                        title={getTitle(item)}
                        description={getDescription(item)}
                        timeLabel={formatTime(item.created_at)}
                        unread={!item.is_read}
                        support={getSectionSupport(item)}
                        errorMessage={item.status === 'FAILED' ? item.error_message : null}
                        actions={renderNotificationActions(item)}
                      />
                    ))
                  ) : featuredInUnread ? (
                    <NotificationsStatePanel
                      tone="quiet"
                      eyebrow="Unread Now"
                      title="這一刻最值得先看的未讀提醒，已經被放到首頁"
                      description="其餘未讀訊號目前已經沒有更多需要分心的地方。先從上方那一則開始就好。"
                    />
                  ) : null}
                </div>
              </NotificationsSection>

              <NotificationsSection
                eyebrow="Quiet Archive"
                title="已經落下，但值得回來看的提醒"
                description="不是每一則提醒都在催促你。這一區保留那些已讀或較低壓力的事件，讓你在需要時能平靜回看。"
                count={archiveItems.length}
              >
                <div className="space-y-4">
                  {!archiveItems.length ? (
                    <NotificationsStatePanel
                      tone="quiet"
                      eyebrow="Quiet Archive"
                      title="暫時還沒有安穩落下的提醒"
                      description="當更多通知被看過、被接住後，它們會留在這裡，成為一片不需要急著處理的回望區。"
                    />
                  ) : archiveRows.length ? (
                    archiveRows.map((item) => (
                      <NotificationPulseRow
                        key={item.id}
                        actionType={item.action_type}
                        status={item.status}
                        title={getTitle(item)}
                        description={getDescription(item)}
                        timeLabel={formatTime(item.created_at)}
                        unread={!item.is_read}
                        support={getSectionSupport(item)}
                        errorMessage={item.status === 'FAILED' ? item.error_message : null}
                        actions={renderNotificationActions(item)}
                      />
                    ))
                  ) : featuredInArchive ? (
                    <NotificationsStatePanel
                      tone="quiet"
                      eyebrow="Quiet Archive"
                      title="這一區最有代表性的一則，已經在上方被安靜聚焦"
                      description="現在 archive 裡沒有第二層需要你停留的提醒，等新的已讀事件累積起來，這裡會再次變得更豐富。"
                    />
                  ) : null}
                </div>
              </NotificationsSection>
            </>
          )}
        </div>

        {statsError && !hasDiagnosticsData ? (
          <NotificationsStatePanel
            tone="error"
            eyebrow="Diagnostics Rail"
            title="診斷側欄暫時沒有回來"
            description="主要通知列表仍可閱讀。重新整理後，我們會把送達率、趨勢與失敗原因摘要帶回來。"
            actions={
              <Button
                variant="outline"
                leftIcon={<RefreshCw className="h-4 w-4" aria-hidden />}
                onClick={() => void handleRefresh()}
              >
                重新整理側欄
              </Button>
            }
          />
        ) : (
          <NotificationsDiagnosticsRail
            eyebrow="Diagnostics Rail"
            title="讓你安心的背景資訊"
            description="運作狀態、近期趨勢和失敗原因仍然可見，但它們退居幕後，只在你需要更深入理解時才說話。"
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <div className="rounded-[1.75rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                <div className="flex items-center gap-2 text-card-foreground">
                  <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Health Score</p>
                </div>
                <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{healthScore}</p>
                <p className="mt-1 type-caption text-muted-foreground">高分代表更多提醒正穩定地抵達對方身邊。</p>
              </div>
              <div className="rounded-[1.75rem] border border-white/56 bg-white/72 p-4 shadow-soft">
                <div className="flex items-center gap-2 text-card-foreground">
                  <Sparkles className="h-4 w-4 text-primary" aria-hidden />
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Queue & Unread</p>
                </div>
                <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">
                  {stats?.queued_count ?? 0} / {stats?.unread_count ?? unreadCount}
                </p>
                <p className="mt-1 type-caption text-muted-foreground">前者是待送佇列，後者是對方尚未打開的提醒。</p>
              </div>
              <div className="rounded-[1.75rem] border border-white/56 bg-white/72 p-4 shadow-soft sm:col-span-2 xl:col-span-1">
                <div className="flex items-center gap-2 text-card-foreground">
                  <AlertTriangle className="h-4 w-4 text-primary" aria-hidden />
                  <p className="type-caption uppercase tracking-[0.18em] text-primary/76">Recent 24h</p>
                </div>
                <p className="mt-2 text-2xl font-semibold text-card-foreground tabular-nums">{stats?.recent_24h_count ?? 0}</p>
                <p className="mt-1 type-caption text-muted-foreground">
                  最近 24 小時失敗 {stats?.recent_24h_failed_count ?? 0}，最後事件 {lastEventLabel}。
                </p>
              </div>
            </div>

            <NotificationsTrendCard
              windowDays={statsWindowDays}
              days={stats?.window_daily ?? []}
              trendMax={trendMax}
              focusedDay={focusedDay}
              onWindowChange={handleWindowDaysChange}
              onHoverDay={setHoveredDay}
            />

            <GlassCard className="overflow-hidden rounded-[2.25rem] border-white/52 bg-white/78 p-5 shadow-soft md:p-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <p className="type-micro uppercase text-primary/80">Failure Shortcuts</p>
                  <h3 className="type-section-title text-card-foreground">最常見的補送原因</h3>
                  <p className="type-body-muted text-muted-foreground">
                    這些不是讓你焦慮的錯誤清單，而是幫你快速切到真正需要補送的那一類提醒。
                  </p>
                </div>

                {topFailureReasons.length ? (
                  <div className="flex flex-wrap gap-2">
                    {topFailureReasons.map((reason) => (
                      <Button
                        key={reason.reason}
                        size="sm"
                        variant="outline"
                        onClick={() => setStatusAndErrorReason('FAILED', reason.reason)}
                        aria-label={`依錯誤原因 ${reason.reason} 篩選`}
                      >
                        {reason.reason} · {reason.count}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <NotificationsStatePanel
                    tone="quiet"
                    eyebrow="Failure Shortcuts"
                    title="目前視窗內沒有 FAILED 事件"
                    description="這通常是好消息。當補送需求再次出現時，這裡會先替你整理出最常見的原因。"
                  />
                )}
              </div>
            </GlassCard>
          </NotificationsDiagnosticsRail>
        )}
      </div>
    </div>
  );
}
