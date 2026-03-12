/**
 * P0-I: Minimal CUJ smoke e2e.
 * Run with: npm run test:e2e (requires app at E2E_BASE_URL or http://localhost:3000)
 */

import { test, expect } from '@playwright/test';

const REFERRAL_INVITE_CODE_KEY = 'haven_referral_invite_code';
const REFERRAL_LANDING_EVENT_ID_KEY = 'haven_referral_landing_event_id';
const REFERRAL_SIGNUP_EVENT_ID_KEY = 'haven_referral_signup_event_id';

function apiSuccess(data: unknown, requestId = 'smoke-e2e-req') {
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
  requestId = 'smoke-e2e-req',
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

test.describe('Smoke / CUJ', () => {
  test('login syncs auth context and redirects to home', async ({ page }) => {
    await page.route('**/api/auth/token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          access_token: 'test-token',
          token_type: 'bearer',
        })),
      });
    });

    await page.route('**/api/users/me**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          id: '11111111-1111-1111-1111-111111111111',
          email: 'user@example.com',
          full_name: 'Smoke User',
          is_active: true,
          partner_id: null,
          partner_name: null,
          partner_nickname: null,
          savings_score: 0,
          created_at: '2026-01-01T00:00:00Z',
        })),
      });
    });

    await page.route('**/api/users/partner-status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          has_partner: false,
          latest_journal_at: null,
          current_score: 0,
          unread_notification_count: 0,
        })),
      });
    });

    await page.route('**/api/journals/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess([])),
      });
    });

    await page.route('**/api/**', async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (
        path === '/api/auth/token' ||
        path.startsWith('/api/users/me') ||
        path === '/api/users/referrals/signup' ||
        path === '/api/users/partner-status' ||
        path.startsWith('/api/journals/')
      ) {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({})),
      });
    });

    await page.goto('/login');
    await page.getByPlaceholder('user@example.com').fill('user@example.com');
    await page.locator('input[type="password"]').fill('password123');
    await page.getByRole('button', { name: '登入' }).click();

    await expect(page).toHaveURL(/\/$/);
    // ✅ 檢查 httpOnly Cookie 是否被設置（應該不在 localStorage 中）
    await expect
      .poll(async () => page.evaluate(() => localStorage.getItem('token')))
      .toBe(null);
    // 驗證頁面已加載（說明認證成功，因為受保護的頁面應該可以訪問）
    await expect(page.locator('main')).toBeVisible();
  });

  test('login keeps token cleared when profile load fails', async ({ page }) => {
    await page.route('**/api/auth/token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          access_token: 'temp-token-that-should-not-persist',
          token_type: 'bearer',
        })),
      });
    });

    await page.route('**/api/users/me**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify(apiError('internal_server_error', 'server-error', { detail: 'server-error' })),
      });
    });

    await page.goto('/login');
    await page.getByPlaceholder('user@example.com').fill('user@example.com');
    await page.locator('input[type="password"]').fill('password123');
    await page.getByRole('button', { name: '登入' }).click();

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText('登入成功，但讀取使用者資料失敗，請再試一次')).toBeVisible();
    // ✅ 驗證 localStorage 中沒有令牌（令牌由 httpOnly Cookie 提供）
    await expect
      .poll(async () => page.evaluate(() => localStorage.getItem('token')))
      .toBe(null);
  });

  test('register page loads and shows age + terms consent', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByRole('heading', { name: /加入 Haven|Join Haven|為你們建立一個更有呼吸感的親密空間/i })).toBeVisible();
    await expect(page.getByText(/18 歲/)).toBeVisible();
    await expect(page.getByRole('link', { name: /服務條款/ })).toBeVisible();
    const checkbox = page.getByRole('checkbox');
    await expect(checkbox).toBeVisible();
    await expect(checkbox).not.toBeChecked();
  });

  test('register requires consent before submit and sends consent payload', async ({ page }) => {
    let registerCalls = 0;
    let registerPayload: Record<string, unknown> | null = null;

    await page.route('**/api/users/', async (route) => {
      registerCalls += 1;
      registerPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          id: '22222222-2222-2222-2222-222222222222',
          email: 'new-user@example.com',
          full_name: 'New User',
          is_active: true,
          partner_id: null,
          partner_name: null,
          partner_nickname: null,
          savings_score: 0,
          created_at: '2026-01-01T00:00:00Z',
        })),
      });
    });

    await page.goto('/register');
    await page.getByPlaceholder('你想怎麼被稱呼？').fill('New User');
    await page.getByPlaceholder('name@example.com').fill('new-user@example.com');
    await page.getByPlaceholder('至少 8 個字元').fill('password123');

    const submitButton = page.getByRole('button', { name: '註冊帳號' });
    await expect(submitButton).toBeDisabled();
    expect(registerCalls).toBe(0);

    await page.getByRole('checkbox').check();
    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    await expect(page).toHaveURL(/\/login$/);
    expect(registerCalls).toBe(1);
    expect(registerPayload).toMatchObject({
      email: 'new-user@example.com',
      full_name: 'New User',
      age_confirmed: true,
      agreed_to_terms: true,
      terms_version: 'v1.0',
      privacy_version: 'v1.0',
    });
  });

  test('register with invite query tracks referral landing event', async ({ page }) => {
    let landingCalls = 0;
    let landingPayload: Record<string, unknown> | null = null;

    await page.route('**/api/users/referrals/landing-view', async (route) => {
      landingCalls += 1;
      landingPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          accepted: true,
          deduped: landingCalls > 1,
          event_type: 'LANDING_VIEW',
        })),
      });
    });

    await page.goto('/register?invite=pairb1');
    await expect(page.getByText(/已偵測邀請碼/i)).toBeVisible();
    await expect.poll(() => landingCalls).toBeGreaterThan(0);
    expect(landingPayload).toMatchObject({
      invite_code: 'PAIRB1',
      source: 'register_page',
      landing_path: '/register',
    });
    expect(String(landingPayload?.['event_id'] ?? '')).toContain('landing-');
  });

  test('login consumes referral context and tracks referral signup event', async ({ page }) => {
    let tokenCalls = 0;
    let signupCalls = 0;
    let signupPayload: Record<string, unknown> | null = null;
    let meCalls = 0;

    await page.addInitScript(
      ({
        inviteKey,
        landingKey,
        signupKey,
      }: {
        inviteKey: string;
        landingKey: string;
        signupKey: string;
      }) => {
        localStorage.setItem(inviteKey, 'PAIRB1');
        localStorage.setItem(landingKey, 'landing-test-event');
        localStorage.setItem(signupKey, 'signup-test-event');
      },
      {
        inviteKey: REFERRAL_INVITE_CODE_KEY,
        landingKey: REFERRAL_LANDING_EVENT_ID_KEY,
        signupKey: REFERRAL_SIGNUP_EVENT_ID_KEY,
      },
    );

    await page.route('**/api/auth/token', async (route) => {
      tokenCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          access_token: 'test-token',
          token_type: 'bearer',
        })),
      });
    });

    await page.route('**/api/users/me**', async (route) => {
      meCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          id: '33333333-3333-3333-3333-333333333333',
          email: 'invitee@example.com',
          full_name: 'Invitee',
          is_active: true,
          partner_id: null,
          partner_name: null,
          partner_nickname: null,
          savings_score: 0,
          created_at: '2026-01-01T00:00:00Z',
        })),
      });
    });

    await page.route('**/api/users/referrals/signup', async (route) => {
      signupCalls += 1;
      signupPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          accepted: true,
          deduped: false,
          event_type: 'SIGNUP',
        })),
      });
    });

    await page.route('**/api/users/partner-status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          has_partner: false,
          latest_journal_at: null,
          current_score: 0,
          unread_notification_count: 0,
        })),
      });
    });

    await page.route('**/api/journals/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess([])),
      });
    });

    await page.goto('/login');
    await expect.poll(() => meCalls).toBeGreaterThan(0);
    const emailInput = page.getByPlaceholder('user@example.com');
    const passwordInput = page.locator('input[type="password"]');
    const loginButton = page.getByRole('button', { name: '登入' });

    for (let attempt = 0; attempt < 3 && tokenCalls === 0; attempt += 1) {
      await emailInput.fill('invitee@example.com');
      await passwordInput.fill('password123');
      await loginButton.click();
      try {
        await expect.poll(() => tokenCalls, { timeout: 4000 }).toBeGreaterThan(0);
      } catch {
        // Retry when a pre-hydration native form submit causes a page reload.
      }
    }

    expect(tokenCalls).toBeGreaterThan(0);
    await expect.poll(() => signupCalls).toBe(1);
    await expect(page).toHaveURL(/\/settings$/, { timeout: 15000 });
    expect(signupPayload).toMatchObject({
      invite_code: 'PAIRB1',
      source: 'login_page',
      event_id: 'signup-test-event',
    });
    await expect
      .poll(() => page.evaluate((key) => localStorage.getItem(key), REFERRAL_INVITE_CODE_KEY))
      .toBe(null);
  });

  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /登入|Haven|Welcome Back/i })).toBeVisible();
  });

  test('legal terms page loads', async ({ page }) => {
    await page.goto('/legal/terms');
    await expect(page.getByRole('heading', { name: /服務條款/i })).toBeVisible();
  });

  test('legal privacy page loads', async ({ page }) => {
    await page.goto('/legal/privacy');
    await expect(page.getByRole('heading', { name: /隱私權政策/i })).toBeVisible();
  });

  test('decks library page loads', async ({ page }) => {
    await page.route('**/api/users/me**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          id: '44444444-4444-4444-4444-444444444444',
          email: 'decks@example.com',
          full_name: 'Deck User',
          is_active: true,
          partner_id: null,
          partner_name: null,
          partner_nickname: null,
          savings_score: 0,
          created_at: '2026-01-01T00:00:00Z',
        })),
      });
    });

    await page.goto('/decks');
    const decksHeading = page.getByRole('heading', { name: /牌組圖書館|今天想聊點什麼/i });
    const loginHeading = page.getByRole('heading', { name: /登入|Haven|Welcome Back/i });
    await expect
      .poll(async () => {
        if (await decksHeading.first().isVisible().catch(() => false)) return 'decks';
        if (await loginHeading.first().isVisible().catch(() => false)) return 'login';
        return 'none';
      })
      .toMatch(/decks|login/);
  });

  test('mediation repair flow v1 enters safety mode after risky step', async ({ page }) => {
    let started = false;
    let statusCalls = 0;
    let stepCompleteCalls = 0;
    const sessionId = 'repair-session-smoke';
    let safetyModeActive = false;
    const completed = false;
    let currentStep = 2;
    let myCompletedSteps = [1];
    const partnerCompletedSteps = [1];

    await page.route('**/api/users/feature-flags', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          has_partner_context: true,
          flags: {
            repair_flow_v1: true,
            weekly_review_v1: false,
          },
          kill_switches: {
            disable_repair_flow_v1: false,
          },
        })),
      });
    });

    await page.route('**/api/users/me**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          id: '55555555-5555-5555-5555-555555555555',
          email: 'repair@example.com',
          full_name: 'Repair User',
          is_active: true,
          partner_id: null,
          partner_name: null,
          partner_nickname: null,
          savings_score: 0,
          created_at: '2026-01-01T00:00:00Z',
        })),
      });
    });

    await page.route('**/api/users/partner-status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          has_partner: false,
          latest_journal_at: null,
          current_score: 0,
          unread_notification_count: 0,
        })),
      });
    });

    await page.route('**/api/mediation/repair/start', async (route) => {
      started = true;
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          accepted: true,
          deduped: false,
          session_id: sessionId,
        })),
      });
    });

    await page.route('**/api/mediation/repair/status**', async (route) => {
      statusCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          enabled: true,
          session_id: sessionId,
          in_repair_flow: true,
          safety_mode_active: safetyModeActive,
          completed,
          current_step: currentStep,
          my_completed_steps: myCompletedSteps,
          partner_completed_steps: partnerCompletedSteps,
        })),
      });
    });

    await page.route('**/api/mediation/repair/step-complete', async (route) => {
      stepCompleteCalls += 1;
      const payload = route.request().postDataJSON() as Record<string, unknown>;
      if (payload['step'] === 2) {
        myCompletedSteps = [1, 2];
        currentStep = 3;
        safetyModeActive = true;
      }

      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({
          accepted: true,
          deduped: false,
          step: Number(payload['step'] ?? 0),
          completed,
          safety_mode_active: safetyModeActive,
        })),
      });
    });

    await page.goto('/mediation');
    await expect(page.getByRole('heading', { name: /修復流程 v1/i })).toBeVisible();

    await page.getByRole('button', { name: '開始修復流程' }).click();
    await expect.poll(() => started).toBe(true);
    await expect.poll(() => statusCalls).toBeGreaterThan(0);

    await expect(page.getByText(/Step 2: 我感受到 \/ 我需要/i)).toBeVisible();
    await page.getByLabel('我感受到').fill('我現在感到很焦躁。');
    await page.getByLabel('我需要').fill('我需要先被聽完，再一起討論。');
    await page.getByRole('button', { name: '完成此步驟' }).click();

    await expect.poll(() => stepCompleteCalls).toBe(1);
    await expect(page.getByRole('heading', { name: '已進入安全模式' })).toBeVisible();
    await expect(page.getByRole('link', { name: /安心專線 1925/i })).toBeVisible();
    await expect(page.getByRole('button', { name: '關閉流程並返回' })).toBeVisible();
  });

  test('core daily loop emits stable core-loop event sequence', async ({ page }) => {
    const coreLoopEvents: string[] = [];
    let dailySyncFilled = false;
    let dailyCardDrawn = false;
    let dailyCardAnswered = false;
    const appreciationList: Array<{ id: number; body_text: string; created_at: string }> = [];

    await page.route('**/api/**', async (route) => {
      const request = route.request();
      const method = request.method().toUpperCase();
      const url = new URL(request.url());
      const path = url.pathname;

      if (path === '/api/auth/token' && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({ access_token: 'test-token', token_type: 'bearer' })),
        });
        return;
      }
      if (path.startsWith('/api/users/me') && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            id: '66666666-6666-6666-6666-666666666666',
            email: 'loop@example.com',
            full_name: 'Loop User',
            is_active: true,
            partner_id: '77777777-7777-7777-7777-777777777777',
            partner_name: 'Partner',
            partner_nickname: null,
            savings_score: 5,
            created_at: '2026-01-01T00:00:00Z',
          })),
        });
        return;
      }
      if (path === '/api/users/partner-status' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            has_partner: true,
            latest_journal_at: null,
            current_score: 5,
            unread_notification_count: 0,
          })),
        });
        return;
      }
      if (path === '/api/users/feature-flags' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            has_partner_context: true,
            flags: {
              repair_flow_v1: false,
              weekly_review_v1: false,
              websocket_realtime_enabled: true,
            },
            kill_switches: {},
          })),
        });
        return;
      }
      if (path === '/api/journals/' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess([])),
        });
        return;
      }
      if (path === '/api/daily-sync/status' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            today: '2026-03-05',
            my_filled: dailySyncFilled,
            partner_filled: false,
            unlocked: false,
            my_mood_score: dailySyncFilled ? 4 : null,
            my_question_id: dailySyncFilled ? 'q-1' : null,
            my_answer_text: dailySyncFilled ? '今天很平靜。' : null,
            partner_mood_score: null,
            partner_question_id: null,
            partner_answer_text: null,
            today_question_id: 'q-1',
            today_question_label: '今天最想被理解的是什麼？',
          })),
        });
        return;
      }
      if (path === '/api/daily-sync' && method === 'POST') {
        dailySyncFilled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({ status: 'ok', message: 'saved' })),
        });
        return;
      }
      if (path === '/api/cards/daily-status' && method === 'GET') {
        if (!dailyCardDrawn) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(apiSuccess({
              state: 'IDLE',
              card: null,
              session_id: null,
              partner_name: 'Partner',
            })),
          });
          return;
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            state: dailyCardAnswered ? 'COMPLETED' : 'IDLE',
            card: {
              id: 'card-1',
              title: '每日提問',
              question: '今天最感謝對方的哪一件事？',
              category: 'daily_vibe',
              depth_level: 1,
              tags: ['gratitude'],
            },
            my_content: dailyCardAnswered ? '謝謝你今天傾聽我。' : null,
            partner_content: dailyCardAnswered ? '謝謝你提醒我放鬆。' : null,
            partner_name: 'Partner',
            session_id: 'daily-session-1',
          })),
        });
        return;
      }
      if (path === '/api/cards/draw' && method === 'GET') {
        dailyCardDrawn = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            id: 'card-1',
            title: '每日提問',
            question: '今天最感謝對方的哪一件事？',
            category: 'daily_vibe',
            depth_level: 1,
            tags: ['gratitude'],
          })),
        });
        return;
      }
      if (path === '/api/cards/respond' && method === 'POST') {
        dailyCardAnswered = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            id: 'resp-1',
            card_id: 'card-1',
            user_id: '66666666-6666-6666-6666-666666666666',
            content: '謝謝你今天傾聽我。',
            status: 'REVEALED',
            created_at: '2026-03-05T00:00:00Z',
            session_id: 'daily-session-1',
          })),
        });
        return;
      }
      if (path === '/api/appreciations' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess(appreciationList)),
        });
        return;
      }
      if (path === '/api/appreciations' && method === 'POST') {
        appreciationList.unshift({
          id: appreciationList.length + 1,
          body_text: '謝謝你今天幫我分擔家務。',
          created_at: '2026-03-05T00:00:00Z',
        });
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess(appreciationList[0])),
        });
        return;
      }
      if (path === '/api/users/events/core-loop' && method === 'POST') {
        const payload = request.postDataJSON() as { event_name?: string };
        if (payload?.event_name) {
          coreLoopEvents.push(payload.event_name);
        }
        await route.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({
            accepted: true,
            deduped: false,
            event_name: payload?.event_name ?? 'unknown',
            loop_completed_today: payload?.event_name === 'appreciation_sent',
          })),
        });
        return;
      }
      if (path === '/api/users/events/cuj' && method === 'POST') {
        await route.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify(apiSuccess({ accepted: true, deduped: false })),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(apiSuccess({})),
      });
    });

    await page.goto('/login');
    await page.getByPlaceholder('user@example.com').fill('loop@example.com');
    await page.locator('input[type="password"]').fill('password123');
    await page.getByRole('button', { name: '登入' }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.getByLabel('今天情緒 1–5 分').selectOption('4');
    await page.getByLabel('你的回答').fill('今天最想被擁抱一下。');
    await page.getByRole('button', { name: /^送出$/ }).first().click();
    await expect.poll(() => coreLoopEvents.includes('daily_sync_submitted')).toBe(true);

    await page.getByRole('tab', { name: /每日共感|每日儀式/ }).click();
    await page.getByRole('button', { name: /抽取今日話題/i }).click();
    await expect.poll(() => coreLoopEvents.includes('daily_card_revealed')).toBe(true);

    await page.getByPlaceholder('在這裡寫下你的想法...').fill('謝謝你今天傾聽我。');
    await page.getByRole('button', { name: /送出並解鎖/i }).click();
    await expect.poll(() => coreLoopEvents.includes('card_answer_submitted')).toBe(true);

    await page.getByRole('tab', { name: '我的空間' }).click();
    await page.getByLabel('感恩內容').fill('謝謝你今天幫我分擔家務。');
    await page.getByRole('button', { name: /^送出$/ }).last().click();
    await expect.poll(() => coreLoopEvents.includes('appreciation_sent')).toBe(true);

    expect(new Set(coreLoopEvents)).toEqual(
      new Set(['daily_sync_submitted', 'daily_card_revealed', 'card_answer_submitted', 'appreciation_sent']),
    );
  });
});
