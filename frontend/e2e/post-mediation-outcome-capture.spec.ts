import { expect, test, type APIRequestContext, type Page, type Route } from '@playwright/test';

const REPAIR_SESSION_STORAGE_KEY = 'haven_repair_flow_session_id_v1';

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

function apiSuccess(data: unknown, requestId = 'post-mediation-outcome-capture-e2e-req') {
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

async function mockOutcomeCaptureApi(page: Page) {
  await page.context().addCookies([
    { name: 'access_token', value: 'post-mediation-mock-token', url: 'http://127.0.0.1:3000' },
    { name: 'access_token', value: 'post-mediation-mock-token', url: 'http://localhost:8000' },
  ]);

  const now = Date.now();
  const savePayloads: Array<Record<string, unknown>> = [];
  const dismissPayloads: string[] = [];
  let repairAgreementHistorySequence = 1;

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

  const pendingCapture = {
    id: 'capture-1',
    repair_session_id: 'repair-session-1',
    shared_commitment: '今晚先散步十分鐘，再回來把需要說清楚。',
    improvement_note: '這次我們比較能先停下來，再慢慢把話說完。',
    status: 'pending',
    captured_by_name: 'Bob',
    created_at: new Date(now - 10 * 60 * 1000).toISOString(),
    updated_at: new Date(now - 5 * 60 * 1000).toISOString(),
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
        protect_what_matters: '先保護彼此仍想站在同一邊這件事。',
        avoid_in_conflict: '不要在最高張力時逼對方立刻回答。',
        repair_reentry: '先留一段空氣，再在 24 小時內回來把感受與需要說清楚。',
        updated_by_name: 'Alice Chen',
        updated_at: new Date(now - 11 * 60 * 60 * 1000).toISOString(),
      },
      repair_agreement_history: [
        {
          id: 'repair-history-seeded-1',
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
              after_text: '先保護彼此仍想站在同一邊這件事。',
            },
          ],
        },
      ],
      pending_repair_outcome_capture: pendingCapture,
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
        source_outcome_capture_id?: string | null;
      };
      savePayloads.push(payload);
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
      system.essentials.repair_agreement_history.unshift({
        id: `repair-history-carry-forward-${repairAgreementHistorySequence}`,
        changed_at: system.essentials.repair_agreements.updated_at,
        changed_by_name: system.me.full_name,
        origin_kind: payload.source_outcome_capture_id ? 'post_mediation_carry_forward' : 'manual_edit',
        source_outcome_capture_id: payload.source_outcome_capture_id ?? null,
        source_captured_by_name: payload.source_outcome_capture_id ? pendingCapture.captured_by_name : null,
        source_captured_at: payload.source_outcome_capture_id ? pendingCapture.updated_at : null,
        fields: buildFieldChanges(previousRepairAgreements, system.essentials.repair_agreements),
      });
      repairAgreementHistorySequence += 1;
      system.essentials.repair_agreement_history = system.essentials.repair_agreement_history.slice(0, 5);
      if (payload.source_outcome_capture_id === pendingCapture.id) {
        system.essentials.pending_repair_outcome_capture = null;
      }
      system.stats.last_activity_at = system.essentials.repair_agreements.updated_at;
      await fulfillJson(route, system.essentials.repair_agreements);
      return;
    }

    if (
      path.endsWith(`/love-map/essentials/repair-outcome-captures/${pendingCapture.id}/dismiss`)
      && method === 'POST'
    ) {
      dismissPayloads.push(pendingCapture.id);
      system.essentials.pending_repair_outcome_capture = null;
      await fulfillJson(route, {
        ...pendingCapture,
        status: 'dismissed',
        updated_at: new Date().toISOString(),
      });
      return;
    }

    await fulfillJson(route, {});
  };

  await page.route('**/api/**', apiHandler);

  return {
    savePayloads,
    dismissPayloads,
    pendingCapture,
  };
}

