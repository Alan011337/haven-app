import { expect, test, type Route } from '@playwright/test';

type NotificationActionType = 'JOURNAL' | 'CARD' | 'COOLDOWN_STARTED' | 'MEDIATION_INVITE';
type NotificationStatus = 'QUEUED' | 'SENT' | 'FAILED' | 'THROTTLED';

type TestNotificationItem = {
  id: string;
  channel: string;
  action_type: NotificationActionType;
  status: NotificationStatus;
  receiver_user_id: string | null;
  sender_user_id: string | null;
  source_session_id: string | null;
  receiver_email: string;
  dedupe_key: string | null;
  is_read: boolean;
  read_at: string | null;
  error_message: string | null;
  created_at: string;
};

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};
const API_ORIGIN = 'http://127.0.0.1:8000/api';

function hoursAgo(now: number, hours: number) {
  return new Date(now - hours * 60 * 60 * 1000).toISOString();
}

function withParams(urlString: string) {
  return new URL(urlString);
}

function filterNotifications(items: TestNotificationItem[], url: URL) {
  const unreadOnly = url.searchParams.get('unread_only') === 'true';
  const actionType = url.searchParams.get('action_type');
  const status = url.searchParams.get('status');
  const errorReason = url.searchParams.get('error_reason')?.trim().toLowerCase() ?? '';

  return items.filter((item) => {
    if (unreadOnly && item.is_read) return false;
    if (actionType && item.action_type !== actionType) return false;
    if (status && item.status !== status) return false;
    if (errorReason && !(item.error_message ?? '').toLowerCase().includes(errorReason)) return false;
    return true;
  });
}

function buildDailyStats(items: TestNotificationItem[], windowDays: number) {
  const grouped = new Map<string, {
    date: string;
    total_count: number;
    sent_count: number;
    failed_count: number;
    throttled_count: number;
    queued_count: number;
  }>();

  for (const item of items) {
    const date = item.created_at.slice(0, 10);
    const current = grouped.get(date) ?? {
      date,
      total_count: 0,
      sent_count: 0,
      failed_count: 0,
      throttled_count: 0,
      queued_count: 0,
    };

    current.total_count += 1;
    if (item.status === 'SENT') current.sent_count += 1;
    if (item.status === 'FAILED') current.failed_count += 1;
    if (item.status === 'THROTTLED') current.throttled_count += 1;
    if (item.status === 'QUEUED') current.queued_count += 1;
    grouped.set(date, current);
  }

  return Array.from(grouped.values())
    .sort((left, right) => left.date.localeCompare(right.date))
    .slice(-windowDays);
}

function buildNotificationStats(items: TestNotificationItem[], url: URL) {
  const windowDays = Number(url.searchParams.get('window_days') ?? '7') || 7;
  const filteredItems = filterNotifications(items, url);
  const failedReasons = filteredItems
    .filter((item) => item.status === 'FAILED' && item.error_message)
    .reduce<Map<string, number>>((accumulator, item) => {
      const reason = item.error_message as string;
      accumulator.set(reason, (accumulator.get(reason) ?? 0) + 1);
      return accumulator;
    }, new Map());

  const sortedReasons = Array.from(failedReasons.entries())
    .sort((left, right) => right[1] - left[1])
    .map(([reason, count]) => ({ reason, count }));

  const lastEventAt = filteredItems
    .map((item) => item.created_at)
    .sort((left, right) => right.localeCompare(left))[0] ?? null;

  return {
    total_count: filteredItems.length,
    unread_count: filteredItems.filter((item) => !item.is_read).length,
    queued_count: filteredItems.filter((item) => item.status === 'QUEUED').length,
    sent_count: filteredItems.filter((item) => item.status === 'SENT').length,
    failed_count: filteredItems.filter((item) => item.status === 'FAILED').length,
    throttled_count: filteredItems.filter((item) => item.status === 'THROTTLED').length,
    journal_count: filteredItems.filter((item) => item.action_type === 'JOURNAL').length,
    card_count: filteredItems.filter((item) => item.action_type === 'CARD').length,
    recent_24h_count: filteredItems.filter((item) => Date.now() - new Date(item.created_at).getTime() <= 24 * 60 * 60 * 1000).length,
    recent_24h_failed_count: filteredItems.filter((item) => item.status === 'FAILED' && Date.now() - new Date(item.created_at).getTime() <= 24 * 60 * 60 * 1000).length,
    window_days: windowDays,
    window_total_count: filteredItems.length,
    window_sent_count: filteredItems.filter((item) => item.status === 'SENT').length,
    window_failed_count: filteredItems.filter((item) => item.status === 'FAILED').length,
    window_throttled_count: filteredItems.filter((item) => item.status === 'THROTTLED').length,
    window_queued_count: filteredItems.filter((item) => item.status === 'QUEUED').length,
    window_daily: buildDailyStats(filteredItems, windowDays),
    window_top_failure_reasons: sortedReasons,
    last_event_at: lastEventAt,
  };
}

