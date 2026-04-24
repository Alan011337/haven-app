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

const DECK_CATEGORIES = [
  'DAILY_VIBE',
  'SOUL_DIVE',
  'SAFE_ZONE',
  'MEMORY_LANE',
  'GROWTH_QUEST',
  'AFTER_DARK',
  'CO_PILOT',
  'LOVE_BLUEPRINT',
] as const;

type MockDeckDepthApi = {
  requestedDeckDepths: number[];
};

function apiSuccess(data: unknown, requestId = 'deck-depth-e2e-req') {
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
    headers: MOCK_API_HEADERS,
    body: JSON.stringify(apiSuccess(data)),
  });
}

function buildCardSession(category: string, depth: 1 | 2 | 3) {
  return {
    id: `deck-depth-session-${category}-${depth}`,
    card_id: `deck-depth-card-${category}-${depth}`,
    category,
    status: 'PENDING',
    created_at: '2026-04-23T08:00:00Z',
    partner_name: 'Bob',
    card: {
      id: `deck-depth-card-${category}-${depth}`,
      title: `今晚的${depth === 1 ? '輕鬆' : depth === 2 ? '靠近' : '深入'}題目`,
      question:
        depth === 1
          ? '今天有哪件小事，讓你們可以輕鬆聊一下？'
          : depth === 2
            ? '最近哪一刻，你希望對方更懂你一點？'
            : '如果今晚願意深入內心，你最想坦白的是什麼？',
      category,
      depth_level: depth,
      tags: ['depth-system'],
    },
  };
}

async function mockDeckDepthApi(page: Page): Promise<MockDeckDepthApi> {
  const requestedDeckDepths: number[] = [];

  await page.route('**/api/auth/token', async (route) => {
    await fulfillJson(route, { access_token: 'deck-depth-token', token_type: 'bearer' });
  });

  await page.route('**/api/users/me**', async (route) => {
    await fulfillJson(route, {
      id: 'deck-depth-user',
      email: 'deck-depth@example.com',
      full_name: 'Deck Depth Reviewer',
      is_active: true,
      partner_id: 'deck-depth-partner',
      partner_name: 'Bob',
      partner_nickname: 'B',
      savings_score: 64,
      created_at: '2026-01-01T00:00:00Z',
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

    if (path.includes('/card-decks/stats') && method === 'GET') {
      await fulfillJson(
        route,
        DECK_CATEGORIES.map((category, index) => ({
          category,
          total_cards: 6,
          answered_cards: index % 3,
          completion_rate: Math.round(((index % 3) / 6) * 1000) / 10,
        })),
      );
      return;
    }

    if (path.includes('/card-decks/draw') && method === 'POST') {
      const preferredDepth = Number(url.searchParams.get('preferred_depth'));
      requestedDeckDepths.push(preferredDepth);
      const depth = preferredDepth === 1 || preferredDepth === 2 || preferredDepth === 3
        ? preferredDepth
        : 1;
      await fulfillJson(route, buildCardSession(url.searchParams.get('category') ?? 'DAILY_VIBE', depth));
      return;
    }

    if (path.includes('/users/notifications/mark-read') && method === 'POST') {
      await fulfillJson(route, { marked_read: 0 });
      return;
    }

    if (path.includes('/cards/') && path.includes('/conversation') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    await fulfillJson(route, {});
  });

  return { requestedDeckDepths };
}

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('name@example.com').fill('deck-depth@example.com');
  await page.locator('input[type="password"]').fill('password123');
  const submitButton = page.getByRole('button', { name: '登入並回到 Haven' });
  await expect(submitButton).toBeEnabled();
  await submitButton.click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function authenticateLive(context: BrowserContext, request: APIRequestContext) {
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

test.describe('Deck Depth System mocked flow', () => {
  test.use({ bypassCSP: true });
  test.setTimeout(60_000);
  test.skip(
    process.env.DECK_DEPTH_MOCK_E2E !== '1',
    'Set DECK_DEPTH_MOCK_E2E=1 to run the mocked Deck depth harness.',
  );

  test('filters Deck Library by human depth and preserves depth into Deck Room', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await mockDeckDepthApi(page);
    await login(page);

    await page.goto('/decks');
    await expect(page.getByTestId('deck-depth-filter-all')).toBeVisible();
    await expect(page.getByTestId('deck-depth-filter-1')).toHaveText('輕鬆聊');
    await expect(page.getByTestId('deck-depth-filter-2')).toHaveText('靠近一點');
    await expect(page.getByTestId('deck-depth-filter-3')).toHaveText('深入內心');

    await page.getByTestId('deck-depth-filter-2').click();
    await expect(page).toHaveURL(/\/decks\?depth=2$/);
    await expect(page.getByRole('heading', { name: /今晚想再靠近一點/ })).toBeVisible();
    await expect(page.locator('a[href*="/decks/SAFE_ZONE"][href*="depth=2"]').first()).toBeVisible();
    await expect(page.locator('a[href*="/decks/GROWTH_QUEST"][href*="depth=2"]').first()).toBeVisible();
    await expect(page.locator('a[href*="/decks/LOVE_BLUEPRINT"][href*="depth=2"]').first()).toBeVisible();
    await expect(page.locator('a[href*="/decks/DAILY_VIBE"][href*="depth=2"]')).toHaveCount(0);
  });

  test('uses the selected depth for the first Deck Room draw without numeric UI', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    const tracker = await mockDeckDepthApi(page);
    await login(page);

    await page.goto('/decks/SAFE_ZONE?depth=3');

    await expect.poll(() => tracker.requestedDeckDepths).toContain(3);
    await expect(page.getByText('本輪節奏 · 深入內心')).toBeVisible();
    await expect(page.getByText(/深度 3/)).toHaveCount(0);
    await expect(page.getByRole('heading', { name: /如果今晚願意深入內心/ })).toBeVisible();
  });
});

test.describe('Deck Depth System live flow', () => {
  test.setTimeout(90_000);
  test.skip(
    process.env.DECK_DEPTH_LIVE_E2E !== '1',
    'Set DECK_DEPTH_LIVE_E2E=1 to run against the seeded local Postgres stack.',
  );

  test('makes depth selectable in the live Deck Library and carries it into the first draw', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    await authenticateLive(context, request);
    await page.setViewportSize({ width: 1440, height: 1100 });

    const requestedDeckDepths: number[] = [];
    page.on('request', (apiRequest) => {
      const url = new URL(apiRequest.url());
      if (url.pathname.includes('/api/card-decks/draw')) {
        requestedDeckDepths.push(Number(url.searchParams.get('preferred_depth')));
      }
    });

    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';
    await page.goto(`${appBaseUrl}/decks`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('deck-depth-filter-2')).toBeVisible();
    await page.getByTestId('deck-depth-filter-2').click();
    await expect(page).toHaveURL(/\/decks\?depth=2$/);
    await expect(page.getByRole('heading', { name: /今晚想再靠近一點/ })).toBeVisible();

    await page.goto(`${appBaseUrl}/decks/SAFE_ZONE?depth=2`, { waitUntil: 'domcontentloaded' });
    await expect.poll(() => requestedDeckDepths).toContain(2);
    await expect(page.getByText(/本輪節奏/)).toBeVisible();
    await expect(page.getByText(/difficulty_level|depth_level|深度 2/i)).toHaveCount(0);
  });
});
