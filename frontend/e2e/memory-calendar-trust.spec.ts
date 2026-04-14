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

type TimelineAppreciationItem = {
  type: 'appreciation';
  id: string;
  body_text: string;
};

type TimelineCardItem = {
  type: 'card';
  session_id: string;
  card_title: string;
  card_question: string;
  my_answer?: string | null;
  partner_answer?: string | null;
};

type TimelineJournalItem = {
  type: 'journal';
  id: string;
  content_preview?: string | null;
};

type TimelinePhotoItem = {
  type: 'photo';
  id: string;
  caption?: string | null;
};

type TimelineItem =
  | TimelineAppreciationItem
  | TimelineCardItem
  | TimelineJournalItem
  | TimelinePhotoItem;

type TimelineResponse = {
  data?: {
    items: TimelineItem[];
  };
  items?: TimelineItem[];
};

type FocusTarget = {
  kind: 'appreciation' | 'card' | 'journal' | 'photo';
  id: string;
};

type DayReference = {
  date: string;
  headingDate: string;
  snippet: string;
  focus: FocusTarget;
};

const MEMORY_API_ORIGIN = 'http://127.0.0.1:8000';
const TZ_OFFSET_MINUTES = new Date().getTimezoneOffset();

function unwrapCalendarDays(payload: CalendarResponse) {
  return payload.data?.days ?? payload.days ?? [];
}

function unwrapTimelineItems(payload: TimelineResponse) {
  return payload.data?.items ?? payload.items ?? [];
}

function formatHeadingDate(date: string) {
  const [year, month, day] = date.split('-').map(Number);
  return `${year}年${month}月${day}日`;
}

function buildFocusTarget(item: TimelineItem): FocusTarget {
  if (item.type === 'card') {
    return { kind: 'card', id: item.session_id };
  }

  return { kind: item.type, id: item.id };
}

function buildVisibleSnippet(item: TimelineItem) {
  if (item.type === 'appreciation') {
    return item.body_text.trim();
  }
  if (item.type === 'card') {
    return item.partner_answer?.trim() || item.my_answer?.trim() || item.card_question.trim() || item.card_title.trim();
  }
  if (item.type === 'journal') {
    return item.content_preview?.trim() ?? '';
  }
  return item.caption?.trim() ?? '';
}

function buildDayReference(date: string, items: TimelineItem[]): DayReference | null {
  for (const item of items) {
    const snippet = buildVisibleSnippet(item);
    if (!snippet) {
      continue;
    }

    return {
      date,
      headingDate: formatHeadingDate(date),
      snippet,
      focus: buildFocusTarget(item),
    };
  }

  return null;
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

async function fetchDayReferences(request: APIRequestContext, token: string) {
  const now = new Date();
  const calendarResponse = await request.get(`${MEMORY_API_ORIGIN}/api/memory/calendar`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    params: {
      year: now.getFullYear(),
      month: now.getMonth() + 1,
      tz_offset_minutes: TZ_OFFSET_MINUTES,
    },
  });
  expect(calendarResponse.ok()).toBeTruthy();

  const calendarPayload = (await calendarResponse.json()) as CalendarResponse;
  const activeDates = unwrapCalendarDays(calendarPayload)
    .filter((day) => day.journal_count > 0 || day.card_count > 0 || day.appreciation_count > 0 || day.has_photo)
    .map((day) => day.date);

  expect(activeDates.length).toBeGreaterThanOrEqual(2);

  const references: DayReference[] = [];
  for (const date of activeDates) {
    const timelineResponse = await request.get(`${MEMORY_API_ORIGIN}/api/memory/timeline`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      params: {
        from_date: date,
        to_date: date,
        tz_offset_minutes: TZ_OFFSET_MINUTES,
        limit: 100,
      },
    });
    expect(timelineResponse.ok()).toBeTruthy();

    const timelinePayload = (await timelineResponse.json()) as TimelineResponse;
    const items = unwrapTimelineItems(timelinePayload);
    const reference = buildDayReference(date, items);
    if (!reference) {
      continue;
    }

    references.push(reference);
    if (references.length === 2) {
      break;
    }
  }

  expect(references.length).toBeGreaterThanOrEqual(2);
  return references;
}

test.describe('Memory calendar trust recovery', () => {
  test('manual calendar selection overrides a deep-linked day and reveals the clicked date content on the live local stack', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(90_000);
    test.skip(
      process.env.MEMORY_CALENDAR_LIVE_E2E !== '1',
      'Set MEMORY_CALENDAR_LIVE_E2E=1 to run against the seeded local Postgres stack.',
    );

    const token = await authenticate(request, context);
    const [dayA, dayB] = await fetchDayReferences(request, token);
    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';

    await page.goto(
      `${appBaseUrl}/memory?date=${dayA.date}&kind=${dayA.focus.kind}&id=${dayA.focus.id}`,
      { waitUntil: 'domcontentloaded' },
    );

    const selectedDayButton = page.locator(`button[aria-label^="${dayA.date}"]`);
    await expect(selectedDayButton).toHaveAttribute('aria-pressed', 'true', { timeout: 15_000 });
    const daySpotlight = page.getByText('Day Spotlight').locator('..');
    await expect(daySpotlight).toBeVisible({ timeout: 15_000 });
    await expect(daySpotlight.getByRole('heading', { level: 3 })).toContainText(dayA.headingDate);
    await expect(page.getByText(dayA.snippet)).toBeVisible();
    await expect(page.locator('[data-memory-focused="true"]')).toHaveCount(1);

    const targetDayButton = page.locator(`button[aria-label^="${dayB.date}"]`);
    await expect(targetDayButton).toBeVisible();
    await targetDayButton.click();

    await expect.poll(() => {
      const url = new URL(page.url());
      return JSON.stringify({
        path: url.pathname,
        date: url.searchParams.get('date'),
        kind: url.searchParams.get('kind'),
        id: url.searchParams.get('id'),
      });
    }).toBe(
      JSON.stringify({
        path: '/memory',
        date: dayB.date,
        kind: null,
        id: null,
      }),
    );

    await expect(targetDayButton).toHaveAttribute('aria-pressed', 'true');
    await expect(daySpotlight.getByRole('heading', { level: 3 })).toContainText(dayB.headingDate);
    await expect(page.getByText(dayB.snippet)).toBeVisible();
    await expect(page.getByText(dayA.snippet)).not.toBeVisible();
    await expect(page.locator('[data-memory-focused="true"]')).toHaveCount(0);
    await expect(page.getByText('這一天目前沒有可展開的細節。')).not.toBeVisible();
  });
});