function buildNotificationsFixture(now: number): TestNotificationItem[] {
  return [
    {
      id: 'n-failed-journal',
      channel: 'EMAIL',
      action_type: 'JOURNAL',
      status: 'FAILED',
      receiver_user_id: 'receiver',
      sender_user_id: 'sender',
      source_session_id: 'session-1',
      receiver_email: 'pulse@example.com',
      dedupe_key: 'dedupe-1',
      is_read: false,
      read_at: null,
      error_message: 'daily digest timeout',
      created_at: hoursAgo(now, 1),
    },
    {
      id: 'n-failed-mediation',
      channel: 'EMAIL',
      action_type: 'MEDIATION_INVITE',
      status: 'FAILED',
      receiver_user_id: 'receiver',
      sender_user_id: 'sender',
      source_session_id: 'session-2',
      receiver_email: 'pulse@example.com',
      dedupe_key: 'dedupe-2',
      is_read: false,
      read_at: null,
      error_message: 'push endpoint missing',
      created_at: hoursAgo(now, 6),
    },
    {
      id: 'n-unread-journal',
      channel: 'EMAIL',
      action_type: 'JOURNAL',
      status: 'SENT',
      receiver_user_id: 'receiver',
      sender_user_id: 'sender',
      source_session_id: 'session-3',
      receiver_email: 'pulse@example.com',
      dedupe_key: 'dedupe-3',
      is_read: false,
      read_at: null,
      error_message: null,
      created_at: hoursAgo(now, 2),
    },
    {
      id: 'n-unread-card',
      channel: 'EMAIL',
      action_type: 'CARD',
      status: 'SENT',
      receiver_user_id: 'receiver',
      sender_user_id: 'sender',
      source_session_id: 'session-4',
      receiver_email: 'pulse@example.com',
      dedupe_key: 'dedupe-4',
      is_read: false,
      read_at: null,
      error_message: null,
      created_at: hoursAgo(now, 12),
    },
    {
      id: 'n-archive-journal',
      channel: 'EMAIL',
      action_type: 'JOURNAL',
      status: 'SENT',
      receiver_user_id: 'receiver',
      sender_user_id: 'sender',
      source_session_id: 'session-5',
      receiver_email: 'pulse@example.com',
      dedupe_key: 'dedupe-5',
      is_read: true,
      read_at: hoursAgo(now, 20),
      error_message: null,
      created_at: hoursAgo(now, 30),
    },
  ];
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: MOCK_API_HEADERS,
    body: JSON.stringify(data),
  });
}

