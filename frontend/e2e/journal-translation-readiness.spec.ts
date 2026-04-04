import { expect, test, type Page, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://localhost:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};

function apiSuccess(data: unknown, requestId = 'journal-translation-readiness-e2e-req') {
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

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('name@example.com').fill('journal-translation@example.com');
  await page.locator('input[type="password"]').fill('password123');
  await page.getByRole('button', { name: '登入並回到 Haven' }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function mockJournalTranslationReadinessApi(page: Page) {
  const now = Date.now();
  const journal = {
    id: 'journal-1',
    user_id: 'me',
    title: '只給伴侶看的整理版',
    content: '# 今晚\n\nRAW SECRET LINE',
    is_draft: false,
    visibility: 'PARTNER_TRANSLATED_ONLY',
    content_format: 'markdown',
    partner_translation_status: 'NOT_REQUESTED',
    partner_translated_content: null as string | null,
    attachments: [] as Array<{
      id: string;
      file_name: string;
      mime_type: string;
      size_bytes: number;
      created_at: string;
      caption: string | null;
      url: string | null;
    }>,
    mood_label: '疲憊',
    emotional_needs: '想先被理解。',
    advice_for_user: '慢一點。',
    action_for_user: '先寫完。',
    action_for_partner: '先聽。',
    advice_for_partner: '先接住。',
    card_recommendation: null,
    safety_tier: 0,
    created_at: hoursAgo(now, 6),
    updated_at: hoursAgo(now, 1),
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
      await fulfillJson(route, { access_token: 'journal-translation-token', token_type: 'bearer' });
      return;
    }

    if (path.endsWith('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'journal-translation@example.com',
        full_name: 'Journal Translation Reviewer',
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Partner',
        partner_nickname: 'P',
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
      await fulfillJson(route, {
        privacy_scope_accepted: true,
        notification_frequency: 'normal',
        ai_intensity: 'gentle',
        updated_at: hoursAgo(now, 24),
      });
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
        in_cooldown: false,
        started_by_me: false,
        ends_at_iso: null,
        remaining_seconds: 0,
      });
      return;
    }

    if (path.endsWith('/daily-sync/status') && method === 'GET') {
      await fulfillJson(route, {
        today: '2026-04-04',
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

    if (path.endsWith('/appreciations') && method === 'GET') {
      await fulfillJson(route, []);
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
        partner_name: 'Partner',
        session_id: 'daily-session-1',
      });
      return;
    }

    if (path.endsWith('/blueprint/date-suggestions') && method === 'GET') {
      await fulfillJson(route, {
        suggested: false,
        message: '',
        last_activity_at: hoursAgo(now, 8),
        suggestions: [],
      });
      return;
    }

    if (path.endsWith('/journals/') && method === 'GET') {
      await fulfillJson(route, [journal]);
      return;
    }

    if (path.endsWith('/journals/partner') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/journals/journal-1') && method === 'GET') {
      await fulfillJson(route, journal);
      return;
    }

    if (path.endsWith('/journals/journal-1') && method === 'PATCH') {
      const payload = route.request().postDataJSON() as Record<string, unknown>;
      if (typeof payload.visibility === 'string') {
        journal.visibility = payload.visibility;
      }
      if (typeof payload.content === 'string') {
        journal.content = payload.content;
      }
      if (typeof payload.title === 'string') {
        journal.title = payload.title;
      }
      if (typeof payload.is_draft === 'boolean') {
        journal.is_draft = payload.is_draft;
      }
      journal.updated_at = new Date().toISOString();
      await fulfillJson(route, journal);
      return;
    }

    await fulfillJson(route, {});
  });

  return {
    setStatus(nextStatus: 'FAILED' | 'NOT_REQUESTED' | 'PENDING' | 'READY') {
      journal.partner_translation_status = nextStatus;
      journal.partner_translated_content =
        nextStatus === 'READY' ? 'TRANSLATED PARTNER MARKER' : null;
      journal.updated_at = new Date().toISOString();
    },
  };
}

test.describe('Journal translated-only readiness', () => {
  test.use({ bypassCSP: true, viewport: { width: 1440, height: 1200 } });

  test('author sees translated-only readiness states without translated content leakage', async ({ page }) => {
    const api = await mockJournalTranslationReadinessApi(page);
    await login(page);

    const expectations = [
      {
        label: '尚未準備好',
        message: '這一頁設成整理後版本後，保存才會開始準備伴侶可讀的版本。',
        shortLabel: '尚未準備',
        state: 'not-ready',
        status: 'NOT_REQUESTED' as const,
      },
      {
        label: '正在整理給伴侶看的版本',
        message: 'Haven 正在準備伴侶可讀的版本。整理完成前，伴侶還看不到這段內容。',
        shortLabel: '整理中',
        state: 'pending',
        status: 'PENDING' as const,
      },
      {
        label: '已整理好給伴侶閱讀',
        message: '伴侶現在看到的是 Haven 整理後的版本，不是你的原文或圖片。',
        shortLabel: '伴侶可讀',
        state: 'ready',
        status: 'READY' as const,
      },
      {
        label: '暫時沒整理好',
        message: 'Haven 這次還沒整理好伴侶可讀的版本。伴侶目前看不到這段內容；你下次保存這一頁時，Haven 會再試一次。',
        shortLabel: '暫未完成',
        state: 'failed',
        status: 'FAILED' as const,
      },
    ];

    for (const expectation of expectations) {
      api.setStatus(expectation.status);
      await page.goto('/journal/journal-1');
      await page.getByRole('button', { name: '分享設定' }).click();

      const statusCard = page.getByTestId('journal-translation-status-card');
      await expect(statusCard).toBeVisible();
      await expect(statusCard).toContainText('伴侶閱讀狀態');
      await expect(statusCard).toContainText(expectation.label);
      await expect(statusCard).toContainText(expectation.message);

      await expect(
        page.locator(`[data-testid="journal-translation-status-chip"][data-state="${expectation.state}"]`).first(),
      ).toContainText(expectation.shortLabel);

      await expect(page.getByText('TRANSLATED PARTNER MARKER')).toHaveCount(0);
    }
  });

  test('library cards show the compact translated-only readiness chip', async ({ page }) => {
    const api = await mockJournalTranslationReadinessApi(page);
    api.setStatus('READY');
    await login(page);
    await page.goto('/journal/journal-1');

    await expect(
      page.locator('[data-testid="journal-translation-status-chip"][data-state="ready"]').first(),
    ).toContainText('伴侶可讀');

    await page.goto('/journal');

    const libraryCard = page.getByRole('link', { name: /只給伴侶看的整理版/ });
    await expect(libraryCard).toContainText('伴侶看整理後的版本');
    await expect(
      libraryCard.locator('[data-testid="journal-translation-status-chip"][data-state="ready"]'),
    ).toContainText('伴侶可讀');
  });
});
