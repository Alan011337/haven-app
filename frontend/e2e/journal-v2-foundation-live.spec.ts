import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import {
  expect,
  test,
  type APIRequestContext,
  type BrowserContext,
  type Page,
} from '@playwright/test';

type AuthPayload = {
  access_token: string;
  refresh_token?: string;
};

const API_ORIGIN = 'http://127.0.0.1:8000';
const SEEDED_LIVE_JOURNAL_ID = 'd0000000-0000-4000-8000-000000000001';
const SCREENSHOT_DIR = '/Users/alanzeng/projects/Haven-local/output/playwright';
const WRITE_CONTINUITY_SCREENSHOT_PATH = path.join(SCREENSHOT_DIR, 'journal-continuity-write.png');
const READ_CONTINUITY_SCREENSHOT_PATH = path.join(SCREENSHOT_DIR, 'journal-continuity-read.png');
const COMPARE_CONTINUITY_SCREENSHOT_PATH = path.join(
  SCREENSHOT_DIR,
  'journal-continuity-compare.png',
);
const VALID_PNG_BUFFER = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR42mP8z8BQDwAF/wJ+g0n7WQAAAABJRU5ErkJggg==',
  'base64',
);

async function authenticate(
  request: APIRequestContext,
  context: BrowserContext,
  appBaseUrl: string,
) {
  const authResponse = await request.post(`${API_ORIGIN}/api/auth/token`, {
    form: {
      username: 'alice@example.com',
      password: 'havendev1',
    },
  });
  expect(authResponse.ok()).toBeTruthy();

  const authPayload = (await authResponse.json()) as AuthPayload;
  await context.addCookies(
    [
      {
        name: 'access_token',
        value: authPayload.access_token,
        url: appBaseUrl,
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
      authPayload.refresh_token
        ? {
            name: 'refresh_token',
            value: authPayload.refresh_token,
            url: appBaseUrl,
            httpOnly: true,
            sameSite: 'Lax' as const,
          }
        : null,
    ].filter(Boolean) as Array<{
      httpOnly: boolean;
      name: string;
      sameSite: 'Lax';
      url: string;
      value: string;
    }>,
  );

  return authPayload;
}

function visibleJournalEditor(page: Page) {
  return page.locator('[aria-label="Journal writing canvas"]:visible').first();
}

async function captureViewportScreenshotViaCdp(page: Page, filePath: string) {
  const client = await page.context().newCDPSession(page);
  const screenshot = await client.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
  });
  await writeFile(filePath, screenshot.data, 'base64');
}

async function prepareStructuredJournal(
  request: APIRequestContext,
  accessToken: string,
  title: string,
) {
  const longMiddleSection = Array.from({ length: 18 }, (_, index) => {
    return `這是長文段落 ${index + 1}，讓第二個章節真的需要被導覽。`;
  }).join('\n\n');
  const content = [
    '# Opening Scene',
    '',
    '先把第一節寫成真正的起點。',
    '',
    longMiddleSection,
    '',
    '## What I Need',
    '',
    '把最後的重點安靜留下來。',
  ].join('\n');

  const updateResponse = await request.patch(`${API_ORIGIN}/api/journals/${SEEDED_LIVE_JOURNAL_ID}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Idempotency-Key': `journal-v2-foundation-${Date.now()}`,
      'X-Device-Id': 'journal-v2-live-device',
    },
    data: {
      title,
      content,
      is_draft: false,
      visibility: 'PRIVATE',
    },
  });
  expect(updateResponse.ok()).toBeTruthy();
  return {
    content,
    id: SEEDED_LIVE_JOURNAL_ID,
  };
}

async function prepareContinuityJournal(
  request: APIRequestContext,
  accessToken: string,
  title: string,
) {
  const content = [
    '# Opening Scene',
    '',
    '先把第一節寫成真正的起點。',
    '',
    '這一頁現在需要的不只是文字存在，還要讓節奏在 write 與 read 之間維持同一種呼吸。',
    '',
    '> 先讓這一段被原樣聽見，不急著結論。',
    '',
    '## What I Need',
    '',
    '這裡開始進入更明確的整理。',
    '',
    '- 第一個需要被看見的點',
    '- 第二個需要被接住的點',
    '',
    '---',
    '',
    '收尾那一段要安靜落下，不要像切到另一個產品。',
  ].join('\n');

  const updateResponse = await request.patch(`${API_ORIGIN}/api/journals/${SEEDED_LIVE_JOURNAL_ID}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Idempotency-Key': `journal-continuity-live-${Date.now()}`,
      'X-Device-Id': 'journal-continuity-live-device',
    },
    data: {
      title,
      content,
      is_draft: false,
      visibility: 'PRIVATE',
    },
  });
  expect(updateResponse.ok()).toBeTruthy();

  return {
    id: SEEDED_LIVE_JOURNAL_ID,
    title,
  };
}

async function waitForJournalAttachmentUpload(page: Page, journalId: string) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.ok() &&
      response.request().method() === 'POST' &&
      url.pathname === `/api/journals/${journalId}/attachments`
    );
  });
}

async function waitForJournalContentUpdate(page: Page, journalId: string) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.ok() &&
      response.request().method() === 'PATCH' &&
      url.pathname === `/api/journals/${journalId}`
    );
  });
}

