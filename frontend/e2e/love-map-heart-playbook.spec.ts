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
    'access-control-allow-origin': requestOrigin || 'http://localhost:3000',
  };
}

function apiSuccess(data: unknown, requestId = 'love-map-heart-playbook-e2e-req') {
  return {
    data,
    meta: { request_id: requestId },
    error: null,
  };
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: resolveMockApiHeaders(route),
    body: JSON.stringify(apiSuccess(data)),
  });
}

async function mockHeartPlaybookApi(page: Page) {
  await page.context().addCookies([
    { name: 'access_token', value: 'heart-playbook-mock-token', url: 'http://127.0.0.1:3000' },
    { name: 'access_token', value: 'heart-playbook-mock-token', url: 'http://localhost:8000' },
  ]);

  const now = Date.now();
  const heartProfilePayloads: Array<Record<string, unknown>> = [];
  let weeklyTaskCompletionCount = 0;

  const system = {
    has_partner: true,
    me: {
      id: 'me',
      full_name: 'Alice Chen',
      email: 'alice@example.com',
    },
    partner: {
      id: 'partner-1',
      partner_name: 'Bob',
    },
    baseline: {
      mine: {
        user_id: 'me',
        partner_id: 'partner-1',
        filled_at: new Date(now - 36 * 60 * 60 * 1000).toISOString(),
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
        filled_at: new Date(now - 30 * 60 * 60 * 1000).toISOString(),
        scores: {
          intimacy: 4,
          conflict: 3,
          trust: 4,
          communication: 4,
          commitment: 4,
        },
      },
    },
    couple_goal: {
      goal_slug: 'better_communication',
      chosen_at: new Date(now - 20 * 60 * 60 * 1000).toISOString(),
    },
    story: {
      available: true,
      moments: [],
      time_capsule: null,
    },
    notes: [],
    wishlist_items: [],
    stats: {
      filled_note_layers: 0,
      baseline_ready_mine: true,
      baseline_ready_partner: true,
      wishlist_count: 0,
      last_activity_at: new Date(now - 8 * 60 * 60 * 1000).toISOString(),
    },
    essentials: {
      my_care_preferences: {
        primary: 'words',
        secondary: 'time',
        updated_at: new Date(now - 10 * 60 * 60 * 1000).toISOString(),
      },
      my_care_profile: {
        support_me: '先陪我安靜一下。',
        avoid_when_stressed: '不要立刻追問。',
        small_delights: '回家時先抱我一下。',
        updated_at: new Date(now - 10 * 60 * 60 * 1000).toISOString(),
      },
      partner_care_preferences: {
        primary: 'acts',
        secondary: 'touch',
        updated_at: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      },
      partner_care_profile: {
        support_me: '先幫我把桌面收乾淨，我會比較能慢慢說。',
        avoid_when_stressed: '不要用玩笑帶過我真的在意的事。',
        small_delights: '如果你先幫我泡熱茶，我會覺得被照顧。',
        updated_at: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      },
      weekly_task: {
        task_slug: 'task_note',
        task_label: '寫一張小紙條謝謝他/她',
        assigned_at: new Date(now - 2 * 24 * 60 * 60 * 1000).toISOString(),
        completed: false,
        completed_at: null,
      },
    },
  };

  const cards = {
    safe: [],
    medium: [],
    deep: [],
  };

  const apiHandler = async (route: Route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: resolveMockApiHeaders(route) });
      return;
    }

    if (path.includes('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'alice@example.com',
        full_name: system.me.full_name,
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Bob',
        savings_score: 42,
      });
      return;
    }

    if (path.endsWith('/love-map/system') && method === 'GET') {
      await fulfillJson(route, system);
      return;
    }

    if (path.endsWith('/love-map/cards') && method === 'GET') {
      await fulfillJson(route, cards);
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

    if (path.endsWith('/love-map/essentials/heart-profile') && method === 'PUT') {
      const payload = route.request().postDataJSON() as {
        primary?: string | null;
        secondary?: string | null;
        support_me?: string | null;
        avoid_when_stressed?: string | null;
        small_delights?: string | null;
      };
      heartProfilePayloads.push(payload);
      system.essentials.my_care_preferences = {
        primary: payload.primary ?? null,
        secondary: payload.secondary ?? null,
        updated_at: new Date().toISOString(),
      };
      system.essentials.my_care_profile = {
        support_me: payload.support_me?.trim() || null,
        avoid_when_stressed: payload.avoid_when_stressed?.trim() || null,
        small_delights: payload.small_delights?.trim() || null,
        updated_at: system.essentials.my_care_preferences.updated_at,
      };
      system.stats.last_activity_at = system.essentials.my_care_preferences.updated_at;
      await fulfillJson(route, {
        care_preferences: system.essentials.my_care_preferences,
        care_profile: system.essentials.my_care_profile,
      });
      return;
    }

    if (path.endsWith('/love-languages/weekly-task/complete') && method === 'POST') {
      weeklyTaskCompletionCount += 1;
      system.essentials.weekly_task = {
        ...(system.essentials.weekly_task ?? {
          task_slug: 'task_note',
          task_label: '寫一張小紙條謝謝他/她',
          assigned_at: new Date(now).toISOString(),
        }),
        completed: true,
        completed_at: new Date().toISOString(),
      };
      await fulfillJson(route, system.essentials.weekly_task);
      return;
    }

    await fulfillJson(route, {});
  };

  await page.route('**/api/**', apiHandler);

  return {
    heartProfilePayloads,
    get weeklyTaskCompletionCount() {
      return weeklyTaskCompletionCount;
    },
  };
}

