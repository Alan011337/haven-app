import { expect, test, type APIRequestContext, type BrowserContext } from '@playwright/test';

type AuthPayload = {
  access_token: string;
  refresh_token?: string;
};

type CalendarDay = {
  date: string;
  journal_count: number;
  card_count: number;
  appreciation_count: number;
  has_photo: boolean;
};

type CalendarResponse = {
  data?: {
    year: number;
    month: number;
    days: CalendarDay[];
  };
  year?: number;
  month?: number;
  days?: CalendarDay[];
};

type TimelineJournalItem = {
  type: 'journal';
  id: string;
  content_preview?: string | null;
};

type TimelineCardItem = {
  type: 'card';
  session_id: string;
  card_title: string;
  card_question: string;
  my_answer?: string | null;
  partner_answer?: string | null;
};

type TimelineAppreciationItem = {
  type: 'appreciation';
  id: string;
  body_text: string;
  is_mine: boolean;
};

type TimelinePhotoItem = {
  type: 'photo';
  id: string;
  caption?: string | null;
};

type TimelineItem =
  | TimelineJournalItem
  | TimelineCardItem
  | TimelineAppreciationItem
  | TimelinePhotoItem;

type TimelineResponse = {
  data?: {
    items: TimelineItem[];
  };
  items?: TimelineItem[];
};

type JournalDetailResponse = {
  id: string;
  content: string;
};

type DeckHistoryEntry = {
  session_id: string;
  card_question: string;
  my_answer: string | null;
  partner_answer: string | null;
};

type AppreciationDetailResponse = {
  id: number;
  body_text: string;
  is_mine: boolean;
};

type JournalArtifactReference = {
  date: string;
  id: string;
  previewSnippet: string;
  fullSnippet: string;
};

type CardArtifactReference = {
  date: string;
  sessionId: string;
  previewSnippet: string;
  question: string;
  myAnswer: string;
  partnerAnswer: string;
};

type AppreciationArtifactReference = {
  date: string;
  id: string;
  previewSnippet: string;
  bodyText: string;
  isMine: boolean;
};

type ArtifactReferences = {
  journal: JournalArtifactReference | null;
  card: CardArtifactReference | null;
  appreciation: AppreciationArtifactReference | null;
};

const MEMORY_API_ORIGIN = 'http://127.0.0.1:8000';
const TZ_OFFSET_MINUTES = new Date().getTimezoneOffset();

function unwrapCalendarDays(payload: CalendarResponse) {
  return payload.data?.days ?? payload.days ?? [];
}

function unwrapTimelineItems(payload: TimelineResponse) {
  return payload.data?.items ?? payload.items ?? [];
}

function takeSnippet(text: string, maxLength = 48) {
  const normalized = text.replace(/\s+/g, ' ').trim();
  return normalized.slice(0, maxLength).trim();
}

