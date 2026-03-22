import { expect, test } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};

function apiSuccess(data: unknown, requestId = 'auth-recovery-e2e-req') {
  return {
    data,
    meta: { request_id: requestId },
    error: null,
  };
}

function apiError(
  code: string,
  message: string,
  details: unknown = null,
  requestId = 'auth-recovery-e2e-req',
) {
  return {
    data: null,
    meta: { request_id: requestId },
    error: {
      code,
      message,
      details,
    },
  };
}

test.describe('Auth + Journal recovery', () => {
  test('login succeeds once even when bootstrap me 401s before cookie-backed hydration', async ({
    page,
  }) => {
    let meCalls = 0;

    await page.route('**/api/auth/token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: MOCK_API_HEADERS,
        body: JSON.stringify(
          apiSuccess({
            access_token: 'test-token',
            token_type: 'bearer',
          }),
        ),
      });
    });

    await page.route('**/api/users/me**', async (route) => {
      meCalls += 1;
      if (meCalls === 1) {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          headers: MOCK_API_HEADERS,
          body: JSON.stringify(apiError('unauthorized', 'not authenticated')),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: MOCK_API_HEADERS,
        body: JSON.stringify(
          apiSuccess({
            id: '11111111-1111-1111-1111-111111111111',
            email: 'user@example.com',
            full_name: 'Recovery User',
            is_active: true,
            partner_id: null,
            partner_name: null,
            partner_nickname: null,
            savings_score: 0,
            created_at: '2026-01-01T00:00:00Z',
          }),
        ),
      });
    });

    await page.route('**/api/users/partner-status', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        headers: MOCK_API_HEADERS,
        body: JSON.stringify(apiError('unauthorized', 'widget fallback only')),
      });
    });

    await page.route('**/api/journals/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: MOCK_API_HEADERS,
        body: JSON.stringify(apiSuccess([])),
      });
    });

    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (
        path === '/api/auth/token' ||
        path.startsWith('/api/users/me') ||
        path === '/api/users/partner-status' ||
        path.startsWith('/api/journals/')
      ) {
        await route.fallback();
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: MOCK_API_HEADERS,
        body: JSON.stringify(apiSuccess({})),
      });
    });

    await page.goto('/login');
    await expect.poll(() => meCalls).toBeGreaterThan(0);
    await page.getByPlaceholder('name@example.com').fill('user@example.com');
    await page.locator('input[type="password"]').fill('password123');
    const submitButton = page.getByRole('button', { name: '登入並回到 Haven' });
    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
    await expect.poll(() => meCalls).toBeGreaterThan(1);
    await expect(page.locator('main')).toBeVisible();
    await page.waitForTimeout(600);
    await expect(page).toHaveURL(/\/$/);
  });
});