test.describe('Notifications pulse center', () => {
  test.describe.configure({ mode: 'serial' });
  test.use({ bypassCSP: true });

  test('prioritizes meaningful notifications and supports unread, failure, retry, and read flows', async ({ page }) => {
    test.slow();
    const now = Date.now();
    let notifications = buildNotificationsFixture(now);

    let retryCalls = 0;
    let markReadCalls = 0;

    await page.route(`${API_ORIGIN}/**`, async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: MOCK_API_HEADERS,
        });
        return;
      }

      const pathname = new URL(route.request().url()).pathname;
      if (pathname.startsWith('/api/journals/')) {
        await fulfillJson(route, []);
        return;
      }

      await fulfillJson(route, {});
    });

    await page.route(`${API_ORIGIN}/auth/token`, async (route) => {
      await fulfillJson(route, {
        access_token: 'notifications-test-token',
        token_type: 'bearer',
      });
    });

    await page.route(`${API_ORIGIN}/users/me**`, async (route) => {
      await fulfillJson(route, {
        id: 'user-1',
        email: 'pulse@example.com',
        full_name: 'Pulse User',
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Partner',
        partner_nickname: 'P',
        savings_score: 42,
        created_at: hoursAgo(now, 300),
      });
    });

    await page.route(`${API_ORIGIN}/users/partner-status`, async (route) => {
      await fulfillJson(route, {
        has_partner: true,
        latest_journal_at: notifications.find((item) => item.action_type === 'JOURNAL')?.created_at ?? null,
        current_score: 42,
        unread_notification_count: notifications.filter((item) => !item.is_read).length,
      });
    });

    await page.route(/^http:\/\/127\.0\.0\.1:8000\/api\/users\/notifications\/stats(?:\?.*)?$/, async (route) => {
      const url = withParams(route.request().url());
      await fulfillJson(route, buildNotificationStats(notifications, url));
    });

    await page.route(`${API_ORIGIN}/users/notifications/*/read`, async (route) => {
      const notificationId = route.request().url().split('/').at(-2);
      notifications = notifications.map((item) =>
        item.id === notificationId
          ? { ...item, is_read: true, read_at: new Date().toISOString() }
          : item,
      );
      markReadCalls += 1;
      await fulfillJson(route, { updated: 1 });
    });

    await page.route(`${API_ORIGIN}/users/notifications/*/retry`, async (route) => {
      const notificationId = route.request().url().split('/').at(-2);
      notifications = notifications.map((item) =>
        item.id === notificationId
          ? { ...item, status: 'SENT', error_message: null }
          : item,
      );
      retryCalls += 1;
      await fulfillJson(route, { queued: true });
    });

    await page.route(/^http:\/\/127\.0\.0\.1:8000\/api\/users\/notifications(?:\?.*)?$/, async (route) => {
      const url = withParams(route.request().url());
      const limit = Number(url.searchParams.get('limit') ?? '50') || 50;
      await fulfillJson(route, filterNotifications(notifications, url).slice(0, limit));
    });

    await page.goto('/notifications');

    await expect(page.getByRole('heading', { name: '每一則提醒，都應該讓你更靠近真正重要的事。' })).toBeVisible();
    await expect(page.getByText('目前可見 5 則')).toBeVisible();
    await expect(page.getByRole('heading', { level: 3, name: '調解模式邀請' })).toBeVisible();

    await page.getByRole('button', { name: /push endpoint missing/ }).click();
    await expect(page.getByLabel('錯誤原因關鍵字')).toHaveValue('push endpoint missing');
    await expect(page.getByText('目前可見 1 則')).toBeVisible();

    await page.getByRole('button', { name: '清除所有通知篩選' }).click();
    await expect(page.getByText('目前可見 5 則')).toBeVisible();

    await page.getByRole('button', { name: '僅看未讀' }).click();
    await expect(page.getByText('目前可見 4 則')).toBeVisible();
    await expect(page.getByText('尚未閱讀 4')).toBeVisible();

    await page.getByRole('button', { name: /重新嘗試投遞通知|重送通知/ }).first().click();
    await expect.poll(() => retryCalls).toBe(1);
    await expect(page.getByText('需要照看 1')).toBeVisible();

    await page.getByRole('button', { name: /標記這則通知為已讀|標記已讀/ }).first().click();
    await expect.poll(() => markReadCalls).toBe(1);
    await expect(page.getByText('尚未閱讀 3')).toBeVisible();
  });

  test('shows all relationship signal filters and only enables bulk mark-read for supported scopes', async ({ page }) => {
    test.slow();
    const now = Date.now();
    let notifications = buildNotificationsFixture(now);
    let bulkMarkReadCalls = 0;
    let lastBulkActionType: string | null = null;

    await page.route(`${API_ORIGIN}/**`, async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: MOCK_API_HEADERS,
        });
        return;
      }

      const pathname = new URL(route.request().url()).pathname;
      if (pathname.startsWith('/api/journals/')) {
        await fulfillJson(route, []);
        return;
      }

      await fulfillJson(route, {});
    });

    await page.route(`${API_ORIGIN}/auth/token`, async (route) => {
      await fulfillJson(route, {
        access_token: 'notifications-test-token',
        token_type: 'bearer',
      });
    });

    await page.route(`${API_ORIGIN}/users/me**`, async (route) => {
      await fulfillJson(route, {
        id: 'user-1',
        email: 'pulse@example.com',
        full_name: 'Pulse User',
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Partner',
        partner_nickname: 'P',
        savings_score: 42,
        created_at: hoursAgo(now, 300),
      });
    });

    await page.route(`${API_ORIGIN}/users/partner-status`, async (route) => {
      await fulfillJson(route, {
        has_partner: true,
        latest_journal_at: notifications.find((item) => item.action_type === 'JOURNAL')?.created_at ?? null,
        current_score: 42,
        unread_notification_count: notifications.filter((item) => !item.is_read).length,
      });
    });

    await page.route(`${API_ORIGIN}/users/notifications/mark-read**`, async (route) => {
      const actionType = withParams(route.request().url()).searchParams.get('action_type');
      lastBulkActionType = actionType;
      notifications = notifications.map((item) => {
        if (!actionType) {
          return { ...item, is_read: true, read_at: new Date().toISOString() };
        }

        return item.action_type.toLowerCase() === actionType
          ? { ...item, is_read: true, read_at: new Date().toISOString() }
          : item;
      });
      bulkMarkReadCalls += 1;
      await fulfillJson(route, { updated: notifications.length });
    });

    await page.route(/^http:\/\/127\.0\.0\.1:8000\/api\/users\/notifications\/stats(?:\?.*)?$/, async (route) => {
      const url = withParams(route.request().url());
      await fulfillJson(route, buildNotificationStats(notifications, url));
    });

    await page.route(/^http:\/\/127\.0\.0\.1:8000\/api\/users\/notifications(?:\?.*)?$/, async (route) => {
      const url = withParams(route.request().url());
      const limit = Number(url.searchParams.get('limit') ?? '50') || 50;
      await fulfillJson(route, filterNotifications(notifications, url).slice(0, limit));
    });

    await page.goto('/notifications');

    await expect(page.getByRole('button', { name: /篩選 調解邀請|調解邀請/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /篩選 冷卻提醒|冷卻提醒/ })).toBeVisible();

    await page.getByRole('button', { name: /篩選 調解邀請|調解邀請/ }).click();
    await expect(page.getByText('目前可見 1 則')).toBeVisible();
    await expect(page.getByRole('button', { name: '全部標記為已讀' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '清除目前焦點篩選' })).toBeVisible();
    await expect(page.getByText(/批次整理先交給單則處理/)).toBeVisible();

    await page.getByRole('button', { name: '清除所有通知篩選' }).click();
    await page.getByRole('button', { name: /篩選 日記更新|日記更新/ }).click();
    await expect(page.getByText('目前可見 3 則')).toBeVisible();

    const markAllReadButton = page.getByRole('button', { name: '全部標記為已讀' });
    await expect(markAllReadButton).toBeVisible();
    await markAllReadButton.click();
    await expect.poll(() => bulkMarkReadCalls).toBe(1);
    await expect.poll(() => lastBulkActionType).toBe('journal');
    await expect(page.getByText('未讀 0')).toBeVisible();

    await page.getByRole('button', { name: '清除所有通知篩選' }).click();
    await expect(page.getByText('未讀 2')).toBeVisible();
  });
});
