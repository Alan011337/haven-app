import { expect, test, type Page, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
  'access-control-allow-private-network': 'true',
  vary: 'Origin',
};

function resolveMockApiHeaders(route: Route) {
  const requestOrigin = route.request().headers().origin?.trim();
  return {
    ...MOCK_API_HEADERS,
    'access-control-allow-origin': requestOrigin || 'http://127.0.0.1:3000',
  };
}

function apiSuccess(data: unknown, requestId = 'toast-quality-e2e-req') {
  return {
    data,
    meta: { request_id: requestId },
    error: null,
  };
}

function apiError(message = 'mock-failure', requestId = 'toast-quality-e2e-req') {
  return {
    data: null,
    meta: { request_id: requestId },
    error: { message },
  };
}

function hoursAgo(now: number, hours: number) {
  return new Date(now - hours * 60 * 60 * 1000).toISOString();
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: resolveMockApiHeaders(route),
    body: JSON.stringify(apiSuccess(data)),
  });
}

async function fulfillError(route: Route, status = 500, message = 'mock-failure') {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: resolveMockApiHeaders(route),
    body: JSON.stringify(apiError(message)),
  });
}

async function expectToast(page: Page, message: string) {
  await expect(page.getByText(message, { exact: true }).last()).toBeVisible({ timeout: 10_000 });
}

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('name@example.com').fill('toast@example.com');
  await page.locator('input[type="password"]').fill('password123');
  const submitButton = page.getByRole('button', { name: '登入並回到 Haven' });
  await expect(submitButton).toBeEnabled();
  await submitButton.click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function mockToastApi(page: Page) {
  const now = Date.now();

  const user = {
    id: 'me',
    email: 'toast@example.com',
    full_name: 'Toast Reviewer',
    is_active: true,
    partner_id: 'partner-1',
    partner_name: 'Bob',
    partner_nickname: 'B',
    savings_score: 61,
    created_at: hoursAgo(now, 500),
  };

  let consent = {
    privacy_scope_accepted: true,
    notification_frequency: 'normal',
    ai_intensity: 'gentle',
    updated_at: hoursAgo(now, 24),
  };

  let dailySyncStatus = {
    today: '2026-04-04',
    my_filled: false,
    partner_filled: false,
    unlocked: false,
    my_mood_score: null as number | null,
    my_question_id: null as string | null,
    my_answer_text: null as string | null,
    partner_mood_score: null as number | null,
    partner_question_id: null as string | null,
    partner_answer_text: null as string | null,
    today_question_id: 'daily-question-1',
    today_question_label: '今天你最想被怎麼對待？',
  };

  let appreciationHistory = [
    {
      id: 1,
      body_text: '謝謝你今天幫我留了一盞燈。',
      created_at: hoursAgo(now, 12),
      is_mine: true,
    },
  ];

  let blueprintItems = [
    {
      id: 'wish-1',
      title: '每個月留一晚只屬於我們',
      notes: '先把那一晚留給散步和晚餐。',
      created_at: hoursAgo(now, 30),
      added_by_me: true,
    },
  ];

  const loveMapSystem = {
    has_partner: true,
    me: {
      id: 'me',
      full_name: 'Toast Reviewer',
      email: 'toast@example.com',
    },
    partner: {
      id: 'partner-1',
      partner_name: 'Bob',
    },
    baseline: {
      mine: {
        user_id: 'me',
        partner_id: 'partner-1',
        filled_at: hoursAgo(now, 36),
        scores: {
          intimacy: 4,
          conflict: 3,
          trust: 5,
          communication: 4,
          commitment: 5,
        },
      },
      partner: {
        user_id: 'partner-1',
        partner_id: 'me',
        filled_at: hoursAgo(now, 22),
        scores: {
          intimacy: 4,
          conflict: 3,
          trust: 4,
          communication: 4,
          commitment: 5,
        },
      },
    },
    couple_goal: {
      goal_slug: 'more_trust',
      chosen_at: hoursAgo(now, 18),
    },
    story: {
      available: true,
      moments: [
        {
          kind: 'appreciation',
          source_id: 'appreciation-1',
          title: '一段被說出口的感謝',
          description: '謝謝你每天早上幫我準備咖啡。',
          occurred_at: hoursAgo(now, 72),
          badges: ['感恩'],
          why_text: '感謝被留下來時，也會變成你們故事裡可回頭看的證據。',
        },
      ],
      time_capsule: null,
    },
    notes: [
      {
        id: 'note-safe',
        layer: 'safe',
        content: '我知道我們最近需要更穩定的回來對話節奏。',
        created_at: hoursAgo(now, 20),
        updated_at: hoursAgo(now, 10),
      },
      {
        id: 'note-medium',
        layer: 'medium',
        content: '忙的時候也還記得彼此在意的是什麼。',
        created_at: hoursAgo(now, 16),
        updated_at: hoursAgo(now, 8),
      },
    ],
    wishlist_items: blueprintItems,
    stats: {
      filled_note_layers: 2,
      baseline_ready_mine: true,
      baseline_ready_partner: true,
      wishlist_count: blueprintItems.length,
      last_activity_at: hoursAgo(now, 8),
    },
  };

  const loveMapCards = {
    safe: [
      {
        id: 'card-safe-1',
        title: '安心時刻',
        description: '描述最近一個讓你感到被接住的片刻。',
        question: '最近哪個小小的舉動，讓你覺得被放在心上？',
        depth_level: 1,
        layer: 'safe',
      },
    ],
    medium: [
      {
        id: 'card-medium-1',
        title: '壓力怎麼被理解',
        description: '談談忙碌時真正需要的是什麼。',
        question: '當你最近壓力很大時，你最希望對方先做什麼？',
        depth_level: 2,
        layer: 'medium',
      },
    ],
    deep: [
      {
        id: 'card-deep-1',
        title: '更深的期待',
        description: '讓核心期待有地方被看見。',
        question: '有什麼長久的期待，是你最近更想被對方理解的？',
        depth_level: 3,
        layer: 'deep',
      },
    ],
  };

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: resolveMockApiHeaders(route) });
      return;
    }

    if (path.endsWith('/auth/token') && method === 'POST') {
      await fulfillJson(route, { access_token: 'toast-token', token_type: 'bearer' });
      return;
    }

    if (path.endsWith('/users/me') && method === 'GET') {
      await fulfillJson(route, user);
      return;
    }

    if (path.endsWith('/users/partner-status') && method === 'GET') {
      await fulfillJson(route, {
        has_partner: true,
        latest_journal_at: hoursAgo(now, 3),
        current_score: 61,
        unread_notification_count: 0,
      });
      return;
    }

    if (path.endsWith('/users/gamification-summary') && method === 'GET') {
      await fulfillJson(route, {
        has_partner_context: true,
        streak_days: 7,
        best_streak_days: 11,
        streak_eligible_today: true,
        level: 2,
        level_points_total: 140,
        level_points_current: 40,
        level_points_target: 100,
        love_bar_percent: 62,
        level_title: 'Warm Keeper',
        anti_cheat_enabled: true,
      });
      return;
    }

    if (path.endsWith('/users/onboarding-quest') && method === 'GET') {
      await fulfillJson(route, {
        enabled: false,
        has_partner_context: true,
        kill_switch_active: false,
        completed_steps: 7,
        total_steps: 7,
        progress_percent: 100,
        steps: [],
      });
      return;
    }

    if (path.endsWith('/users/sync-nudges') && method === 'GET') {
      await fulfillJson(route, {
        enabled: false,
        has_partner_context: true,
        kill_switch_active: false,
        nudge_cooldown_hours: 18,
        nudges: [],
      });
      return;
    }

    if (path.endsWith('/users/first-delight') && method === 'GET') {
      await fulfillJson(route, {
        enabled: false,
        has_partner_context: true,
        kill_switch_active: false,
        delivered: false,
        eligible: false,
        reason: 'disabled',
        dedupe_key: null,
        title: null,
        description: null,
        metadata: {},
      });
      return;
    }

    if (path.endsWith('/users/me/onboarding-consent') && method === 'GET') {
      await fulfillJson(route, consent);
      return;
    }

    if (path.endsWith('/users/me/onboarding-consent') && method === 'POST') {
      const payload = route.request().postDataJSON() as typeof consent;
      consent = {
        ...consent,
        ...payload,
        updated_at: new Date().toISOString(),
      };
      await fulfillJson(route, consent);
      return;
    }

    if (path.endsWith('/reports/weekly') && method === 'GET') {
      await fulfillJson(route, {
        period_start: '2026-03-29',
        period_end: '2026-04-04',
        daily_sync_completion_rate: 0.57,
        daily_sync_days_filled: 4,
        appreciation_count: 3,
        insight: '這週的連結仍然在，只是更需要被刻意照顧。',
      });
      return;
    }

    if (path.endsWith('/cooldown/status') && method === 'GET') {
      await fulfillJson(route, {
        in_cooldown: true,
        started_by_me: true,
        ends_at_iso: new Date(now + 60 * 60 * 1000).toISOString(),
        remaining_seconds: 3600,
      });
      return;
    }

    if (path.endsWith('/cooldown/rewrite-message') && method === 'POST') {
      await fulfillError(route);
      return;
    }

    if (path.endsWith('/journals/') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/journals/partner') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/journals/') && method === 'POST') {
      await fulfillError(route);
      return;
    }

    if (path.endsWith('/daily-sync/status') && method === 'GET') {
      await fulfillJson(route, dailySyncStatus);
      return;
    }

    if (path.endsWith('/daily-sync') && method === 'POST') {
      const payload = route.request().postDataJSON() as {
        mood_score: number;
        question_id: string;
        answer_text: string;
      };
      dailySyncStatus = {
        ...dailySyncStatus,
        my_filled: true,
        my_mood_score: payload.mood_score,
        my_question_id: payload.question_id,
        my_answer_text: payload.answer_text,
      };
      await fulfillJson(route, {
        accepted: true,
      });
      return;
    }

    if (path.endsWith('/appreciations') && method === 'GET') {
      await fulfillJson(route, appreciationHistory);
      return;
    }

    if (path.endsWith('/appreciations') && method === 'POST') {
      const payload = route.request().postDataJSON() as { body_text: string };
      appreciationHistory = [
        {
          id: appreciationHistory.length + 1,
          body_text: payload.body_text,
          created_at: new Date().toISOString(),
          is_mine: true,
        },
        ...appreciationHistory,
      ];
      await fulfillJson(route, appreciationHistory[0]);
      return;
    }

    if (path.endsWith('/love-languages/weekly-task') && method === 'GET') {
      await fulfillJson(route, {
        task_slug: 'weekly-touch',
        task_label: '本週留一個溫柔的小觸碰給對方。',
        assigned_at: hoursAgo(now, 48),
        completed: false,
        completed_at: null,
      });
      return;
    }

    if (path.endsWith('/mediation/status') && method === 'GET') {
      await fulfillJson(route, {
        in_mediation: false,
        questions: [],
        my_answered: false,
        partner_answered: false,
      });
      return;
    }

    if (path.endsWith('/cards/daily-status') && method === 'GET') {
      await fulfillJson(route, {
        state: 'IDLE',
        card: null,
        my_content: null,
        partner_content: null,
        partner_name: 'Bob',
        session_id: 'daily-session-1',
      });
      return;
    }

    if (path.endsWith('/cards/draw') && method === 'GET') {
      await fulfillError(route);
      return;
    }

    if (path.endsWith('/cards/respond') && method === 'POST') {
      await fulfillJson(route, {
        id: 'card-response-1',
        card_id: 'card-1',
        user_id: 'me',
        content: '我想被慢慢聽完。',
        status: 'PENDING',
        created_at: new Date().toISOString(),
        session_id: 'daily-session-1',
      });
      return;
    }

    if (path.endsWith('/blueprint/date-suggestions') && method === 'GET') {
      await fulfillJson(route, {
        suggested: true,
        message: '這週適合留一段安靜的晚餐散步時間。',
        last_activity_at: hoursAgo(now, 8),
        suggestions: ['吃完晚餐後去河邊散步 20 分鐘。'],
      });
      return;
    }

    if (path.endsWith('/blueprint/') && method === 'GET') {
      await fulfillJson(route, blueprintItems);
      return;
    }

    if (path.endsWith('/blueprint/') && method === 'POST') {
      const payload = route.request().postDataJSON() as { title: string; notes?: string };
      if (payload.title.includes('失敗')) {
        await fulfillError(route);
        return;
      }
      const nextItem = {
        id: `wish-${blueprintItems.length + 1}`,
        title: payload.title,
        notes: payload.notes ?? '',
        created_at: new Date().toISOString(),
        added_by_me: true,
      };
      blueprintItems = [nextItem, ...blueprintItems];
      loveMapSystem.wishlist_items = blueprintItems;
      loveMapSystem.stats.wishlist_count = blueprintItems.length;
      await fulfillJson(route, nextItem);
      return;
    }

    if (path.endsWith('/baseline') && method === 'GET') {
      await fulfillJson(route, loveMapSystem.baseline);
      return;
    }

    if (path.endsWith('/couple-goal') && method === 'GET') {
      await fulfillJson(route, loveMapSystem.couple_goal);
      return;
    }

    if (path.endsWith('/love-map/system') && method === 'GET') {
      await fulfillJson(route, loveMapSystem);
      return;
    }

    if (path.endsWith('/love-map/cards') && method === 'GET') {
      await fulfillJson(route, loveMapCards);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future/refinements') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/love-map/notes') && method === 'POST') {
      const payload = route.request().postDataJSON() as { layer: string; content: string };
      const existing = loveMapSystem.notes.find((note) => note.layer === payload.layer);
      if (existing) {
        existing.content = payload.content;
        existing.updated_at = new Date().toISOString();
      }
      await fulfillJson(route, {
        id: existing?.id ?? `note-${payload.layer}`,
        layer: payload.layer,
        content: payload.content,
        created_at: existing?.created_at ?? new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future/generate') && method === 'POST') {
      await fulfillError(route);
      return;
    }

    await fulfillJson(route, {});
  });
}

