import { expect, test, type Page, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};

function apiSuccess(data: unknown, requestId = 'journal-v3-e2e-req') {
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

type MockJournal = {
  action_for_partner: string;
  action_for_user: string;
  advice_for_partner: string;
  advice_for_user: string;
  attachments: Array<{
    id: string;
    file_name: string;
    mime_type: string;
    size_bytes: number;
    created_at: string;
    caption: string | null;
    url: string | null;
  }>;
  card_recommendation: null;
  content: string;
  content_format: string;
  created_at: string;
  emotional_needs: string;
  id: string;
  is_draft: boolean;
  mood_label: string;
  partner_translated_content: string;
  partner_translation_status: string;
  safety_tier: number;
  title: string;
  updated_at: string;
  user_id: string;
  visibility: string;
};

async function mockJournalApi(
  page: Page,
  options?: {
    journalOverrides?: Partial<MockJournal>;
    withExistingJournal?: boolean;
  },
) {
  const now = Date.now();
  const createPayloads: Array<Record<string, unknown>> = [];
  const updatePayloads: Array<Record<string, unknown>> = [];
  let attachmentUploadCount = 0;
  let hasJournal = Boolean(options?.withExistingJournal);
  const baseJournal: MockJournal = {
    id: 'journal-1',
    user_id: 'me',
    title: '夜裡想留下的一頁',
    content: '# 今晚\n\n我想先慢一點，也想先被理解。\n\n> 先不要急著給答案。',
    is_draft: false,
    visibility: 'PARTNER_TRANSLATED_ONLY',
    content_format: 'markdown',
    partner_translation_status: 'READY',
    partner_translated_content: '# Tonight\n\nPlease hear me first.',
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
    emotional_needs: '我需要先被理解。',
    advice_for_user: '先停一下。',
    action_for_user: '只先說感受。',
    action_for_partner: '慢一點回應。',
    advice_for_partner: '先接住，不急著解決。',
    card_recommendation: null,
    safety_tier: 0,
    created_at: hoursAgo(now, 4),
    updated_at: hoursAgo(now, 1),
  };
  let journal: MockJournal = {
    ...baseJournal,
    ...options?.journalOverrides,
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
      await fulfillJson(route, { access_token: 'journal-token', token_type: 'bearer' });
      return;
    }

    if (path.includes('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'journal@example.com',
        full_name: 'Journal Reviewer',
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

    if (method === 'GET' && path.endsWith('/journals/')) {
      await fulfillJson(route, hasJournal ? [journal] : []);
      return;
    }

    if (method === 'GET' && path.endsWith('/journals/partner')) {
      await fulfillJson(route, hasJournal && !journal.is_draft ? [journal] : []);
      return;
    }

    if (method === 'GET' && path.endsWith('/journals/journal-1')) {
      await fulfillJson(route, journal);
      return;
    }

    if (method === 'POST' && path.endsWith('/journals/')) {
      const payload = route.request().postDataJSON() as Record<string, unknown>;
      createPayloads.push(payload);
      hasJournal = true;
      journal = {
        ...journal,
        title: typeof payload.title === 'string' ? payload.title : journal.title,
        content: String(payload.content ?? ''),
        is_draft: Boolean(payload.is_draft),
        visibility:
          typeof payload.visibility === 'string' ? payload.visibility : journal.visibility,
        content_format: String(payload.content_format ?? 'markdown'),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      await fulfillJson(route, { ...journal, new_savings_score: 61, score_gained: 3 });
      return;
    }

    if (method === 'PATCH' && path.endsWith('/journals/journal-1')) {
      const payload = route.request().postDataJSON() as Record<string, unknown>;
      updatePayloads.push(payload);
      journal = {
        ...journal,
        title: typeof payload.title === 'string' ? payload.title : journal.title,
        content: typeof payload.content === 'string' ? payload.content : journal.content,
        is_draft:
          typeof payload.is_draft === 'boolean' ? payload.is_draft : journal.is_draft,
        visibility:
          typeof payload.visibility === 'string' ? payload.visibility : journal.visibility,
        updated_at: new Date().toISOString(),
      };
      await fulfillJson(route, journal);
      return;
    }

    if (method === 'POST' && path.endsWith('/journals/journal-1/attachments')) {
      attachmentUploadCount += 1;
      const attachment = {
        id: 'attachment-1',
        file_name: 'window-light.png',
        mime_type: 'image/png',
        size_bytes: 4096,
        created_at: new Date().toISOString(),
        caption: null,
        url: 'https://example.com/window-light.png',
      };
      journal = {
        ...journal,
        attachments: [...journal.attachments, attachment],
        updated_at: new Date().toISOString(),
      };
      await fulfillJson(route, attachment);
      return;
    }

    if (method === 'DELETE' && path.endsWith('/journals/journal-1/attachments/attachment-1')) {
      journal = {
        ...journal,
        attachments: [],
        updated_at: new Date().toISOString(),
      };
      await route.fulfill({ status: 204, headers: MOCK_API_HEADERS, body: '' });
      return;
    }

    if (method === 'DELETE' && path.endsWith('/journals/journal-1')) {
      await route.fulfill({ status: 204, headers: MOCK_API_HEADERS, body: '' });
      return;
    }

    await fulfillJson(route, {});
  });

  return {
    createPayloads,
    getAttachmentUploadCount: () => attachmentUploadCount,
    getJournal: () => journal,
    updatePayloads,
  };
}

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('name@example.com').fill('journal@example.com');
  await page.locator('input[type="password"]').fill('password123');
  const submitButton = page.getByRole('button', { name: '登入並回到 Haven' });
  await expect(submitButton).toBeEnabled();
  await submitButton.click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

function visibleJournalEditor(page: Page) {
  return page.locator('[aria-label="Journal writing canvas"]:visible').first();
}

test.describe('Journal 書房 v3', () => {
  test.use({ bypassCSP: true });
  test.describe.configure({ mode: 'serial' });
  test.setTimeout(60_000);

  test('creates a new page, saves it, reloads it, and saves again after image insertion', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    const apiState = await mockJournalApi(page, { withExistingJournal: false });
    await login(page);

    await page.goto('/journal');
    await expect(
      page.getByRole('heading', { level: 1, name: '把值得留下來的心事，寫成真正可重讀的一頁。' }),
    ).toBeVisible();

    await page.getByRole('button', { name: '開始新的一頁' }).click();
    await expect(page.getByLabel('Journal title')).toBeVisible();

    await page.getByLabel('Journal title').fill('夜裡想留下的一頁');

    const editor = visibleJournalEditor(page);
    await editor.click();
    await editor.pressSequentially('今晚我想先慢一點，也想先被理解。');
    await expect(editor).toContainText('今晚我想先慢一點，也想先被理解。');

    const createPageButton = page.getByRole('button', { name: '建立這一頁' });
    const saveDraftButton = page.getByRole('button', { name: /保存草稿|立即保存/ }).first();
    const usedCreateButton = await createPageButton.isVisible().catch(() => false);
    if (usedCreateButton) {
      await createPageButton.click();
    } else {
      await expect(saveDraftButton).toBeVisible();
      await saveDraftButton.click();
    }

    await expect(page).toHaveURL(/\/journal\/journal-1$/);
    expect(apiState.createPayloads.length).toBeGreaterThanOrEqual(1);
    expect(apiState.createPayloads[0]?.visibility).toBe('PRIVATE');
    if (usedCreateButton) {
      expect(apiState.createPayloads[0]).toEqual({
        content: '今晚我想先慢一點，也想先被理解。',
        content_format: 'markdown',
        is_draft: false,
        title: '夜裡想留下的一頁',
        visibility: 'PRIVATE',
      });
    }

    await page.reload();
    await expect(page.getByLabel('Journal title')).toHaveValue('夜裡想留下的一頁');
    await expect(visibleJournalEditor(page)).toContainText('今晚我想先慢一點，也想先被理解。');

    await page.getByTestId('journal-file-input').setInputFiles({
      name: 'window-light.png',
      mimeType: 'image/png',
      buffer: Buffer.from('journal-v3-image'),
    });

    await expect(page.getByRole('img', { name: 'window light' }).first()).toBeVisible();
    expect(apiState.getAttachmentUploadCount()).toBe(1);
    expect(apiState.updatePayloads.at(-1)?.content).toContain('![window light](attachment:attachment-1)');

    await editor.click();
    await editor.press('End');
    await editor.pressSequentially('\n\n我想再補上一句，讓這頁更完整。');
    await page.getByRole('button', { name: /保存草稿|立即保存/ }).first().click();

    await expect.poll(() => apiState.updatePayloads.length).toBeGreaterThanOrEqual(2);
    expect(apiState.updatePayloads.at(-1)?.content).toContain('我想再補上一句，讓這頁更完整。');
    expect(apiState.updatePayloads.at(-1)?.content).toContain('![window light](attachment:attachment-1)');

    await page.getByRole('button', { name: '閱讀' }).click();
    await expect(page.getByRole('heading', { level: 2, name: '夜裡想留下的一頁' })).toBeVisible();
    await expect(page.getByRole('img', { name: 'window light' }).first()).toBeVisible();
  });

  test('auto-creates a blank draft before image upload so the flow does not deadlock', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 960 });
    const apiState = await mockJournalApi(page, { withExistingJournal: false });
    await login(page);

    await page.goto('/journal');
    await page.getByRole('button', { name: '開始新的一頁' }).click();
    await expect(page.getByLabel('Journal title')).toBeVisible();

    const chooserPromise = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: '插入圖片' }).click();
    const chooser = await chooserPromise;
    await chooser.setFiles({
      name: 'window-light.png',
      mimeType: 'image/png',
      buffer: Buffer.from('journal-v3-image'),
    });

    await expect(page).toHaveURL(/\/journal\/journal-1$/);
    expect(apiState.createPayloads).toHaveLength(1);
    expect(apiState.getAttachmentUploadCount()).toBe(1);
    expect(apiState.updatePayloads).toHaveLength(1);
    expect(apiState.createPayloads[0]).toEqual({
      content: '',
      content_format: 'markdown',
      is_draft: true,
      title: null,
      visibility: 'PRIVATE',
    });
    expect(apiState.updatePayloads[0]?.is_draft).toBe(true);
    expect(apiState.updatePayloads[0]?.content).toContain('![window light](attachment:attachment-1)');
    await expect(page.getByRole('img', { name: 'window light' }).first()).toBeVisible();
    await expect(page.getByText('暫時沒收好')).toHaveCount(0);
    await expect(page.getByText('草稿已收好')).toBeVisible();
  });

  test('slash menu stays visible near the viewport edge and supports keyboard selection', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 780 });
    await mockJournalApi(page, { withExistingJournal: false });
    await login(page);

    await page.goto('/journal');
    await page.getByRole('button', { name: '開始新的一頁' }).click();

    const editor = visibleJournalEditor(page);
    await editor.click();
    for (let index = 0; index < 14; index += 1) {
      await editor.pressSequentially(`第 ${index + 1} 段`);
      await editor.press('Enter');
      await editor.press('Enter');
    }
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await editor.press('End');
    await editor.press('Enter');
    await editor.pressSequentially('/');

    const slashMenu = page.getByTestId('journal-slash-menu');
    await expect(slashMenu).toBeVisible();
    const menuBounds = await slashMenu.boundingBox();
    expect(menuBounds).not.toBeNull();
    if (menuBounds) {
      expect(menuBounds.y).toBeGreaterThanOrEqual(0);
      expect(menuBounds.y + menuBounds.height).toBeLessThanOrEqual(780);
    }

    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await expect(page.getByTestId('journal-slash-option-heading-2')).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('Escape');
    await expect(slashMenu).toBeHidden();

    await editor.press('Backspace');
    await editor.press('Enter');
    await editor.pressSequentially('/link');
    await expect(slashMenu).toBeVisible();
    await page.keyboard.press('Enter');
    await expect(visibleJournalEditor(page)).toContainText('連結文字');
  });

  test('document map keeps long-form structure navigable across write, read, and compare modes', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 780 });
    const longMiddleSection = Array.from({ length: 18 }, (_, index) => {
      return `這是中段第 ${index + 1} 段，讓長文真的拉開距離。`;
    }).join('\n\n');

    await mockJournalApi(page, {
      withExistingJournal: true,
      journalOverrides: {
        title: 'Map Flow Check',
        content: [
          '# Opening Scene',
          '',
          '先把第一節寫成真正的起點。',
          '',
          longMiddleSection,
          '',
          '## What I Need',
          '',
          '最後把真正想留下的重點安放下來。',
        ].join('\n'),
      },
    });
    await login(page);

    await page.goto('/journal/journal-1');
    await expect(page.getByTestId('journal-document-map')).toBeVisible();
    await expect(page.getByTestId('journal-document-map-entry-map-flow-check')).toBeVisible();
    await expect(page.getByTestId('journal-document-map-entry-opening-scene')).toBeVisible();
    await expect(page.getByTestId('journal-document-map-entry-what-i-need')).toBeVisible();

    const writeTarget = page.getByTestId('journal-write-section-what-i-need');
    await expect(writeTarget).not.toBeInViewport();
    await page.getByTestId('journal-document-map-entry-what-i-need').click();
    await expect(writeTarget).toBeInViewport();

    await page.getByRole('button', { name: '閱讀' }).click();
    const readTarget = page.getByTestId('journal-read-section-what-i-need');
    await expect(readTarget).not.toBeInViewport();
    await page.getByTestId('journal-document-map-entry-what-i-need').click();
    await expect(readTarget).toBeInViewport();

    await page.getByRole('button', { name: '對照' }).click();
    await expect(visibleJournalEditor(page)).toBeVisible();
    await expect(readTarget).not.toBeInViewport();
    await page.getByTestId('journal-document-map-entry-what-i-need').click();
    await expect(readTarget).toBeInViewport();
  });

  test('home journal composer hands off into Journal 書房 instead of publishing directly', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    const apiState = await mockJournalApi(page, { withExistingJournal: false });
    await login(page);

    await page.goto('/');
    await page.getByLabel('日記內容').fill('把這一段帶進 Journal 書房，再慢慢變成完整的一頁。');
    await page.getByRole('button', { name: '帶著這段進入 Journal 書房' }).click();

    await expect(page).toHaveURL(/\/journal\?compose=1$/);
    await expect(visibleJournalEditor(page)).toContainText(
      '把這一段帶進 Journal 書房，再慢慢變成完整的一頁。',
    );
    expect(apiState.createPayloads).toHaveLength(0);
  });
});
