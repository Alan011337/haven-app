import { expect, test } from '@playwright/test';

test.describe('Non-core surface naming sweep', () => {
  test.use({ bypassCSP: true });
  test.setTimeout(90_000);

  test('shows cleaned non-core surface naming on the live local stack', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.skip(
      process.env.NON_CORE_NAMING_LIVE_E2E !== '1',
      'Set NON_CORE_NAMING_LIVE_E2E=1 to run against the seeded local Postgres stack.',
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

    await page.goto(`${appBaseUrl}/settings`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('Settings', { exact: true }).first()).toBeVisible();
    await expect(page.getByRole('heading', { level: 3, name: 'Relationship System 現在是這塊知識的主場' })).toBeVisible();
    await expect(page.getByRole('link', { name: '前往 Relationship System' })).toHaveAttribute(
      'href',
      '/love-map',
    );
    await expect(page.getByText('Love Map', { exact: true })).toHaveCount(0);

    await page.goto(`${appBaseUrl}/analysis`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('Analysis', { exact: true }).first()).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: /把最近的互動，翻成更深的理解。|先把自己的情緒節奏，讀得更清楚。/,
      }),
    ).toBeVisible();

    await page.goto(`${appBaseUrl}/mediation`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('Mediation', { exact: true }).first()).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: '把最難說清楚的時刻，放進一個足夠溫和的房間。',
      }),
    ).toBeVisible();

    await page.goto(`${appBaseUrl}/notifications`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('Notifications', { exact: true }).first()).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: '每一則提醒，都應該讓你更靠近真正重要的事。',
      }),
    ).toBeVisible();

    expect(consoleErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
});