test.describe('Heart Care Playbook deepening', () => {
  test.use({ bypassCSP: true });

  test('saves the richer Heart Care Playbook in mocked mode', async ({ page }) => {
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Heart Care Playbook spec.',
    );

    const apiState = await mockHeartPlaybookApi(page);
    await page.goto('/love-map');

    await expect(page.getByTestId('relationship-heart-playbook-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-playbook-partner-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-playbook-partner-support')).toContainText(
      '先幫我把桌面收乾淨，我會比較能慢慢說。',
    );

    await page.locator('#love-map-care-primary').selectOption('acts');
    await page.locator('#love-map-care-secondary').selectOption('time');
    await page.getByLabel('當我過載時，先怎麼幫我').fill('先幫我把手機放遠一點。');
    await page.getByLabel('我壓力大時，先避免什麼').fill('不要立刻逼我做決定。');
    await page.getByLabel('哪些小動作最能讓我感到被照顧').fill('回家時先抱我一下。');
    await page.getByRole('button', { name: '保存 Heart Care Playbook' }).click();

    await expect.poll(() => apiState.heartProfilePayloads.length).toBe(1);
    expect(apiState.heartProfilePayloads[0]).toEqual({
      primary: 'acts',
      secondary: 'time',
      support_me: '先幫我把手機放遠一點。',
      avoid_when_stressed: '不要立刻逼我做決定。',
      small_delights: '回家時先抱我一下。',
    });

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('relationship-heart-playbook-card')).toBeVisible();
    await expect(page.getByLabel('當我過載時，先怎麼幫我')).toHaveValue('先幫我把手機放遠一點。');
    await expect(page.getByLabel('我壓力大時，先避免什麼')).toHaveValue('不要立刻逼我做決定。');
    await expect(page.getByLabel('哪些小動作最能讓我感到被照顧')).toHaveValue('回家時先抱我一下。');
    await expect(page.getByText('已留下 5/5 個 care cues').first()).toBeVisible();

    await page.getByRole('button', { name: '標記本週任務完成' }).click();
    await expect.poll(() => apiState.weeklyTaskCompletionCount).toBe(1);
    await expect(page.getByText('本週任務已完成')).toBeVisible();
  });

  test('edits and persists the Heart Care Playbook on the live local stack', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(90_000);
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E !== '1',
      'Set LOVE_MAP_LIVE_E2E=1 to run against the seeded local Postgres stack.',
    );

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
    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('relationship-heart-playbook-card')).toBeVisible();
    await expect(page.getByText('我的 Heart Care Playbook')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-playbook-partner-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-playbook-partner-card').locator('textarea')).toHaveCount(0);

    await page.locator('#love-map-care-primary').selectOption('acts');
    await page.locator('#love-map-care-secondary').selectOption('time');
    await page.getByLabel('當我過載時，先怎麼幫我').fill('先讓我喝口水，再陪我把事情排一排。');
    await page.getByLabel('我壓力大時，先避免什麼').fill('不要在我還很急的時候一直追問為什麼。');
    await page.getByLabel('哪些小動作最能讓我感到被照顧').fill('如果你先幫我留一杯熱飲，我會立刻放鬆一些。');
    await page.getByRole('button', { name: '保存 Heart Care Playbook' }).click();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.locator('#love-map-care-primary')).toHaveValue('acts');
    await expect(page.locator('#love-map-care-secondary')).toHaveValue('time');
    await expect(page.getByLabel('當我過載時，先怎麼幫我')).toHaveValue(
      '先讓我喝口水，再陪我把事情排一排。',
    );
    await expect(page.getByLabel('我壓力大時，先避免什麼')).toHaveValue(
      '不要在我還很急的時候一直追問為什麼。',
    );
    await expect(page.getByLabel('哪些小動作最能讓我感到被照顧')).toHaveValue(
      '如果你先幫我留一杯熱飲，我會立刻放鬆一些。',
    );
    await expect(page.getByText('已留下 5/5 個 care cues').first()).toBeVisible();

    const completeWeeklyTaskButton = page.getByRole('button', { name: '標記本週任務完成' });
    if ((await completeWeeklyTaskButton.count()) > 0) {
      await completeWeeklyTaskButton.click();
    }
    await expect(page.getByText('本週任務已完成')).toBeVisible();
  });
});