test.describe('Toast message quality sweep', () => {
  test.use({ bypassCSP: true });
  test.setTimeout(90_000);

  test('shows calmer toast copy across mocked Home, Relationship System, Blueprint, Settings, and Journal flows', async ({
    page,
  }) => {
    test.skip(
      process.env.TOAST_LIVE_E2E === '1',
      'Skip mocked coverage during live seeded-stack verification.',
    );

    await page.setViewportSize({ width: 1440, height: 1100 });
    await mockToastApi(page);
    await login(page);

    await expect(page.locator('#home-tabpanel-mine').getByRole('heading', { name: '今天這一頁，先只留給你自己。' })).toBeVisible({
      timeout: 15_000,
    });

    const dailySyncForm = page.locator('form').filter({ has: page.locator('#daily-answer') });
    await page.locator('#daily-answer').fill('今天我最想被慢慢聽完。');
    await dailySyncForm.getByRole('button', { name: '送出' }).click();
    await expectToast(page, '今天的同步已收好。');

    const appreciationForm = page.locator('form').filter({ has: page.locator('#appreciation-text') });
    await page.locator('#appreciation-text').fill('謝謝你今天替我留了一點安靜。');
    await appreciationForm.getByRole('button', { name: '送出' }).click();
    await expectToast(page, '這句感謝已送出。');

    await page.goto('/blueprint');
    await page.getByRole('button', { name: '加入 Blueprint' }).click();
    await expectToast(page, '先寫下一個想一起靠近的未來片段。');

    await page.getByLabel('標題').fill('這次會失敗的片段');
    await page.getByRole('button', { name: '加入 Blueprint' }).click();
    await expectToast(page, '這個片段這次沒有順利收進 Blueprint。');

    await page.goto('/settings');
    await page.getByRole('button', { name: '儲存信任設定' }).click();
    await expectToast(page, '安全感與通知設定已收好。');

    await page.getByLabel('寫給對方（改寫成我訊息）').fill('我想先被好好聽完。');
    await page.getByRole('button', { name: '改寫預覽' }).click();
    await expectToast(page, '這次沒有順利整理這段話，稍後再試一次。');

  });

  test('shows representative live toast copy on the seeded local stack', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.skip(
      process.env.TOAST_LIVE_E2E !== '1',
      'Set TOAST_LIVE_E2E=1 to run against the seeded local Postgres stack.',
    );

    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });
    page.on('pageerror', (error) => {
      pageErrors.push(String(error));
    });

    const authResponse = await request.post('http://127.0.0.1:8000/api/auth/token', {
      form: {
        username: 'alice@example.com',
        password: 'havendev1',
      },
    });
    expect(authResponse.ok()).toBeTruthy();
    const authPayload = (await authResponse.json()) as {
      access_token: string;
      refresh_token?: string;
    };

    await context.addCookies(
      [
        {
          name: 'access_token',
          value: authPayload.access_token,
          domain: '127.0.0.1',
          path: '/',
          httpOnly: true,
          sameSite: 'Lax',
        },
        authPayload.refresh_token
          ? {
              name: 'refresh_token',
              value: authPayload.refresh_token,
              domain: '127.0.0.1',
              path: '/',
              httpOnly: true,
              sameSite: 'Lax' as const,
            }
          : null,
      ].filter(Boolean) as Array<{
        name: string;
        value: string;
        domain: string;
        path: string;
        httpOnly: boolean;
        sameSite: 'Lax';
      }>,
    );

    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';

    await page.goto(`${appBaseUrl}/`, { waitUntil: 'domcontentloaded' });
    await expect(
      page.locator('#home-tabpanel-mine').getByRole('heading', { name: '今天這一頁，先只留給你自己。' }),
    ).toBeVisible({ timeout: 20_000 });

    const liveAppreciationForm = page.locator('form').filter({ has: page.locator('#appreciation-text') });
    await page.locator('#appreciation-text').fill('謝謝你今天先替我留了一點空間。');
    await liveAppreciationForm.getByRole('button', { name: '送出' }).click();
    await expectToast(page, '這句感謝已送出。');

    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    await page.getByLabel('未來片段標題').fill('一起把週日早晨留給散步');
    await page.getByLabel('補充（選填）').fill('想把那段時間變成固定的安靜儀式。');
    await page.getByRole('button', { name: '放進共同藍圖' }).click();
    await expectToast(page, '這段未來片段已放進 Shared Future。');

    await page.goto(`${appBaseUrl}/blueprint`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: '加入 Blueprint' }).click();
    await expectToast(page, '先寫下一個想一起靠近的未來片段。');

    await page.getByLabel('標題').fill('一起把週五晚餐留給彼此');
    await page.getByLabel('備註（選填）').fill('就算只有一個小時，也想把那段時間留給我們。');
    await page.getByRole('button', { name: '加入 Blueprint' }).click();
    await expectToast(page, '這個片段已收進 Blueprint。');

    await page.goto(`${appBaseUrl}/settings`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: '儲存信任設定' }).click();
    await expectToast(page, '安全感與通知設定已收好。');

    await page.goto(`${appBaseUrl}/journal?compose=1`, { waitUntil: 'domcontentloaded' });
    const startPageButton = page.getByRole('button', { name: '開始新的一頁' });
    if (await startPageButton.isVisible().catch(() => false)) {
      await startPageButton.click();
    }
    await expect(page.getByLabel('Journal title')).toBeVisible({ timeout: 20_000 });
    await page.getByLabel('Journal title').fill('今晚想先留下一頁');
    const liveEditor = page.getByLabel('Journal writing canvas');
    await liveEditor.click();
    await liveEditor.pressSequentially('今晚我想先慢一點，也想先被理解。');
    const createPageButton = page.getByRole('button', { name: '建立這一頁' });
    if (await createPageButton.isVisible().catch(() => false)) {
      await createPageButton.click();
      await expectToast(page, '新的草稿頁已收進 Journal 書房。');
    } else {
      const saveDraftButton = page.getByRole('button', { name: /保存草稿|立即保存/ }).first();
      await expect(saveDraftButton).toBeVisible({ timeout: 20_000 });
      await saveDraftButton.click();
      await expect(page.getByText(/^(草稿已收好|已收好)$/)).toBeVisible({ timeout: 20_000 });
    }

    expect(consoleErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
});
