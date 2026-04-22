import { expect, test, type Page, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};

function apiSuccess(data: unknown, requestId = 'journal-sharing-e2e-req') {
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
  await page.getByPlaceholder('name@example.com').fill('journal-sharing@example.com');
  await page.locator('input[type="password"]').fill('password123');
  await page.getByRole('button', { name: '登入並回到 Haven' }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function mockJournalSharingApi(page: Page) {
  const now = Date.now();
  const updatePayloads: Array<Record<string, unknown>> = [];

  let ownerJournal = {
    id: 'journal-1',
    user_id: 'me',
    title: '沿用舊設定的一頁',
    content: '# 今晚\n\n這是作者自己的原文。',
    is_draft: false,
    visibility: 'PARTNER_ANALYSIS_ONLY',
    content_format: 'markdown',
    partner_translation_status: 'NOT_REQUESTED',
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
    emotional_needs: '需要被理解。',
    advice_for_user: '先慢一點。',
    action_for_user: '先把感受寫完。',
    action_for_partner: '先聽，再回應。',
    advice_for_partner: '先接住對方。',
    card_recommendation: null,
    safety_tier: 0,
    created_at: hoursAgo(now, 6),
    updated_at: hoursAgo(now, 1),
  };

  const translatedPartnerJournal = {
    id: 'partner-journal-translated',
    user_id: 'partner-1',
    title: '只給伴侶看的整理版',
    content: 'RAW SECRET LINE',
    visibility: 'PARTNER_TRANSLATED_ONLY',
    partner_translation_status: 'READY',
    partner_translated_content: 'TRANSLATED PARTNER MARKER',
    attachments: [
      {
        id: 'translated-attachment-1',
        file_name: 'translated-secret-photo.jpg',
        mime_type: 'image/jpeg',
        size_bytes: 1024,
        created_at: hoursAgo(now, 5),
        caption: null,
        url: 'https://example.com/translated-secret-photo.jpg',
      },
    ],
    mood_label: '低落',
    emotional_needs: '需要先被看見。',
    advice_for_partner: '先聽。',
    action_for_partner: '抱抱對方。',
    card_recommendation: 'SAFE_ZONE',
    safety_tier: 0,
    created_at: hoursAgo(now, 5),
    updated_at: hoursAgo(now, 5),
  };

  const pendingTranslatedPartnerJournal = {
    id: 'partner-journal-pending-translated',
    user_id: 'partner-1',
    title: '整理中但不應露出',
    content: 'PENDING RAW SECRET LINE',
    visibility: 'PARTNER_TRANSLATED_ONLY',
    partner_translation_status: 'PENDING',
    partner_translated_content: null,
    attachments: [
      {
        id: 'pending-translated-attachment-1',
        file_name: 'pending-secret-photo.jpg',
        mime_type: 'image/jpeg',
        size_bytes: 1024,
        created_at: hoursAgo(now, 4.5),
        caption: null,
        url: 'https://example.com/pending-secret-photo.jpg',
      },
    ],
    mood_label: '緊張',
    emotional_needs: 'PENDING NEEDS SHOULD NOT LEAK',
    advice_for_partner: 'PENDING ADVICE SHOULD NOT LEAK',
    action_for_partner: 'PENDING ACTION SHOULD NOT LEAK',
    card_recommendation: 'SAFE_ZONE',
    safety_tier: 0,
    created_at: hoursAgo(now, 4.5),
    updated_at: hoursAgo(now, 4.5),
  };

  const originalPartnerJournal = {
    id: 'partner-journal-original',
    user_id: 'partner-1',
    title: '原文共享頁',
    content: 'ORIGINAL PARTNER MARKER',
    visibility: 'PARTNER_ORIGINAL',
    partner_translation_status: 'NOT_REQUESTED',
    partner_translated_content: null,
    attachments: [
      {
        id: 'original-attachment-1',
        file_name: 'shared-photo.jpg',
        mime_type: 'image/jpeg',
        size_bytes: 2048,
        created_at: hoursAgo(now, 4),
        caption: null,
        url: 'https://example.com/shared-photo.jpg',
      },
    ],
    mood_label: '平靜',
    emotional_needs: null,
    advice_for_partner: null,
    action_for_partner: null,
    card_recommendation: null,
    safety_tier: 0,
    created_at: hoursAgo(now, 4),
    updated_at: hoursAgo(now, 4),
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
      await fulfillJson(route, { access_token: 'journal-sharing-token', token_type: 'bearer' });
      return;
    }

    if (path.endsWith('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'journal-sharing@example.com',
        full_name: 'Journal Sharing Reviewer',
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

    if (path.endsWith('/journals/partner') && method === 'GET') {
      await fulfillJson(route, [
        translatedPartnerJournal,
        pendingTranslatedPartnerJournal,
        originalPartnerJournal,
      ]);
      return;
    }

    if (path.endsWith('/journals/journal-1') && method === 'GET') {
      await fulfillJson(route, ownerJournal);
      return;
    }

    if (path.endsWith('/journals/') && method === 'GET') {
      await fulfillJson(route, [ownerJournal]);
      return;
    }

    if (path.endsWith('/journals/journal-1') && method === 'PATCH') {
      const payload = route.request().postDataJSON() as Record<string, unknown>;
      updatePayloads.push(payload);
      ownerJournal = {
        ...ownerJournal,
        title: typeof payload.title === 'string' ? payload.title : ownerJournal.title,
        content: typeof payload.content === 'string' ? payload.content : ownerJournal.content,
        is_draft:
          typeof payload.is_draft === 'boolean' ? payload.is_draft : ownerJournal.is_draft,
        visibility:
          typeof payload.visibility === 'string' ? payload.visibility : ownerJournal.visibility,
        updated_at: new Date().toISOString(),
      };
      await fulfillJson(route, ownerJournal);
      return;
    }

    await fulfillJson(route, {});
  });

  return {
    getUpdatePayloads: () => updatePayloads,
  };
}

test.describe('Journal sharing permissions', () => {
  test.use({ bypassCSP: true });
  test.setTimeout(90_000);

  test('keeps the author share selector to 3 modes and preserves legacy visibility until explicitly changed', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    const apiState = await mockJournalSharingApi(page);
    await login(page);

    await page.goto('/journal/journal-1');
    await expect(page.getByLabel('Journal title')).toHaveValue('沿用舊設定的一頁');
    await expect(page.getByText('伴侶只看分析（舊版）')).toBeVisible();

    await page.getByRole('button', { name: '分享設定' }).click();
    await expect(page.getByRole('button', { name: '私密保存' })).toBeVisible();
    await expect(page.getByRole('button', { name: '伴侶看原文' })).toBeVisible();
    await expect(page.getByRole('button', { name: '伴侶看整理後的版本' })).toBeVisible();
    await expect(
      page.getByText('保存後 Haven 才會準備伴侶可讀的版本；整理完成前，伴侶看不到原文、圖片或整理版。'),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: '伴侶只看分析' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '完全私密（不送 AI）' })).toHaveCount(0);
    await expect(
      page.getByText('這一頁沿用較早的「伴侶只看分析」設定。只要你不改分享設定，它就會維持只分享分析資訊。'),
    ).toBeVisible();
    const deliveryPanel = page.getByTestId('journal-partner-visibility-panel');
    await expect(deliveryPanel).toBeVisible();
    await expect(deliveryPanel).toContainText('伴侶可見狀態');
    await expect(deliveryPanel).toContainText('伴侶現在看得到什麼');
    await expect(deliveryPanel).toContainText('伴侶現在看到舊版分析資訊');
    await expect(deliveryPanel).toContainText('下一次保存會發生什麼');
    await expect(deliveryPanel).toContainText('保存後維持舊版分析分享');
    await expect(deliveryPanel).toContainText('交付生命週期');
    await expect(deliveryPanel).toContainText('不在交付中');
    await expect(deliveryPanel).toContainText('信任邊界');
    await expect(deliveryPanel).toContainText('未保存前，伴侶端仍依照上一次保存的設定');

    const editor = page.getByLabel('Journal writing canvas');
    await editor.click();
    await editor.pressSequentially('\n\n補上一句新的作者文字。');
    await page.getByRole('button', { name: '立即保存' }).click();

    await expect.poll(() => apiState.getUpdatePayloads().length).toBeGreaterThan(0);
    expect(apiState.getUpdatePayloads().at(-1)).not.toHaveProperty('visibility');

    await page.getByRole('button', { name: '私密保存' }).click();
    await expect(deliveryPanel).toContainText('保存後伴侶仍看不到');
    await page.getByRole('button', { name: '立即保存' }).click();

    await expect.poll(() => apiState.getUpdatePayloads().length).toBeGreaterThan(1);
    expect(apiState.getUpdatePayloads().at(-1)?.visibility).toBe('PRIVATE');
    await expect(
      page.getByRole('button', { name: /私密保存/ }),
    ).toHaveAttribute('aria-pressed', 'true');

    await page.getByRole('button', { name: '閱讀' }).click();
    await expect(page.getByText('TRANSLATED PARTNER MARKER')).toHaveCount(0);
  });

  test('explains original-share dirty state before save', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    const apiState = await mockJournalSharingApi(page);
    await login(page);

    await page.goto('/journal/journal-1');
    await page.getByRole('button', { name: '分享設定' }).click();
    await page.getByRole('button', { name: '伴侶看原文' }).click();
    await page.getByRole('button', { name: '立即保存' }).click();

    await expect.poll(() => apiState.getUpdatePayloads().length).toBeGreaterThan(0);
    expect(apiState.getUpdatePayloads().at(-1)?.visibility).toBe('PARTNER_ORIGINAL');

    const editor = page.getByLabel('Journal writing canvas');
    await editor.click();
    await editor.pressSequentially('\n\n這段還沒有保存給伴侶。');

    const deliveryPanel = page.getByTestId('journal-partner-visibility-panel');
    await expect(deliveryPanel).toBeVisible();
    await expect(deliveryPanel).toHaveAttribute('data-tone', 'dirty');
    await expect(deliveryPanel).toContainText('伴侶現在看到上一次保存的原文');
    await expect(deliveryPanel).toContainText('你剛改的內容還沒送出');
    await expect(deliveryPanel).toContainText('下一次保存後，伴侶會看到你保存下來的原文');
    const lifecycleCard = page.getByTestId('journal-delivery-lifecycle-card');
    await expect(lifecycleCard).toHaveAttribute('data-lifecycle-state', 'original');
    await expect(lifecycleCard).toContainText('原文分享等待保存');
    await expect(lifecycleCard).toContainText('原文分享不產生整理版');
  });

  test('shows original vs translated partner content with the stricter translated-only boundary', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await mockJournalSharingApi(page);
    await login(page);

    await page.goto('/');
    await page.getByRole('tab', { name: '伴侶來信' }).click();

    const translatedCard = page
      .getByRole('heading', { level: 3, name: '只給伴侶看的整理版' })
      .locator('xpath=ancestor::article[1]');
    await expect(translatedCard.getByText('TRANSLATED PARTNER MARKER')).toBeVisible();
    await expect(translatedCard.getByText('RAW SECRET LINE')).toHaveCount(0);
    await expect(translatedCard.getByText('translated-secret-photo.jpg')).toHaveCount(0);
    await expect(translatedCard.getByText('內心深處的渴望')).toHaveCount(0);
    await expect(translatedCard.getByText('理解視角')).toHaveCount(0);
    await expect(translatedCard.getByText('具體做法')).toHaveCount(0);
    await expect(translatedCard.locator('img')).toHaveCount(0);

    const pendingTranslatedCard = page
      .getByRole('heading', { level: 3, name: '整理中但不應露出' })
      .locator('xpath=ancestor::article[1]');
    await expect(pendingTranslatedCard.getByText('整理中', { exact: true })).toBeVisible();
    await expect(pendingTranslatedCard.getByText('伴侶目前看不到這封來信')).toBeVisible();
    await expect(pendingTranslatedCard.getByText('PENDING RAW SECRET LINE')).toHaveCount(0);
    await expect(pendingTranslatedCard.getByText('pending-secret-photo.jpg')).toHaveCount(0);
    await expect(pendingTranslatedCard.getByText('PENDING NEEDS SHOULD NOT LEAK')).toHaveCount(0);
    await expect(pendingTranslatedCard.getByText('PENDING ADVICE SHOULD NOT LEAK')).toHaveCount(0);
    await expect(pendingTranslatedCard.getByText('PENDING ACTION SHOULD NOT LEAK')).toHaveCount(0);
    await expect(pendingTranslatedCard.locator('img')).toHaveCount(0);

    const originalCard = page
      .getByRole('heading', { level: 3, name: '原文共享頁' })
      .locator('xpath=ancestor::article[1]');
    await expect(originalCard.getByText('ORIGINAL PARTNER MARKER')).toBeVisible();
    await expect(originalCard.getByText('shared-photo.jpg')).toBeVisible();
  });
});
