import { expect, test, type Page, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
  'access-control-allow-private-network': 'true',
  vary: 'Origin',
};

function resolveMockApiHeaders(route: Route) {
  const requestOrigin = route.request().headers().origin?.trim();
  return {
    ...MOCK_API_HEADERS,
    'access-control-allow-origin': requestOrigin || 'http://localhost:3000',
  };
}

function apiSuccess(data: unknown, requestId = 'love-map-repair-agreements-e2e-req') {
  return {
    data,
    meta: { request_id: requestId },
    error: null,
  };
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: resolveMockApiHeaders(route),
    body: JSON.stringify(apiSuccess(data)),
  });
}

async function mockRepairAgreementsApi(page: Page) {
  await page.context().addCookies([
    { name: 'access_token', value: 'repair-agreements-mock-token', url: 'http://127.0.0.1:3000' },
    { name: 'access_token', value: 'repair-agreements-mock-token', url: 'http://localhost:8000' },
  ]);

  const now = Date.now();
  const repairAgreementPayloads: Array<Record<string, unknown>> = [];
  let weeklyTaskCompletionCount = 0;
  let repairAgreementHistorySequence = 2;

  const buildFieldChanges = (
    previous: {
      protect_what_matters: string | null;
      avoid_in_conflict: string | null;
      repair_reentry: string | null;
    },
    next: {
      protect_what_matters: string | null;
      avoid_in_conflict: string | null;
      repair_reentry: string | null;
    },
  ) => {
    const fieldMeta = [
      ['protect_what_matters', '當張力升高時，我們想保護什麼'],
      ['avoid_in_conflict', '卡住或升高時，我們先避免什麼'],
      ['repair_reentry', '要重新開啟修復時，我們怎麼回來'],
    ] as const;

    return fieldMeta.flatMap(([key, label]) => {
      const beforeText = previous[key];
      const afterText = next[key];
      if (beforeText === afterText) {
        return [];
      }
      const change_kind = beforeText == null
        ? 'added'
        : afterText == null
          ? 'cleared'
          : 'updated';
      return [{
        key,
        label,
        change_kind,
        before_text: beforeText,
        after_text: afterText,
      }];
    });
  };

  const system = {
    has_partner: true,
    me: {
      id: 'me',
      full_name: 'Alice Chen',
      email: 'alice@example.com',
    },
    partner: {
      id: 'partner-1',
      partner_name: 'Bob',
    },
    baseline: {
      mine: {
        user_id: 'me',
        partner_id: 'partner-1',
        filled_at: new Date(now - 36 * 60 * 60 * 1000).toISOString(),
        scores: {
          intimacy: 4,
          conflict: 3,
          trust: 5,
          communication: 4,
          commitment: 5,
        },
      },
      partner: {
        user_id: 'partner-1',
        partner_id: 'me',
        filled_at: new Date(now - 30 * 60 * 60 * 1000).toISOString(),
        scores: {
          intimacy: 4,
          conflict: 3,
          trust: 4,
          communication: 4,
          commitment: 4,
        },
      },
    },
    couple_goal: {
      goal_slug: 'better_communication',
      chosen_at: new Date(now - 20 * 60 * 60 * 1000).toISOString(),
    },
    story: {
      available: true,
      moments: [],
      time_capsule: null,
    },
    notes: [],
    wishlist_items: [],
    stats: {
      filled_note_layers: 0,
      baseline_ready_mine: true,
      baseline_ready_partner: true,
      wishlist_count: 0,
      last_activity_at: new Date(now - 8 * 60 * 60 * 1000).toISOString(),
    },
    essentials: {
      my_care_preferences: {
        primary: 'words',
        secondary: 'time',
        updated_at: new Date(now - 10 * 60 * 60 * 1000).toISOString(),
      },
      my_care_profile: {
        support_me: '先陪我安靜一下。',
        avoid_when_stressed: '不要立刻追問。',
        small_delights: '回家時先抱我一下。',
        updated_at: new Date(now - 10 * 60 * 60 * 1000).toISOString(),
      },
      partner_care_preferences: {
        primary: 'acts',
        secondary: 'touch',
        updated_at: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      },
      partner_care_profile: {
        support_me: '先幫我把桌面收乾淨，我會比較能慢慢說。',
        avoid_when_stressed: '不要用玩笑帶過我真的在意的事。',
        small_delights: '如果你先幫我泡熱茶，我會覺得被照顧。',
        updated_at: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      },
      repair_agreements: {
        protect_what_matters: '先保護彼此的安全感，不在最高張力時替對方下定論。',
        avoid_in_conflict: '避免翻舊帳，也避免在還很急的時候一直逼對方給答案。',
        repair_reentry: '先留一段空氣，再在 24 小時內回來把感受與需要說清楚。',
        updated_by_name: 'Alice Chen',
        updated_at: new Date(now - 11 * 60 * 60 * 1000).toISOString(),
      },
      repair_agreement_history: [
        {
          id: 'repair-history-manual-1',
          changed_at: new Date(now - 11 * 60 * 60 * 1000).toISOString(),
          changed_by_name: 'Alice Chen',
          origin_kind: 'manual_edit',
          source_outcome_capture_id: null,
          source_captured_by_name: null,
          source_captured_at: null,
          fields: [
            {
              key: 'protect_what_matters',
              label: '當張力升高時，我們想保護什麼',
              change_kind: 'updated',
              before_text: '先保護彼此想修復的意圖。',
              after_text: '先保護彼此的安全感，不在最高張力時替對方下定論。',
            },
          ],
          revision_note: '我們決定先練一週看看再微調。',
        },
        {
          id: 'repair-history-carry-forward-1',
          changed_at: new Date(now - 26 * 60 * 60 * 1000).toISOString(),
          changed_by_name: 'Alice Chen',
          origin_kind: 'post_mediation_carry_forward',
          source_outcome_capture_id: 'capture-seeded-1',
          source_captured_by_name: 'Bob',
          source_captured_at: new Date(now - 27 * 60 * 60 * 1000).toISOString(),
          fields: [
            {
              key: 'repair_reentry',
              label: '要重新開啟修復時，我們怎麼回來',
              change_kind: 'updated',
              before_text: '先各自冷靜。',
              after_text: '先留一段空氣，再在 24 小時內回來把感受與需要說清楚。',
            },
          ],
          revision_note: null,
        },
        {
          // Superseded-no-note fixture: this is an earlier manual edit to
          // repair_reentry that carries a human "why." The later carry-forward
          // (entry above) overwrites the wording without a note, so the
          // primary echo for repair_reentry is absent. The fallback chip
          // should surface THIS entry's revision_note with explicit
          // `該段後來又有微調` framing, without implying the note describes
          // the current wording exactly.
          id: 'repair-history-manual-earliest',
          changed_at: new Date(now - 48 * 60 * 60 * 1000).toISOString(),
          changed_by_name: 'Alice Chen',
          origin_kind: 'manual_edit',
          source_outcome_capture_id: null,
          source_captured_by_name: null,
          source_captured_at: null,
          fields: [
            {
              key: 'repair_reentry',
              label: '要重新開啟修復時，我們怎麼回來',
              change_kind: 'updated',
              before_text: '吵完就各走各的。',
              after_text: '先各自冷靜。',
            },
          ],
          revision_note: '想先試試短暫分開、但不冷處理太久。',
        },
      ],
      weekly_task: {
        task_slug: 'task_note',
        task_label: '寫一張小紙條謝謝他/她',
        assigned_at: new Date(now - 2 * 24 * 60 * 60 * 1000).toISOString(),
        completed: false,
        completed_at: null,
      },
    },
  };

  const cards = {
    safe: [],
    medium: [],
    deep: [],
  };

  const apiHandler = async (route: Route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: resolveMockApiHeaders(route) });
      return;
    }

    if (path.includes('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'alice@example.com',
        full_name: system.me.full_name,
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Bob',
        savings_score: 42,
      });
      return;
    }

    if (path.endsWith('/love-map/system') && method === 'GET') {
      await fulfillJson(route, system);
      return;
    }

    if (path.endsWith('/love-map/cards') && method === 'GET') {
      await fulfillJson(route, cards);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future/refinements') && method === 'GET') {
      await fulfillJson(route, []);
      return;
    }

    if (path.endsWith('/love-map/essentials/repair-agreements') && method === 'PUT') {
      const payload = route.request().postDataJSON() as {
        protect_what_matters?: string | null;
        avoid_in_conflict?: string | null;
        repair_reentry?: string | null;
        revision_note?: string | null;
      };
      repairAgreementPayloads.push(payload);
      const previousRepairAgreements = {
        ...system.essentials.repair_agreements,
      };
      system.essentials.repair_agreements = {
        protect_what_matters: payload.protect_what_matters?.trim() || null,
        avoid_in_conflict: payload.avoid_in_conflict?.trim() || null,
        repair_reentry: payload.repair_reentry?.trim() || null,
        updated_by_name: system.me.full_name,
        updated_at: new Date().toISOString(),
      };
      const normalizedRevisionNote = payload.revision_note?.trim() || null;
      system.essentials.repair_agreement_history.unshift({
        id: `repair-history-manual-${repairAgreementHistorySequence}`,
        changed_at: system.essentials.repair_agreements.updated_at,
        changed_by_name: system.me.full_name,
        origin_kind: 'manual_edit',
        source_outcome_capture_id: null,
        source_captured_by_name: null,
        source_captured_at: null,
        fields: buildFieldChanges(previousRepairAgreements, system.essentials.repair_agreements),
        revision_note: normalizedRevisionNote,
      });
      repairAgreementHistorySequence += 1;
      system.essentials.repair_agreement_history = system.essentials.repair_agreement_history.slice(0, 5);
      system.stats.last_activity_at = system.essentials.repair_agreements.updated_at;
      await fulfillJson(route, system.essentials.repair_agreements);
      return;
    }

    if (path.endsWith('/love-languages/weekly-task/complete') && method === 'POST') {
      weeklyTaskCompletionCount += 1;
      system.essentials.weekly_task = {
        ...(system.essentials.weekly_task ?? {
          task_slug: 'task_note',
          task_label: '寫一張小紙條謝謝他/她',
          assigned_at: new Date(now).toISOString(),
        }),
        completed: true,
        completed_at: new Date().toISOString(),
      };
      await fulfillJson(route, system.essentials.weekly_task);
      return;
    }

    await fulfillJson(route, {});
  };

  await page.route('**/api/**', apiHandler);

  return {
    repairAgreementPayloads,
    get weeklyTaskCompletionCount() {
      return weeklyTaskCompletionCount;
    },
  };
}

