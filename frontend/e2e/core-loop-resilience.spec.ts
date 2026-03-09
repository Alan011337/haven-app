import { expect, test } from '@playwright/test';

function apiSuccess(data: unknown, requestId = 'core-loop-e2e-req') {
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
  requestId = 'core-loop-e2e-req',
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

test.describe('Core loop resilience', () => {
  test('protected home redirects to login on /users/me unauthorized', async ({ page }) => {
    await page.route('**/api/users/me**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify(apiError('unauthorized', 'not-authenticated')),
      });
    });
    await page.goto('/');
    await expect(page).toHaveURL(/\/login$/);
  });

  test('home renders with partner-status fallback when partner-status API fails', async ({ page }) => {
    await page.route('**/api/auth/token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({ access_token: 'token', token_type: 'bearer' })),
      });
    });
    await page.route('**/api/users/me**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          apiSuccess({
            id: '44444444-4444-4444-4444-444444444444',
            email: 'resilience@example.com',
            full_name: 'Resilience User',
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
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify(apiError('internal_server_error', 'partner-status-failed')),
      });
    });
    await page.route('**/api/journals/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess([])),
      });
    });

    await page.goto('/login');
    await page.getByPlaceholder('user@example.com').fill('resilience@example.com');
    await page.locator('input[type="password"]').fill('password123');
    await page.getByRole('button', { name: '登入' }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('main')).toBeVisible();
  });
});
