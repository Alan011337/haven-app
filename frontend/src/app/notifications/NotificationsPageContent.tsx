'use client';

import Link from 'next/link';
import {
  Bell,
  BookOpen,
  Check,
  CheckCheck,
  HandHeart,
  MessageCircleMore,
  Pause,
  RefreshCw,
} from 'lucide-react';

import {
  useNotificationsData,
  formatTime,
  getTitle,
  getActionLink,
} from '@/features/notifications/useNotificationsData';
import type { NotificationEventItem } from '@/services/api-client';

/* ── Relationship-meaningful description (ignores delivery status) ── */

function getRelationshipDescription(item: NotificationEventItem): string {
  if (item.action_type === 'JOURNAL') return '前往伴侶心聲查看最新內容。';
  if (item.action_type === 'MEDIATION_INVITE')
    return '填寫三題換位思考，可查看彼此心聲與下次 SOP。';
  if (item.action_type === 'COOLDOWN_STARTED')
    return '伴侶需要暫停一下，建議稍後再好好聊。';
  return '前往每日共感或牌組查看新回覆。';
}

/* ── Icon resolver ── */

function getItemIcon(actionType: string) {
  if (actionType === 'JOURNAL') return BookOpen;
  if (actionType === 'MEDIATION_INVITE') return HandHeart;
  if (actionType === 'COOLDOWN_STARTED') return Pause;
  return MessageCircleMore;
}

/* ── Main content ── */