async function loginForAccessToken(
  request: APIRequestContext,
  username: string,
  password: string,
) {
  const response = await request.post('http://127.0.0.1:8000/api/auth/token', {
    form: { username, password },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as {
    access_token: string;
    refresh_token?: string;
  };
}

async function completeRepairFlowV1(
  request: APIRequestContext,
  aliceAccessToken: string,
  bobAccessToken: string,
) {
  const readHeaders = (token: string) => ({
    Authorization: `Bearer ${token}`,
  });

  const postHeaders = (token: string, idempotencyKey: string) => ({
    ...readHeaders(token),
    'Content-Type': 'application/json',
    'Idempotency-Key': idempotencyKey,
  });

  const startResponse = await request.post('http://127.0.0.1:8000/api/mediation/repair/start', {
    headers: postHeaders(
      aliceAccessToken,
      `repair-start-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    ),
    data: { source: 'web' },
  });
  expect(startResponse.ok()).toBeTruthy();
  const sessionId = (await startResponse.json()).session_id as string;

  const sharedCommitment =
    `今晚先散步十分鐘，再回來用比較慢的語氣把需要說清楚。${String(Date.now()).slice(-6)}`;
  const improvementNote =
    `這次我們有先停下來，再回來把承諾講清楚。${String(Date.now()).slice(-6)}`;

  const stepCalls: Array<{
    token: string;
    body: Record<string, string | number>;
  }> = [
    {
      token: aliceAccessToken,
      body: {
        session_id: sessionId,
        step: 2,
        i_feel: '我很受傷。',
        i_need: '我需要先被聽完。',
      },
    },
    {
      token: bobAccessToken,
      body: {
        session_id: sessionId,
        step: 2,
        i_feel: '我也很挫折。',
        i_need: '我需要先不要被打斷。',
      },
    },
    {
      token: aliceAccessToken,
      body: {
        session_id: sessionId,
        step: 3,
        mirror_text: '我聽見你需要我先把節奏放慢。',
      },
    },
    {
      token: bobAccessToken,
      body: {
        session_id: sessionId,
        step: 3,
        mirror_text: '我聽見你需要先被完整聽完。',
      },
    },
    {
      token: aliceAccessToken,
      body: {
        session_id: sessionId,
        step: 4,
        shared_commitment: '今晚先散步十分鐘，再回來把需要說清楚。',
      },
    },
    {
      token: bobAccessToken,
      body: {
        session_id: sessionId,
        step: 4,
        shared_commitment: sharedCommitment,
      },
    },
    {
      token: aliceAccessToken,
      body: {
        session_id: sessionId,
        step: 5,
        improvement_note: '我這次有先把你的句子聽完。',
      },
    },
    {
      token: bobAccessToken,
      body: {
        session_id: sessionId,
        step: 5,
        improvement_note: improvementNote,
      },
    },
  ];

  for (const stepCall of stepCalls) {
    const response = await request.post('http://127.0.0.1:8000/api/mediation/repair/step-complete', {
      headers: postHeaders(
        stepCall.token,
        `repair-step-${stepCall.body.step}-${sessionId}-${Math.random().toString(36).slice(2, 10)}`,
      ),
      data: stepCall.body,
    });
    expect(response.ok()).toBeTruthy();
  }

  const statusResponse = await request.get('http://127.0.0.1:8000/api/mediation/repair/status', {
    headers: readHeaders(aliceAccessToken),
    params: { session_id: sessionId },
  });
  expect(statusResponse.ok()).toBeTruthy();
  const statusPayload = await statusResponse.json();
  expect(statusPayload.completed).toBeTruthy();
  expect(statusPayload.outcome_capture_pending).toBeTruthy();

  return {
    sessionId,
    sharedCommitment,
  };
}

test.describe('Post-mediation outcome capture', () => {
  test.use({ bypassCSP: true });

  test('reviews and applies a pending repair outcome in mocked mode', async ({ page }) => {
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked post-mediation capture apply spec.',
    );

    const apiState = await mockOutcomeCaptureApi(page);
    await page.goto('/love-map');

    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toBeVisible();
    await expect(page.getByText(apiState.pendingCapture.shared_commitment)).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText('手動微調');

    await page.getByRole('button', { name: '帶入 Repair Agreements' }).click();
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(
      apiState.pendingCapture.shared_commitment,
    );

    await page.getByRole('button', { name: '保存 Repair Agreements' }).click();

    await expect.poll(() => apiState.savePayloads.length).toBe(1);
    expect(apiState.savePayloads[0]).toEqual({
      protect_what_matters: '先保護彼此仍想站在同一邊這件事。',
      avoid_in_conflict: '不要在最高張力時逼對方立刻回答。',
      repair_reentry: apiState.pendingCapture.shared_commitment,
      source_outcome_capture_id: apiState.pendingCapture.id,
    });

    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toHaveCount(0);
    await page.reload();
    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toHaveCount(0);
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(
      apiState.pendingCapture.shared_commitment,
    );
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText(
      '修復帶回',
    );
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText(
      apiState.pendingCapture.shared_commitment,
    );
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry'),
    ).toContainText('修復帶回');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry'),
    ).toContainText(apiState.pendingCapture.shared_commitment);
  });

  test('dismisses a pending repair outcome in mocked mode', async ({ page }) => {
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked post-mediation capture dismiss spec.',
    );

    const apiState = await mockOutcomeCaptureApi(page);
    await page.goto('/love-map');

    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toBeVisible();
    await page.getByRole('button', { name: '暫時不帶回' }).click();

    await expect.poll(() => apiState.dismissPayloads.length).toBe(1);
    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toHaveCount(0);
  });

  test('carries a completed repair flow back into Heart on the live local stack', async ({
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

    const aliceAuth = await loginForAccessToken(request, 'alice@example.com', 'havendev1');
    const bobAuth = await loginForAccessToken(request, 'bob@example.com', 'havendev1');
    const completedFlow = await completeRepairFlowV1(
      request,
      aliceAuth.access_token,
      bobAuth.access_token,
    );

    await context.addCookies(
      [
        {
          name: 'access_token',
          value: aliceAuth.access_token,
          domain: '127.0.0.1',
          path: '/',
          httpOnly: true,
          sameSite: 'Lax',
        },
        aliceAuth.refresh_token
          ? {
              name: 'refresh_token',
              value: aliceAuth.refresh_token,
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
    await page.goto(`${appBaseUrl}/mediation`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(
      ({ sessionKey, sessionId }) => {
        window.localStorage.setItem(sessionKey, sessionId);
      },
      {
        sessionKey: REPAIR_SESSION_STORAGE_KEY,
        sessionId: completedFlow.sessionId,
      },
    );
    await page.reload({ waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('link', { name: '把這次修復帶回關係系統' })).toBeVisible();
    await page.getByRole('link', { name: '把這次修復帶回關係系統' }).click();

    await expect(page).toHaveURL(/\/love-map#heart$/);
    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toBeVisible();
    await expect(page.getByText(completedFlow.sharedCommitment)).toBeVisible();

    await page.getByRole('button', { name: '帶入 Repair Agreements' }).click();
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(
      completedFlow.sharedCommitment,
    );

    await page.getByRole('button', { name: '保存 Repair Agreements' }).click();
    await expect(page.getByTestId('relationship-heart-post-mediation-outcome-card')).toHaveCount(0);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('要重新開啟修復時，我們怎麼回來')).toHaveValue(
      completedFlow.sharedCommitment,
    );
    await expect(page.getByTestId('relationship-heart-repair-agreements-updated-by')).toContainText('Alice');
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText(
      '修復帶回',
    );
    await expect(page.getByTestId('relationship-heart-repair-agreements-history-entry-0')).toContainText(
      completedFlow.sharedCommitment,
    );
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry'),
    ).toContainText('修復帶回');
    await expect(
      page.getByTestId('relationship-heart-repair-field-review-repair_reentry'),
    ).toContainText(completedFlow.sharedCommitment);
  });
});
