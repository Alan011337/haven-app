import { expect, test, type APIRequestContext, type BrowserContext, type Page } from '@playwright/test';

type AuthPayload = {
  access_token: string;
  refresh_token?: string;
};

const API_ORIGIN = 'http://127.0.0.1:8000';

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

  const listResponse = await request.get(`${API_ORIGIN}/api/journals/`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  expect(listResponse.ok()).toBeTruthy();
  const listPayload = (await listResponse.json()) as {
    data?: Array<{ id?: string }>;
    id?: string;
  } | Array<{ id?: string }>;
  const journals = Array.isArray(listPayload)
    ? listPayload
    : Array.isArray(listPayload.data)
      ? listPayload.data
      : [];
  const journalId = journals[0]?.id ?? '';
  expect(journalId).toBeTruthy();

  const updateResponse = await request.patch(`${API_ORIGIN}/api/journals/${journalId}`, {
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
    id: journalId,
  };
}

test.describe('Journal V2 foundation live local stack', () => {
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
    await expect(page.getByLabel('Journal title')).toHaveValue(uniqueTitle);
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
});