function stripMarkdownToSnippet(text: string, maxLength = 48) {
  const normalized = text
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/[*_`>#-]/g, ' ')
    .replace(/\[[^\]]+\]\([^)]+\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return normalized.slice(0, maxLength).trim();
}

async function authenticate(
  request: APIRequestContext,
  context: BrowserContext,
) {
  const authResponse = await request.post(`${MEMORY_API_ORIGIN}/api/auth/token`, {
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

  return authPayload.access_token;
}

async function fetchJson<T>(request: APIRequestContext, token: string, path: string, params?: Record<string, string | number>) {
  const response = await request.get(`${MEMORY_API_ORIGIN}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    params,
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as T;
}

async function tryFetchJson<T>(request: APIRequestContext, token: string, path: string, params?: Record<string, string | number>) {
  const response = await request.get(`${MEMORY_API_ORIGIN}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    params,
  });
  if (!response.ok()) {
    return null;
  }
  return (await response.json()) as T;
}

async function fetchArtifactReferences(request: APIRequestContext, token: string): Promise<ArtifactReferences> {
  const now = new Date();
  const calendarPayload = await fetchJson<CalendarResponse>(request, token, '/api/memory/calendar', {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    tz_offset_minutes: TZ_OFFSET_MINUTES,
  });

  const activeDates = unwrapCalendarDays(calendarPayload)
    .filter((day) => day.journal_count > 0 || day.card_count > 0 || day.appreciation_count > 0 || day.has_photo)
    .map((day) => day.date);

  expect(activeDates.length).toBeGreaterThan(0);

  const references: ArtifactReferences = {
    journal: null,
    card: null,
    appreciation: null,
  };

  for (const date of activeDates) {
    const timelinePayload = await fetchJson<TimelineResponse>(request, token, '/api/memory/timeline', {
      from_date: date,
      to_date: date,
      tz_offset_minutes: TZ_OFFSET_MINUTES,
      limit: 100,
    });
    const items = unwrapTimelineItems(timelinePayload);

    for (const item of items) {
      if (!references.journal && item.type === 'journal' && item.content_preview?.trim()) {
        const journalDetail = await tryFetchJson<JournalDetailResponse>(request, token, `/api/journals/${item.id}`);
        if (!journalDetail) {
          continue;
        }
        const fullSnippet = stripMarkdownToSnippet(journalDetail.content);
        if (fullSnippet) {
          references.journal = {
            date,
            id: item.id,
            previewSnippet: takeSnippet(item.content_preview),
            fullSnippet,
          };
        }
      }

      if (!references.card && item.type === 'card') {
        const cardDetail = await tryFetchJson<DeckHistoryEntry>(request, token, `/api/card-decks/history/${item.session_id}`);
        if (!cardDetail) {
          continue;
        }
        references.card = {
          date,
          sessionId: item.session_id,
          previewSnippet: takeSnippet(item.card_question || item.card_title),
          question: takeSnippet(cardDetail.card_question, 80),
          myAnswer: takeSnippet(cardDetail.my_answer ?? '', 80),
          partnerAnswer: takeSnippet(cardDetail.partner_answer ?? '', 80),
        };
      }

      if (!references.appreciation && item.type === 'appreciation' && item.body_text.trim()) {
        const appreciationDetail = await fetchJson<AppreciationDetailResponse>(request, token, `/api/appreciations/${item.id}`);
        references.appreciation = {
          date,
          id: String(appreciationDetail.id),
          previewSnippet: takeSnippet(item.body_text),
          bodyText: takeSnippet(appreciationDetail.body_text, 80),
          isMine: appreciationDetail.is_mine,
        };
      }
    }

    if (references.journal && references.card && references.appreciation) {
      break;
    }
  }

  return references;
}

test.describe('Memory artifact open-through', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(
      process.env.MEMORY_ARTIFACT_LIVE_E2E !== '1',
      'Set MEMORY_ARTIFACT_LIVE_E2E=1 to run against the seeded local Postgres stack.',
    );
    page.setDefaultTimeout(20_000);
  });

  test('journal day spotlight items open the full journal and return to the selected memory day', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(90_000);

    const token = await authenticate(request, context);
    const references = await fetchArtifactReferences(request, token);
    expect(references.journal).not.toBeNull();
    const journal = references.journal!;
    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';

    await page.goto(`${appBaseUrl}/memory?date=${journal.date}`, { waitUntil: 'domcontentloaded' });

    const selectedDayButton = page.locator(`button[aria-label^="${journal.date}"]`);
    await expect(selectedDayButton).toHaveAttribute('aria-pressed', 'true', { timeout: 15_000 });
    await expect(page.getByTestId('memory-day-reveal-summary')).toBeVisible();

    const journalCard = page.locator('[data-memory-kind="journal"]').filter({ hasText: journal.previewSnippet }).first();
    await expect(journalCard).toBeVisible();
    const journalRevealRow = page.getByTestId(`memory-day-reveal-row-journal:${journal.id}`).first();
    await expect(journalRevealRow).toBeVisible();
    await expect(journalRevealRow).toContainText(journal.previewSnippet);
    await journalRevealRow.getByRole('button', { name: '打開完整日記' }).click();

    await expect.poll(() => {
      const url = new URL(page.url());
      return JSON.stringify({
        path: url.pathname,
        from: url.searchParams.get('from'),
        date: url.searchParams.get('date'),
      });
    }, { timeout: 45_000 }).toBe(
      JSON.stringify({
        path: `/journal/${journal.id}`,
        from: 'memory',
        date: journal.date,
      }),
    );

    await expect(page.getByText(journal.fullSnippet, { exact: false }).first()).toBeVisible({ timeout: 20_000 });

    await page.getByRole('link', { name: '返回' }).first().click();

    await expect.poll(() => {
      const url = new URL(page.url());
      return JSON.stringify({
        path: url.pathname,
        date: url.searchParams.get('date'),
      });
    }, { timeout: 30_000 }).toBe(
      JSON.stringify({
        path: '/memory',
        date: journal.date,
      }),
    );
    await expect(selectedDayButton).toHaveAttribute('aria-pressed', 'true');
  });

  test('card day spotlight items open the full card conversation dialog for the selected session', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(90_000);

    const token = await authenticate(request, context);
    const references = await fetchArtifactReferences(request, token);
    expect(references.card).not.toBeNull();
    const card = references.card!;
    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';

    await page.goto(`${appBaseUrl}/memory?date=${card.date}`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator(`button[aria-label^="${card.date}"]`)).toHaveAttribute('aria-pressed', 'true', { timeout: 15_000 });
    await expect(page.getByTestId('memory-day-reveal-summary')).toBeVisible();

    const cardMemory = page.locator('[data-memory-kind="card"]').filter({ hasText: card.previewSnippet }).first();
    const cardRevealRow = page.getByTestId(`memory-day-reveal-row-card:${card.sessionId}`).first();
    await expect(cardRevealRow).toBeVisible();
    await cardRevealRow.getByRole('button', { name: '定位片段' }).click();
    await expect(cardMemory).toBeVisible();
    await cardRevealRow.getByRole('button', { name: '打開完整卡片對話' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(card.question, { exact: false })).toBeVisible();
    await expect(dialog.getByText(card.myAnswer, { exact: false })).toBeVisible();
    await expect(dialog.getByText(card.partnerAnswer, { exact: false })).toBeVisible();

    await dialog.getByRole('button', { name: '關閉' }).click();
    await expect(dialog).not.toBeVisible();
  });

  test('appreciation day spotlight items open the full appreciation dialog for the selected note', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(90_000);

    const token = await authenticate(request, context);
    const references = await fetchArtifactReferences(request, token);
    expect(references.appreciation).not.toBeNull();
    const appreciation = references.appreciation!;
    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';

    await page.goto(`${appBaseUrl}/memory?date=${appreciation.date}`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator(`button[aria-label^="${appreciation.date}"]`)).toHaveAttribute('aria-pressed', 'true', { timeout: 15_000 });
    await expect(page.getByTestId('memory-day-reveal-summary')).toBeVisible();

    const appreciationCard = page.locator('[data-memory-kind="appreciation"]').filter({ hasText: appreciation.previewSnippet }).first();
    await expect(appreciationCard).toBeVisible();
    const appreciationRevealRow = page.getByTestId(`memory-day-reveal-row-appreciation:${appreciation.id}`).first();
    await expect(appreciationRevealRow).toBeVisible();
    await expect(appreciationRevealRow).toContainText(appreciation.previewSnippet);
    await appreciationRevealRow.getByRole('button', { name: '打開完整感謝' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(appreciation.bodyText, { exact: false })).toBeVisible();
    await expect(dialog.getByText(appreciation.isMine ? '我寫的' : '伴侶寫的')).toBeVisible();
  });
});