async function waitForAttachmentCaptionUpdate(page: Page, journalId: string) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.ok() &&
      response.request().method() === 'PATCH' &&
      /^\/api\/journals\/[^/]+\/attachments\/[^/]+$/.test(url.pathname) &&
      url.pathname.startsWith(`/api/journals/${journalId}/attachments/`)
    );
  });
}

test.describe('Journal V2 foundation live local stack', () => {
  test.describe.configure({ mode: 'serial' });

  test('document map keeps a real journal page navigable across write, read, and compare after reload', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(120_000);
    test.skip(
      process.env.JOURNAL_V2_LIVE_E2E !== '1',
      'Set JOURNAL_V2_LIVE_E2E=1 to run against the local seeded stack.',
    );

    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';
    const uniqueTitle = `Document Map Live ${Date.now()}`;
    const authPayload = await authenticate(request, context, appBaseUrl);
    const journal = await prepareStructuredJournal(request, authPayload.access_token, uniqueTitle);
    expect(journal.id).toBeTruthy();

    await page.goto(`${appBaseUrl}/journal/${journal.id}`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('Journal title')).toHaveValue(uniqueTitle, { timeout: 20_000 });

    const documentMap = page.getByTestId('journal-document-map');
    const mapEntry = page.getByTestId('journal-document-map-entry-what-i-need');
    const writeTarget = page.getByTestId('journal-write-section-what-i-need');

    await expect(documentMap).toBeVisible();
    await expect(mapEntry).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await mapEntry.click();
    await expect(writeTarget).toBeInViewport();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('Journal title')).toHaveValue(uniqueTitle, { timeout: 20_000 });
    await expect(documentMap).toBeVisible();

    await page.getByRole('button', { name: '閱讀' }).click();
    const readTarget = page.getByTestId('journal-read-section-what-i-need');
    await mapEntry.click();
    await expect(readTarget).toBeInViewport();

    await page.getByRole('button', { name: '對照' }).click();
    await expect(visibleJournalEditor(page)).toBeVisible();
    await mapEntry.click();
    await expect(readTarget).toBeInViewport();
  });

  test('write, read, and compare keep one coherent document rhythm with image and caption content', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(180_000);
    test.skip(
      process.env.JOURNAL_CONTINUITY_LIVE_E2E !== '1',
      'Set JOURNAL_CONTINUITY_LIVE_E2E=1 to run against the local seeded stack.',
    );

    await mkdir(SCREENSHOT_DIR, { recursive: true });

    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';
    const uniqueTitle = `Continuity Live ${Date.now()}`;
    const authoredCaption = '夜裡的照片也應該跟文字呼吸一致。';
    await page.setViewportSize({ width: 1440, height: 1200 });
    const authPayload = await authenticate(request, context, appBaseUrl);
    const journal = await prepareContinuityJournal(request, authPayload.access_token, uniqueTitle);

    await page.goto(`${appBaseUrl}/journal/${journal.id}`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('Journal title')).toHaveValue(uniqueTitle, { timeout: 20_000 });
    await expect(page.getByTestId('journal-document-map')).toBeVisible();

    const fileInput = page.getByTestId('journal-file-input');
    const uploadResponsePromise = waitForJournalAttachmentUpload(page, journal.id);
    const updateResponsePromise = waitForJournalContentUpdate(page, journal.id);
    await fileInput.setInputFiles({
      name: 'continuity-light.png',
      mimeType: 'image/png',
      buffer: VALID_PNG_BUFFER,
    });
    await uploadResponsePromise;
    await updateResponsePromise;

    const captionField = page.getByPlaceholder('為這張照片寫一句話（選填）').first();
    await expect(captionField).toBeVisible();
    await captionField.fill(authoredCaption);
    const captionUpdatePromise = waitForAttachmentCaptionUpdate(page, journal.id);
    await page.getByLabel('Journal title').click();
    await captionUpdatePromise;

    const writeSection = page.getByTestId('journal-write-section-what-i-need');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.getByTestId('journal-document-map-entry-what-i-need').click();
    await expect(writeSection).toBeInViewport();
    await expect(visibleJournalEditor(page)).toContainText('先把第一節寫成真正的起點。');
    await expect(visibleJournalEditor(page)).toContainText('先讓這一段被原樣聽見，不急著結論。');
    await expect(captionField).toHaveValue(authoredCaption);
    await page.screenshot({ path: WRITE_CONTINUITY_SCREENSHOT_PATH, fullPage: true });

    await page.getByRole('button', { name: '閱讀' }).click();
    const readSection = page.getByTestId('journal-read-section-what-i-need');
    await page.getByTestId('journal-document-map-entry-what-i-need').click();
    await expect(readSection).toBeInViewport();
    const readCaption = page.locator('figcaption').filter({ hasText: authoredCaption }).first();
    await expect(readCaption).toBeVisible();
    await expect(page.getByText('continuity light', { exact: true })).toHaveCount(0);
    await page.screenshot({ path: READ_CONTINUITY_SCREENSHOT_PATH, fullPage: true });

    await page.getByRole('button', { name: '對照' }).click();
    await expect(visibleJournalEditor(page)).toBeVisible();
    await page.getByTestId('journal-document-map-entry-what-i-need').click();
    await expect(readSection).toBeInViewport();
    await expect(readCaption).toBeVisible();
    await captureViewportScreenshotViaCdp(page, COMPARE_CONTINUITY_SCREENSHOT_PATH);
  });
});