export default function NotificationsPageContent() {
  const {
    items,
    loading,
    refreshing,
    retryingId,
    onlyUnread,
    unreadCount,
    handleRefresh,
    handleMarkAllRead,
    handleToggleUnread,
    handleMarkOneRead,
    handleRetryDelivery,
  } = useNotificationsData();

  return (
    <div className="space-y-8 md:space-y-10">
      {/* ── Page identity ── */}
      <div className="space-y-3 animate-slide-up-fade">
        <h1 className="font-art text-[2rem] leading-[1.05] tracking-tight text-gradient-gold md:text-[2.8rem]">
          伴侶動態
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          你們之間的每一個心動瞬間。
        </p>
      </div>

      {/* ── Compact action bar ── */}
      <div className="flex items-center gap-2 animate-slide-up-fade-1">
        <button
          type="button"
          onClick={handleToggleUnread}
          className={[
            'inline-flex items-center gap-1.5 rounded-button px-4 py-2 text-xs font-medium transition-all duration-haven ease-haven focus-ring-premium',
            onlyUnread
              ? 'border border-primary/20 bg-primary/8 text-card-foreground shadow-soft'
              : 'border border-white/50 bg-white/60 text-muted-foreground hover:text-card-foreground hover:bg-white/80',
          ].join(' ')}
          aria-pressed={onlyUnread}
        >
          未讀
          {unreadCount > 0 && (
            <span className="tabular-nums text-primary">{unreadCount}</span>
          )}
        </button>

        {unreadCount > 0 && (
          <button
            type="button"
            onClick={handleMarkAllRead}
            className="inline-flex items-center gap-1.5 rounded-button border border-white/50 bg-white/60 px-4 py-2 text-xs font-medium text-muted-foreground transition-all duration-haven ease-haven hover:text-card-foreground hover:bg-white/80 focus-ring-premium"
          >
            <CheckCheck className="h-3.5 w-3.5" aria-hidden />
            全部已讀
          </button>
        )}

        <button
          type="button"
          onClick={handleRefresh}
          className="inline-flex items-center justify-center rounded-button border border-white/50 bg-white/60 p-2 text-muted-foreground transition-all duration-haven ease-haven hover:text-card-foreground hover:bg-white/80 focus-ring-premium"
          aria-label="重新整理"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`}
          />
        </button>
      </div>

      {/* ── Notification feed ── */}
      <section className="animate-slide-up-fade-2" aria-label="通知列表">
        {loading ? (
          <div
            className="py-16 text-center text-sm text-muted-foreground animate-breathe"
            role="status"
          >
            載入中...
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-[2rem] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(248,244,238,0.78))] px-6 py-14 text-center shadow-soft">
            <Bell
              className="mx-auto h-8 w-8 text-primary/40"
              aria-hidden
            />
            <p className="mt-4 font-art text-lg font-medium text-card-foreground/80">
              目前沒有新動態
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              有新的互動時，這裡會提醒你。
            </p>
            <Link
              href="/"
              className="mt-6 inline-flex items-center justify-center rounded-button border border-border/70 bg-card/82 px-5 py-2.5 text-sm font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift focus-ring-premium"
            >
              返回首頁
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {items.map((item, idx) => {
              const ItemIcon = getItemIcon(item.action_type);
              const stagger =
                idx < 6
                  ? `animate-slide-up-fade${idx > 0 ? `-${idx}` : ''}`
                  : '';
              const isFailed =
                item.status === 'FAILED' || item.status === 'THROTTLED';

              return (
                <li
                  key={item.id}
                  className={`rounded-[1.5rem] border border-white/50 bg-white/70 shadow-soft backdrop-blur-sm transition-all duration-haven ease-haven hover:-translate-y-px hover:shadow-lift overflow-hidden ${stagger}`}
                >
                  <div
                    className={`px-5 py-4 ${!item.is_read ? 'border-l-[3px] border-l-primary/35 bg-primary/[0.03]' : ''}`}
                  >
                    <div className="flex items-start gap-3">
                      <ItemIcon
                        className={`mt-0.5 h-4 w-4 shrink-0 ${item.is_read ? 'text-muted-foreground/50' : 'text-primary/50'}`}
                        aria-hidden
                      />

                      <div className="min-w-0 flex-1">
                        {/* Title + unread dot */}
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-medium text-card-foreground">
                            {getTitle(item)}
                          </h3>
                          {!item.is_read && (
                            <span
                              className="h-2 w-2 shrink-0 rounded-full bg-primary"
                              aria-label="未讀"
                            />
                          )}
                        </div>

                        {/* Relationship description */}
                        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                          {getRelationshipDescription(item)}
                        </p>

                        {/* Gentle failed recovery line */}
                        {isFailed && (
                          <p className="mt-1.5 text-xs text-muted-foreground/70">
                            通知暫時未送達
                          </p>
                        )}

                        {/* Footer: timestamp + actions */}
                        <div className="mt-3 flex items-center justify-between gap-3">
                          <span className="text-xs tabular-nums text-muted-foreground/70">
                            {formatTime(item.created_at)}
                          </span>

                          <div className="flex items-center gap-3">
                            {!item.is_read && (
                              <button
                                type="button"
                                onClick={() =>
                                  void handleMarkOneRead(item.id)
                                }
                                className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors duration-haven ease-haven hover:text-card-foreground focus-ring-premium rounded"
                              >
                                <Check
                                  className="h-3.5 w-3.5"
                                  aria-hidden
                                />
                                已讀
                              </button>
                            )}

                            {isFailed && (
                              <button
                                type="button"
                                onClick={() =>
                                  void handleRetryDelivery(item.id)
                                }
                                disabled={retryingId === item.id}
                                className={`inline-flex items-center gap-1 text-xs font-medium rounded focus-ring-premium transition-colors duration-haven ease-haven ${
                                  retryingId === item.id
                                    ? 'text-muted-foreground/50 cursor-not-allowed'
                                    : 'text-primary hover:opacity-80'
                                }`}
                              >
                                <RefreshCw
                                  className={`h-3 w-3 ${retryingId === item.id ? 'animate-spin' : ''}`}
                                  aria-hidden
                                />
                                重新傳送
                              </button>
                            )}

                            <Link
                              href={getActionLink(item)}
                              className="text-xs font-medium text-primary transition-opacity duration-haven ease-haven hover:opacity-80 focus-ring-premium rounded"
                            >
                              前往查看
                            </Link>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