test.describe('Repair Agreements deepening', () => {
  test.use({ bypassCSP: true });

  test('saves pair-maintained Repair Agreements in mocked mode', async ({ page }) => {
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Repair Agreements spec.',
    );

    const apiState = await mockRepairAgreementsApi(page);
    await page.goto('/love-map');

    await expect(page.getByTestId('relationship-heart-repair-agreements-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-updated-by')).toContainText('Alice Chen');
    await expect(page.getByTestId('relationship-heart-repair-agreements-history')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText('手動微調');
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-1')).toContainText('修復帶回');
    // Timeline entries collapse their before/after detail by default: each entry renders a
    // "觸及：…" scan line + an expand button. The detail panel is not mounted until opened.
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText('觸及：');
    // Revision-note excerpt: visible as an italic quoted chip when the change row carries one;
    // entries without a note never render the chip (no empty-space artifact).
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-note')).toContainText(
      '我們決定先練一週看看再微調。',
    );
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-1-note')).toHaveCount(0);
    // No carry-forward pending in this fixture, so the carry-forward helper line below the
    // revision-note input should NOT appear.
    await expect(page.getByText('這段註記會和從修復帶回的內容一起留下。')).toHaveCount(0);
    await expect(
      page.getByTestId('relationship-heart-repair-agreements-history-entry-0-expand'),
    ).toHaveText('看看這一次改了什麼');
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-detail')).toHaveCount(0);
    // Expanding entry 0 reveals the before/after cards and flips the button label.
    await page.getByTestId('relationship-heart-repair-agreements-history-entry-0-expand').click();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-detail')).toBeVisible();
    await expect(
      page.getByTestId('relationship-heart-repair-agreements-history-entry-0-expand'),
    ).toHaveText('收起這次的改動');
    // Collapse again so subsequent assertions read the default state.
    await page.getByTestId('relationship-heart-repair-agreements-history-entry-0-expand').click();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-detail')).toHaveCount(0);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters'),
    ).toContainText('目前採用');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry'),
    ).toContainText('修復帶回');
    // Per-field revision-intent echo: the latest change responsible for each field's current
    // value carries the human "why" directly into the field review panel. The manual_edit entry
    // that established the current protect_what_matters value carries a note, so the echo is
    // visible inside its field panel. The carry-forward entry responsible for repair_reentry
    // has revision_note: null, so no echo renders in that panel (zero pixels, no empty chip).
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters-note'),
    ).toContainText('我們決定先練一週看看再微調。');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-note'),
    ).toHaveCount(0);
    // Superseded-no-note resolution: the carry-forward entry that established
    // the current repair_reentry wording has no revision_note, so the primary
    // echo is absent. But an earlier manual edit on the same field carries a
    // human "why" that is still meaningfully close to the current wording.
    // The fallback chip surfaces that earlier note with explicit framing
    // (`該段後來又有微調`) and shows the note's original target wording
    // (`先各自冷靜。`) so users can tell exactly what the note described —
    // never pretending it describes the current text verbatim.
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toContainText('該段後來又有微調');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toContainText('想先試試短暫分開、但不冷處理太久。');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toContainText('先各自冷靜。');
    // Primary echo wins over fallback: when protect_what_matters' current-value
    // change itself carries a note, the earlier-note chip is suppressed
    // entirely (no duplicate "why" rendering on the same field).
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters-earlier-note'),
    ).toHaveCount(0);
    await expect(page.getByRole('link', { name: '打開 Mediation' })).toHaveAttribute('href', '/mediation');
    await expect(page.getByRole('link', { name: '打開 Support 設定' })).toHaveAttribute(
      'href',
      '/settings#settings-support',
    );

    await page
      .getByLabel('當張力升高時，我們想保護什麼')
      .fill('先保護彼此正在努力靠近這件事，不在最高點替對方定型。');
    await page
      .getByLabel('卡住或升高時，我們先避免什麼')
      .fill('不要翻舊帳，也不要在還很急的時候逼對方立刻給答案。');
    await page
      .getByLabel('要重新開啟修復時，我們怎麼回來')
      .fill('先留出一段空氣，再在 24 小時內回來，用比較慢的語氣把卡住的點說清楚。');
    // Optional revision note: the e2e covers the "note present" path. When typed, the note is
    // plumbed through the upsert payload and surfaces as the quoted chip on the new timeline entry.
    await page
      .getByTestId('relationship-heart-repair-agreements-revision-note-input')
      .fill('走過上週那次之後，我們重新寫的版本。');
    await page.getByRole('button', { name: '保存 Repair Agreements' }).click();

    await expect.poll(() => apiState.repairAgreementPayloads.length).toBe(1);
    expect(apiState.repairAgreementPayloads[0]).toEqual({
      protect_what_matters: '先保護彼此正在努力靠近這件事，不在最高點替對方定型。',
      avoid_in_conflict: '不要翻舊帳，也不要在還很急的時候逼對方立刻給答案。',
      repair_reentry: '先留出一段空氣，再在 24 小時內回來，用比較慢的語氣把卡住的點說清楚。',
      // Direct (non-carry-forward) edits send null for source_outcome_capture_id so the
      // backend records history with origin_kind="manual_edit".
      source_outcome_capture_id: null,
      revision_note: '走過上週那次之後，我們重新寫的版本。',
    });

    await expect(page.getByLabel('當張力升高時，我們想保護什麼')).toHaveValue(
      '先保護彼此正在努力靠近這件事，不在最高點替對方定型。',
    );
    await expect(page.getByLabel('卡住或升高時，我們先避免什麼')).toHaveValue(
      '不要翻舊帳，也不要在還很急的時候逼對方立刻給答案。',
    );
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(
      '先留出一段空氣，再在 24 小時內回來，用比較慢的語氣把卡住的點說清楚。',
    );
    await expect(page.getByText('已留下 3/3 個 repair agreements').first()).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-updated-by')).toContainText('Alice Chen');
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText('手動微調');
    // The note chip appears on the new entry, visible regardless of expand state.
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-note')).toContainText(
      '走過上週那次之後，我們重新寫的版本。',
    );
    // Save clears the note input so the user doesn't accidentally resubmit the same note.
    await expect(
      page.getByTestId('relationship-heart-repair-agreements-revision-note-input'),
    ).toHaveValue('');
    // Expand the newly-saved entry to read its before/after detail; "目前版本" + the new text
    // live inside the detail panel now.
    await page.getByTestId('relationship-heart-repair-agreements-history-entry-0-expand').click();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-detail')).toContainText(
      '目前版本',
    );
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-detail')).toContainText(
      '先保護彼此正在努力靠近這件事，不在最高點替對方定型。',
    );
    // After the manual-edit save, the just-written note now also echoes inside the matching
    // per-field review panel — visible adjacent to the current value so users don't have to
    // scan the timeline to understand the wording.
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters-note'),
    ).toContainText('走過上週那次之後，我們重新寫的版本。');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-note'),
    ).toContainText('走過上週那次之後，我們重新寫的版本。');
    // Primary takes over: now that the save established a new current-value
    // change on repair_reentry that itself carries a note, the earlier-note
    // fallback chip (which had surfaced the superseded earlier "why") is
    // suppressed. Only one "why" per field, attached to the exact wording.
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toHaveCount(0);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters'),
    ).toContainText('手動微調');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters'),
    ).toContainText('先保護彼此正在努力靠近這件事，不在最高點替對方定型。');

    await page.getByRole('button', { name: '標記本週任務完成' }).click();
    await expect.poll(() => apiState.weeklyTaskCompletionCount).toBe(1);
    await expect(page.getByTestId('relationship-heart-weekly-task-card').getByText('本週任務已完成')).toBeVisible();
  });

  test('edits and persists Repair Agreements on the live local stack', async ({
    page,
    context,
    request,
    baseURL,
  }) => {
    test.setTimeout(120_000);
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E !== '1',
      'Set LOVE_MAP_LIVE_E2E=1 to run against the seeded local Postgres stack.',
    );

    const authResponse = await request.post('http://127.0.0.1:8000/api/auth/token', {
      form: {
        username: 'alice@example.com',
        password: 'havendev1',
      },
    });
    expect(authResponse.ok()).toBeTruthy();
    const authPayload = (await authResponse.json()) as {
      access_token: string;
      refresh_token?: string;
    };

    await context.addCookies(
      [
        {
          name: 'access_token',
          value: authPayload.access_token,
          domain: '127.0.0.1',
          path: '/',
          httpOnly: true,
          sameSite: 'Lax',
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

    const appBaseUrl = baseURL ?? 'http://127.0.0.1:3000';
    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('relationship-heart-repair-agreements-card')).toBeVisible();
    await expect(page.getByText('我們的 Repair Agreements')).toBeVisible();

    const revisionSuffix = String(Date.now()).slice(-6);
    const nextProtectValue = `先保護彼此仍想站在同一邊這件事，不在最急的時候替對方下最後定論。${revisionSuffix}`;
    const nextAvoidValue = `不要翻舊帳，也不要在半夜還很急的時候逼對方立刻說清楚。${revisionSuffix}`;
    const nextReentryValue = `如果真的卡住，先暫停，再在 24 小時內回來用更慢的語氣說感受和需要。${revisionSuffix}`;

    await page
      .getByLabel('當張力升高時，我們想保護什麼')
      .fill(nextProtectValue);
    await page
      .getByLabel('卡住或升高時，我們先避免什麼')
      .fill(nextAvoidValue);
    await page
      .getByLabel('要重新開啟修復時，我們怎麼回來')
      .fill(nextReentryValue);
    await expect(page.getByRole('button', { name: '保存 Repair Agreements' })).toBeEnabled();
    await page.getByRole('button', { name: '保存 Repair Agreements' }).click();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('當張力升高時，我們想保護什麼')).toHaveValue(nextProtectValue);
    await expect(page.getByLabel('卡住或升高時，我們先避免什麼')).toHaveValue(nextAvoidValue);
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(nextReentryValue);
    await expect(page.getByTestId('relationship-heart-repair-agreements-updated-by')).toContainText('Alice');
    await expect(page.getByTestId('relationship-heart-repair-agreements-history')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText('手動微調');
    // Expand entry 0 so the newly-persisted before/after text is reachable in the timeline
    // detail panel (which is collapsed by default on the live stack as well).
    await page.getByTestId('relationship-heart-repair-agreements-history-entry-0-expand').click();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0-detail')).toContainText(
      nextProtectValue,
    );
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters'),
    ).toContainText(nextProtectValue);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-protect_what_matters'),
    ).toContainText('目前版本');

    const primaryNoteReentryValue = `先各自冷靜，再約定一個能回來說話的時間。${revisionSuffix}`;
    const primaryNoteText = `想先試試短暫分開、但不要讓它變成冷處理。${revisionSuffix}`;
    await page
      .getByLabel('要重新開啟修復時，我們怎麼回來')
      .fill(primaryNoteReentryValue);
    await page
      .getByTestId('relationship-heart-repair-agreements-revision-note-input')
      .fill(primaryNoteText);
    await expect(page.getByRole('button', { name: '保存 Repair Agreements' })).toBeEnabled();
    await page.getByRole('button', { name: '保存 Repair Agreements' }).click();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(primaryNoteReentryValue);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-note'),
    ).toContainText(primaryNoteText);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toHaveCount(0);

    const supersedingReentryValue = `如果又卡住，先暫停，再在隔天晚餐前用更慢的語氣回來。${revisionSuffix}`;
    await page
      .getByLabel('要重新開啟修復時，我們怎麼回來')
      .fill(supersedingReentryValue);
    await expect(
      page.getByTestId('relationship-heart-repair-agreements-revision-note-input'),
    ).toHaveValue('');
    await expect(page.getByRole('button', { name: '保存 Repair Agreements' })).toBeEnabled();
    await page.getByRole('button', { name: '保存 Repair Agreements' }).click();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(supersedingReentryValue);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-note'),
    ).toHaveCount(0);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toContainText('該段後來又有微調');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toContainText(primaryNoteText);
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry-earlier-note'),
    ).toContainText(primaryNoteReentryValue);

    const mediationHref = await page.getByRole('link', { name: '打開 Mediation' }).getAttribute('href');
    expect(mediationHref).toBe('/mediation');
    await page.goto(`${appBaseUrl}${mediationHref}`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/mediation$/);

    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    const supportHref = await page.getByRole('link', { name: '打開 Support 設定' }).getAttribute('href');
    expect(supportHref).toBe('/settings#settings-support');
    await page.goto(`${appBaseUrl}${supportHref}`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/settings#settings-support$/);
  });
});
