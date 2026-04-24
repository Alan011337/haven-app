import {
  expect,
  test,
  type APIRequestContext,
  type BrowserContext,
  type Page,
  type Route,
} from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};

function apiSuccess(data: unknown, requestId = 'home-daily-depth-e2e-req') {
  return {
    data,
    meta: { request_id: requestId },
    error: null,
  };
}

function hoursAgo(now: number, hours: number) {
  return new Date(now - hours * 60 * 60 * 1000).toISOString();
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: MOCK_API_HEADERS,
    body: JSON.stringify(apiSuccess(data)),
  });
}

type MockHomeDailyDepthApi = {
  requestedDepths: number[];
};

function buildDailyCard(depth: 1 | 2 | 3) {
  return {
    id: `daily-card-${depth}`,
    title: `今晚的第 ${depth} 種節奏`,
    description: '給今晚的一張題目。',
    question:
      depth === 1
        ? '今天有哪件小事，讓你覺得舒服一點？'
        : depth === 2
          ? '最近哪一刻，你最希望我更懂你一點？'
          : '如果今晚願意更坦白，你最想讓我真正知道的是什麼？',
    category: 'daily_vibe',
    difficulty_level: depth,
    depth_level: depth,
    tags: ['home-depth'],
  };
}

async function mockHomeApi(page: Page): Promise<MockHomeDailyDepthApi> {
  const now = Date.now();
  const requestedDepths: number[] = [];
  let dailyStatus = {
    state: 'IDLE',
    card: null as ReturnType<typeof buildDailyCard> | null,
    partner_name: 'Bob',
    session_id: null as string | null,
  };

  await page.route('**/api/auth/token', async (route) => {
    await fulfillJson(route, { access_token: 'home-daily-depth-token', token_type: 'bearer' });
  });

  await page.route('**/api/users/me**', async (route) => {
    await fulfillJson(route, {
      id: 'me',
      email: 'home-daily-depth@example.com',
      full_name: 'Home Daily Depth Reviewer',
      is_active: true,
      partner_id: 'partner-1',
      partner_name: 'Bob',
      partner_nickname: 'B',
      savings_score: 61,
      created_at: hoursAgo(now, 500),
    });
  });

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: MOCK_API_HEADERS });
      return;
    }

    if (
      (path.endsWith('/auth/token') && method === 'POST') ||
      (path.includes('/users/me') && method === 'GET')
    ) {
      await route.fallback();
      return;
    }

    if (path.includes('/users/partner-status') && method === 'GET') {
      await fulfillJson(route, {
        has_partner: true,
        latest_journal_at: hoursAgo(now, 3),
        current_score: 61,
        unread_notification_count: 0,
      });
      return;
    }

    if (path.includes('/users/gamification-summary') && method === 'GET') {
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

    if (path.includes('/users/onboarding-quest') && method === 'GET') {
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

    if (path.includes('/users/sync-nudges') && method === 'GET') {
      await fulfillJson(route, {
        enabled: false,
        has_partner_context: true,
        kill_switch_active: false,
        nudge_cooldown_hours: 18,
        nudges: [],
      });
      return;
    }

    if (path.includes('/users/first-delight') && method === 'GET') {
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

    if (path.includes('/journals/') && !path.includes('/journals/partner') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.includes('/journals/partner') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.includes('/daily-sync/status') && method === 'GET') {
      await fulfillJson(route, {
        today: '2026-04-05',
        my_filled: false,
        partner_filled: false,
        unlocked: false,
        my_mood_score: null,
        my_question_id: null,
        my_answer_text: null,
        partner_mood_score: null,
        partner_question_id: null,
        partner_answer_text: null,
        today_question_id: 'daily-question-1',
        today_question_label: '今天你最想被怎麼對待？',
      });
      return;
    }

    if (path.includes('/mediation/status') && method === 'GET') {
      await fulfillJson(route, {
        in_mediation: false,
        questions: [],
        my_answered: false,
        partner_answered: false,
      });
      return;
    }

    if (path.includes('/blueprint/date-suggestions') && method === 'GET') {
      await fulfillJson(route, {
        suggested: true,
        message: '今晚適合留一個安靜的問題給彼此。',
        last_activity_at: hoursAgo(now, 8),
        suggestions: ['散步 15 分鐘，再慢慢聊。'],
      });
      return;
    }

    if (path.includes('/appreciations') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.includes('/love-languages/weekly-task') && method === 'GET') {
      await fulfillJson(route, {
        task_slug: 'weekly-touch',
        task_label: '本週留一個溫柔的小觸碰給對方。',
        assigned_at: hoursAgo(now, 48),
        completed: false,
        completed_at: null,
      });
      return;
    }

    if (path.includes('/cards/daily-status') && method === 'GET') {
      await fulfillJson(route, dailyStatus);
      return;
    }

    if (path.includes('/cards/draw') && method === 'GET') {
      const preferredDepth = Number(url.searchParams.get('preferred_depth'));
      requestedDepths.push(preferredDepth);
      const depth = preferredDepth as 1 | 2 | 3;
      const card = buildDailyCard(depth);
      dailyStatus = {
        state: 'IDLE',
        card,
        partner_name: 'Bob',
        session_id: `session-${depth}`,
      };
      await fulfillJson(route, card);
      return;
    }

    await fulfillJson(route, {});
  });

  return { requestedDepths };
}

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('name@example.com').fill('home-daily-depth@example.com');
  await page.locator('input[type="password"]').fill('password123');
  const submitButton = page.getByRole('button', { name: '登入並回到 Haven' });
  await expect(submitButton).toBeEnabled();
  await submitButton.click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
  await page.goto('/?tab=card');
  await expect(page).toHaveURL(/\/\?tab=card$/, { timeout: 20_000 });
}

