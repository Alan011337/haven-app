import { expect, test, type Page, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};

function apiSuccess(data: unknown, requestId = 'home-core-surface-e2e-req') {
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

async function mockHomeApi(page: Page) {
  const now = Date.now();
  const myJournal = {
    id: 'journal-1',
    user_id: 'me',
    title: '今天想先收住的一頁',
    content: '先把今天最想留下的那幾句收好。',
    is_draft: false,
    visibility: 'PARTNER_TRANSLATED_ONLY',
    content_format: 'markdown',
    partner_translation_status: 'READY',
    partner_translated_content: 'Hold on to today first.',
    attachments: [],
    mood_label: '平靜',
    emotional_needs: '我需要一點安靜整理自己。',
    advice_for_user: '慢慢寫。',
    action_for_user: '先寫第一句。',
    action_for_partner: '先接住。',
    advice_for_partner: '不要急著解決。',
    card_recommendation: null,
    safety_tier: 0,
    created_at: hoursAgo(now, 4),
    updated_at: hoursAgo(now, 2),
  };

  const partnerJournal = {
    ...myJournal,
    id: 'partner-journal-1',
    user_id: 'partner-1',
    title: '給你的來信',
    content: '今天想慢慢跟你說。',
    partner_translated_content: 'Today I want to tell you this slowly.',
    created_at: hoursAgo(now, 6),
    updated_at: hoursAgo(now, 5),
  };

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: MOCK_API_HEADERS });
      return;
    }

    if (path.endsWith('/auth/token') && method === 'POST') {
      await fulfillJson(route, { access_token: 'home-token', token_type: 'bearer' });
      return;
    }

    if (path.includes('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'home@example.com',
        full_name: 'Home Reviewer',
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Bob',
        partner_nickname: 'B',
        savings_score: 61,
        created_at: hoursAgo(now, 500),
      });
      return;
    }

    if (path.endsWith('/users/partner-status') && method === 'GET') {
      await fulfillJson(route, {
        has_partner: true,
        latest_journal_at: hoursAgo(now, 3),
        current_score: 61,
        unread_notification_count: 1,
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

    if (path.endsWith('/journals/') && method === 'GET') {
      await fulfillJson(route, [myJournal]);
      return;
    }

    if (path.endsWith('/journals/partner') && method === 'GET') {
      await fulfillJson(route, [partnerJournal]);
      return;
    }

    if (path.endsWith('/daily-sync/status') && method === 'GET') {
      await fulfillJson(route, {
        today: '2026-04-03',
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

    if (path.endsWith('/mediation/status') && method === 'GET') {
      await fulfillJson(route, {
        in_mediation: false,
        questions: [],
        my_answered: false,
        partner_answered: false,
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

    if (path.endsWith('/appreciations') && method === 'GET') {
      await fulfillJson(route, [
        {
          id: 1,
          body_text: '謝謝你今天記得幫我帶熱拿鐵。',
          created_at: hoursAgo(now, 12),
          is_mine: true,
        },
      ]);
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

    await fulfillJson(route, {});
  });
}

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('name@example.com').fill('home@example.com');
  await page.locator('input[type="password"]').fill('password123');
  const submitButton = page.getByRole('button', { name: '登入並回到 Haven' });
  await expect(submitButton).toBeEnabled();
  await submitButton.click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe('Home core surface continuity', () => {
  test.use({ bypassCSP: true });
  test.setTimeout(60_000);

  test('renders the new Home continuity cues in mocked mode', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await mockHomeApi(page);
    await login(page);

    const guide = page.getByTestId('home-core-surfaces-guide');
    await expect(guide.getByText('Home 先安靜整理今天，再把你送進更深的 Haven surfaces。')).toBeVisible();
    await expect(guide.getByRole('link', { name: 'Journal 書房' })).toHaveAttribute('href', '/journal');
    await expect(guide.getByRole('link', { name: 'Relationship System' })).toHaveAttribute('href', '/love-map');
    await expect(guide.getByRole('link', { name: 'Memory' })).toHaveAttribute('href', '/memory');
    await expect(guide.getByRole('link', { name: 'Blueprint' })).toHaveAttribute('href', '/blueprint');
    await expect(page.getByText('完整反思寫作')).toBeVisible();
    await expect(page.getByText('結構化關係理解')).toBeVisible();
    await expect(guide.getByText('Shared Archive')).toBeVisible();
    await expect(guide.getByText('完整 Shared Future')).toBeVisible();

    const minePanel = page.locator('#home-tabpanel-mine');
    await expect(
      minePanel.getByRole('heading', { name: '今天這一頁，先只留給你自己。' }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      minePanel.getByText(
        'Home 先收住今天最前面的幾句；如果你想把感受、圖片與分享邊界寫得更完整，下一步就進 Journal 書房。',
      ),
    ).toBeVisible();
    await expect(minePanel.getByText('反思寫作').first()).toBeVisible();
    await expect(minePanel.getByRole('link', { name: '進入 Journal 書房' })).toBeVisible();

    await expect(
      minePanel.getByRole('link', { name: '進入 Memory（完整 Shared Archive）' }),
    ).toBeVisible();

    await expect(
      page.getByRole('link', { name: '進入 Blueprint（完整 Shared Future）' }).first(),
    ).toBeVisible({ timeout: 8_000 });

    await page.getByRole('tab', { name: '每日儀式' }).click();
    const cardPanel = page.locator('#home-tabpanel-card');
    await expect(
      cardPanel.getByText('今天的 ritual 先留在這裡；如果某個節奏值得留下更久，就帶去 Relationship System。'),
    ).toBeVisible();
    await expect(cardPanel.getByRole('link', { name: '進入 Relationship System' })).toBeVisible();

    await expect(page.locator('a[href="/love-map"][aria-label="Relationship System"]')).toBeVisible();
    await expect(page.locator('a[href="/blueprint"][aria-label="Blueprint"]')).toBeVisible();
    await expect(page.locator('a[href="/memory"][aria-label="Memory"]')).toBeVisible();
  });

  test('connects Home to deeper surfaces on the live local stack', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.skip(
      process.env.HOME_CORE_LIVE_E2E !== '1',
      'Set HOME_CORE_LIVE_E2E=1 to run against the seeded local Postgres stack.',
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

    const guide = page.getByTestId('home-core-surfaces-guide');
    const minePanel = page.locator('#home-tabpanel-mine');
    await expect(guide.getByText('Home 先安靜整理今天，再把你送進更深的 Haven surfaces。')).toBeVisible();
    await expect(guide.getByRole('link', { name: 'Journal 書房' })).toBeVisible();
    await expect(guide.getByRole('link', { name: 'Relationship System' })).toBeVisible();
    await expect(guide.getByRole('link', { name: 'Memory' })).toBeVisible();
    await expect(guide.getByRole('link', { name: 'Blueprint' })).toBeVisible();
    await expect(guide.getByRole('link', { name: 'Relationship System' })).toHaveAttribute(
      'href',
      '/love-map',
    );
    await expect(guide.getByRole('link', { name: 'Blueprint' })).toHaveAttribute(
      'href',
      '/blueprint',
    );
    await expect(page.locator('a[href="/love-map"][aria-label="Relationship System"]')).toBeVisible();
    await expect(page.locator('a[href="/blueprint"][aria-label="Blueprint"]')).toBeVisible();
    await expect(page.locator('a[href="/memory"][aria-label="Memory"]')).toBeVisible();
    await expect(
      minePanel.getByRole('heading', { name: '今天這一頁，先只留給你自己。' }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(minePanel.getByRole('link', { name: '進入 Journal 書房' })).toBeVisible();
    await expect(minePanel.getByRole('link', { name: '進入 Journal 書房' })).toHaveAttribute(
      'href',
      '/journal?compose=1',
    );
    await expect(
      minePanel.getByRole('link', { name: '進入 Memory（完整 Shared Archive）' }),
    ).toBeVisible();

    await minePanel.getByRole('link', { name: '進入 Journal 書房' }).click();
    await expect(page).toHaveURL(/\/journal\?compose=1$/);

    await page.goto(`${appBaseUrl}/`, { waitUntil: 'domcontentloaded' });
    const memoryCta = page.locator('#home-tabpanel-mine').getByRole('link', {
      name: '進入 Memory（完整 Shared Archive）',
    });
    await expect(
      page.locator('#home-tabpanel-mine').getByRole('heading', { name: '今天這一頁，先只留給你自己。' }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(memoryCta).toHaveAttribute('href', '/memory');
    await page.goto(`${appBaseUrl}/memory`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/memory$/);

    await page.goto(`${appBaseUrl}/`, { waitUntil: 'domcontentloaded' });
    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/love-map$/);

    await page.goto(`${appBaseUrl}/`, { waitUntil: 'domcontentloaded' });
    await page.goto(`${appBaseUrl}/blueprint`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/blueprint$/);

    await page.goto(`${appBaseUrl}/?tab=card`, { waitUntil: 'domcontentloaded' });
    const liveCardPanel = page.locator('#home-tabpanel-card');
    await expect(
      liveCardPanel.getByText('今天的 ritual 先留在這裡；如果某個節奏值得留下更久，就帶去 Relationship System。'),
    ).toBeVisible();
    await expect(liveCardPanel.getByRole('link', { name: '進入 Relationship System' })).toHaveAttribute(
      'href',
      '/love-map',
    );
    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/love-map$/);
    expect(consoleErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
});