async function authenticateLive(
  context: BrowserContext,
  request: APIRequestContext,
) {
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
        sameSite: 'Lax' as const,
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
}

test.describe('Home daily empathy depth chooser', () => {
  test.use({ bypassCSP: true });
  test.setTimeout(60_000);
  test.skip(
    process.env.HOME_DAILY_DEPTH_MOCK_E2E !== '1',
    'Set HOME_DAILY_DEPTH_MOCK_E2E=1 to run the mocked Home depth chooser harness.',
  );

  test('requires a humane depth choice before draw and updates the chooser copy', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await mockHomeApi(page);
    await login(page);

    const chooser = page.getByTestId('home-daily-depth-chooser');
    const drawCta = page.getByTestId('home-daily-depth-draw-cta');

    await expect(page.getByRole('heading', { name: '今晚想怎麼聊？' })).toBeVisible();
    await expect(chooser).toBeVisible();
    await expect(drawCta).toBeDisabled();
    await expect(page.getByText('輕鬆聊')).toBeVisible();
    await expect(page.getByText('靠近一點')).toBeVisible();
    await expect(page.getByText('深入內心')).toBeVisible();
    await expect(page.getByText('先選一個今晚想聊的節奏，再抽一張剛剛好的題目。')).toBeVisible();

    await page.getByTestId('home-daily-depth-option-1').click();
    await expect(drawCta).toHaveText('抽一張適合「輕鬆聊」的題目');
    await expect(
      chooser.locator('p').filter({ hasText: '先用比較不費力的問題，慢慢進到今晚。' }),
    ).toBeVisible();

    await page.getByTestId('home-daily-depth-option-2').click();
    await expect(drawCta).toHaveText('抽一張適合「靠近一點」的題目');
    await expect(
      chooser.locator('p').filter({ hasText: '聊近況，也聊到彼此真正想被理解的地方。' }),
    ).toBeVisible();

    await page.getByTestId('home-daily-depth-option-3').click();
    await expect(drawCta).toHaveText('抽一張適合「深入內心」的題目');
    await expect(
      chooser.locator('p').filter({ hasText: '留給今晚願意更坦白、更靠近內在的時刻。' }),
    ).toBeVisible();
  });

  test('sends preferred_depth from Home and keeps post-draw language humane', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    const tracker = await mockHomeApi(page);
    await login(page);

    await page.getByTestId('home-daily-depth-option-2').click();
    await page.getByTestId('home-daily-depth-draw-cta').click();

    await expect.poll(() => tracker.requestedDepths).toContain(2);
    await expect(page.getByRole('heading', { name: '今晚的第 2 種節奏' })).toBeVisible();
    await expect(page.getByText(/daily vibe/i)).toHaveCount(0);
    await expect(page.getByText(/深度 2/)).toHaveCount(0);
    await expect(page.getByText('靠近一點')).toBeVisible();
  });
});

test.describe('Home daily empathy depth chooser live flow', () => {
  test.setTimeout(90_000);
  test.skip(
    process.env.HOME_DAILY_DEPTH_LIVE_E2E !== '1',
    'Set HOME_DAILY_DEPTH_LIVE_E2E=1 to run against the seeded local Postgres stack.',
  );

  test('lets Alice pick a live Daily Empathy depth before drawing', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    await authenticateLive(context, request);
    await page.setViewportSize({ width: 1440, height: 1100 });

    const requestedDepths: number[] = [];
    page.on('request', (apiRequest) => {
      const url = new URL(apiRequest.url());
      if (url.pathname.includes('/api/cards/draw')) {
        requestedDepths.push(Number(url.searchParams.get('preferred_depth')));
      }
    });

    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';
    await page.goto(`${appBaseUrl}/?tab=card`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('home-daily-depth-chooser')).toBeVisible();
    await page.getByTestId('home-daily-depth-option-3').click();
    await expect(page.getByTestId('home-daily-depth-draw-cta')).toHaveText(
      '抽一張適合「深入內心」的題目',
    );
    await page.getByTestId('home-daily-depth-draw-cta').click();

    await expect.poll(() => requestedDepths).toContain(3);
    await expect(page.getByText('深入內心')).toBeVisible();
    await expect(page.getByText(/difficulty_level|depth_level|深度 3/i)).toHaveCount(0);
  });
});
