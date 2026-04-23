import { expect, test, type Route } from '@playwright/test';

const MOCK_API_HEADERS = {
  'access-control-allow-origin': 'http://127.0.0.1:3000',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
};
const API_ORIGIN = '**/api';

function hoursAgo(now: number, hours: number) {
  return new Date(now - hours * 60 * 60 * 1000).toISOString();
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: MOCK_API_HEADERS,
    body: JSON.stringify(data),
  });
}

test.describe('Analysis understanding center', () => {
  test.use({ bypassCSP: true });

  test('turns current relationship data into useful derived insight', async ({ page }) => {
    test.skip(
      process.env.ANALYSIS_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Analysis spec.',
    );

    const now = Date.now();
    const myJournals = [
      {
        id: 'mine-1',
        user_id: 'me',
        content: '今天其實有點累，也怕一開口又變成防禦。',
        created_at: hoursAgo(now, 18),
        mood_label: '疲憊',
        mood_score: 42,
        emotional_needs: '我需要先被理解，而不是立刻被糾正。',
        advice_for_user: '先承認自己的疲累，再開始對話。',
        action_for_user: '今晚先留 10 分鐘只談感受，不談解法。',
        safety_tier: 1,
      },
      {
        id: 'mine-2',
        user_id: 'me',
        content: '但我也有感覺到對方其實有在努力。',
        created_at: hoursAgo(now, 72),
        mood_label: '感激',
        mood_score: 68,
        emotional_needs: '我需要被看見努力也同時被安撫。',
        advice_for_user: '把感謝說得更具體。',
        action_for_user: '先說一件今天真心感謝的事。',
        safety_tier: 0,
      },
    ];

    const partnerJournals = [
      {
        id: 'partner-1',
        user_id: 'partner',
        content: '最近我需要更多安全感，不然很容易先縮回去。',
        created_at: hoursAgo(now, 10),
        mood_label: '不安',
        mood_score: 38,
        emotional_needs: '我需要安全感和更慢一點的回應。',
        advice_for_user: '先用更柔和的語氣。',
        action_for_user: '把真正擔心的是什麼說出來。',
        safety_tier: 0,
      },
      {
        id: 'partner-2',
        user_id: 'partner',
        content: '其實我也想重新靠近，只是不知道怎麼開口。',
        created_at: hoursAgo(now, 96),
        mood_label: '想靠近',
        mood_score: 61,
        emotional_needs: '我需要一個不會立刻變成爭執的入口。',
        advice_for_user: '從比較小的問題重新開始。',
        action_for_user: '先說今天最想被理解的一件事。',
        safety_tier: 0,
      },
    ];

    await page.route(`${API_ORIGIN}/**`, async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: MOCK_API_HEADERS,
        });
        return;
      }

      const pathname = new URL(route.request().url()).pathname;
      if (pathname.startsWith('/api/journals/')) {
        await fulfillJson(route, []);
        return;
      }

      await fulfillJson(route, {});
    });

    await page.route(`${API_ORIGIN}/auth/token`, async (route) => {
      await fulfillJson(route, {
        access_token: 'analysis-test-token',
        token_type: 'bearer',
      });
    });

    await page.route(`${API_ORIGIN}/users/me**`, async (route) => {
      await fulfillJson(route, {
        id: 'user-1',
        email: 'analysis@example.com',
        full_name: 'Analysis User',
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Partner',
        partner_nickname: 'P',
        savings_score: 58,
        created_at: hoursAgo(now, 500),
      });
    });

    await page.route(`${API_ORIGIN}/users/partner-status`, async (route) => {
      await fulfillJson(route, {
        has_partner: true,
        latest_journal_at: partnerJournals[0].created_at,
        current_score: 58,
        unread_notification_count: 2,
      });
    });

    await page.route(`${API_ORIGIN}/journals/**`, async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname.endsWith('/partner')) {
        await fulfillJson(route, partnerJournals);
        return;
      }
      await fulfillJson(route, myJournals);
    });

    await page.route(`${API_ORIGIN}/daily-sync/status`, async (route) => {
      await fulfillJson(route, {
        today: '2026-03-15',
        my_filled: false,
        partner_filled: true,
        unlocked: true,
        my_mood_score: null,
        my_question_id: null,
        my_answer_text: null,
        partner_mood_score: 4,
        partner_question_id: 'q-1',
        partner_answer_text: '我希望今天的對話慢一點。',
        today_question_id: 'q-1',
        today_question_label: '今天最想被理解的是什麼？',
      });
    });

    await page.route(`${API_ORIGIN}/reports/weekly`, async (route) => {
      await fulfillJson(route, {
        period_start: '2026-03-09',
        period_end: '2026-03-15',
        daily_sync_completion_rate: 0.43,
        daily_sync_days_filled: 3,
        appreciation_count: 2,
        insight: '這週的連結還在，但更需要被刻意照顧，而不是等情緒自己變好。',
        partner_daily_sync_days_filled: 4,
        pair_sync_overlap_days: 2,
        pair_sync_alignment_rate: 0.29,
      });
    });

    await page.route(`${API_ORIGIN}/memory/report**`, async (route) => {
      await fulfillJson(route, {
        period: 'month',
        from_date: '2026-02-15',
        to_date: '2026-03-15',
        emotion_trend_summary: '最近你們其實都有想靠近的動機，但更常在安全感不足時先縮回去。',
        top_topics: ['修復', '安全感', '重新靠近'],
        health_suggestion: '先從一段低壓力、只談感受不談對錯的十分鐘開始。',
        generated_at: hoursAgo(now, 6),
      });
    });

    await page.route(`${API_ORIGIN}/love-map/system`, async (route) => {
      await fulfillJson(route, {
        has_partner: true,
        me: {
          id: 'me',
          full_name: 'Analysis User',
          email: 'analysis@example.com',
        },
        partner: {
          id: 'partner-1',
          partner_name: 'Partner',
        },
        baseline: {
          mine: null,
          partner: null,
        },
        couple_goal: null,
        relationship_compass: {
          identity_statement: '我們是在忙裡仍願意回來對話的伴侶。',
          story_anchor: '想一起記得那些有走回彼此的時刻。',
          future_direction: '接下來一起靠近更穩定的週末節奏。',
          updated_by_name: 'Analysis User',
          updated_at: hoursAgo(now, 8),
        },
        relationship_compass_history: [],
        story: {
          available: true,
          moments: [
            {
              kind: 'appreciation',
              title: '謝謝你把語氣放慢',
              description: '被明確說出口的好事。',
              occurred_at: hoursAgo(now, 22),
              badges: ['Appreciation'],
              why_text: '這是最近正在撐住關係的連結證據。',
              source_id: '11',
            },
          ],
          time_capsule: null,
        },
        notes: [],
        wishlist_items: [
          {
            id: 'wish-1',
            title: '週末慢慢散步',
            notes: '把對話放慢。',
            created_at: hoursAgo(now, 70),
            added_by_me: true,
          },
        ],
        stats: {
          filled_note_layers: 0,
          baseline_ready_mine: false,
          baseline_ready_partner: false,
          wishlist_count: 1,
          last_activity_at: hoursAgo(now, 8),
        },
        essentials: {
          my_care_preferences: null,
          partner_care_preferences: null,
          my_care_profile: {
            support_me: '先用柔和語氣問我需不需要一點時間。',
            avoid_when_stressed: '不要立刻分析對錯。',
            small_delights: '幫我留一杯熱茶。',
            updated_at: hoursAgo(now, 12),
          },
          partner_care_profile: {
            support_me: '先讓我安靜十分鐘。',
            avoid_when_stressed: '不要急著追問。',
            small_delights: '把餐桌收乾淨。',
            updated_at: hoursAgo(now, 14),
          },
          repair_agreements: {
            protect_what_matters: '先保護彼此的安全感。',
            avoid_in_conflict: '避免翻舊帳或替對方下結論。',
            repair_reentry: '24 小時內用較慢語氣回來。',
            updated_by_name: 'Analysis User',
            updated_at: hoursAgo(now, 9),
          },
          repair_agreement_history: [],
          pending_repair_outcome_capture: null,
          weekly_task: {
            task_slug: 'slow-check-in',
            task_label: '一起完成一段十分鐘低壓力 check-in。',
            assigned_at: hoursAgo(now, 30),
            completed: false,
            completed_at: null,
          },
        },
      });
    });

    await page.route(`${API_ORIGIN}/appreciations**`, async (route) => {
      const url = new URL(route.request().url());
      if (url.searchParams.has('from_date')) {
        await fulfillJson(route, [
          {
            id: 11,
            body_text: '謝謝你昨天願意先說出自己的真實感受，讓我不用一直猜。',
            created_at: hoursAgo(now, 22),
          },
          {
            id: 12,
            body_text: '我有感覺到你今天刻意把語氣放慢，這讓我安心很多。',
            created_at: hoursAgo(now, 44),
          },
        ]);
        return;
      }

      await fulfillJson(route, [
        {
          id: 11,
          body_text: '謝謝你昨天願意先說出自己的真實感受，讓我不用一直猜。',
          created_at: hoursAgo(now, 22),
        },
        {
          id: 12,
          body_text: '我有感覺到你今天刻意把語氣放慢，這讓我安心很多。',
          created_at: hoursAgo(now, 44),
        },
        {
          id: 13,
          body_text: '你有記得回來確認我的狀態，這對我真的很重要。',
          created_at: hoursAgo(now, 88),
        },
      ]);
    });

    await page.goto('/analysis');

    await expect(page.getByRole('heading', { level: 1, name: '把最近的互動，翻成更深的理解。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '最近比較容易錯開彼此的節奏' })).toBeVisible();
    await expect(page.getByText('本週同步 43%')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '值得你們優先照看的地方' })).toBeVisible();
    await expect(page.getByText('最近的情緒張力偏高，先顧安全感再談內容').first()).toBeVisible();
    await expect(page.getByText('有一些訊號還在等待被接住')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '正在替你們撐住關係的好事' })).toBeVisible();
    await expect(page.getByText('感謝有被說出來，而不是只停在心裡').first()).toBeVisible();
    await expect(page.getByText('雙方最近都有留下自己的痕跡')).toBeVisible();
    await expect(page.getByText('最近你們反覆回到「修復」')).toBeVisible();
    await expect(page.getByText('安全感', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('最近比較常浮出的需要')).toBeVisible();
    await expect(page.getByText('我需要安全感和更慢一點的回應。')).toBeVisible();
    await expect(page.getByRole('link', { name: '回到今天同步' }).first()).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把判讀拆回真正的依據' })).toBeVisible();
    await expect(page.getByTestId('analysis-v2-brief')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '這週的關係讀法' })).toBeVisible();
    await expect(page.getByTestId('analysis-v2-brief-card-current')).toContainText('我們最近怎麼樣');
    await expect(page.getByTestId('analysis-v2-brief-card-strength')).toContainText('什麼正在撐住我們');
    await expect(page.getByTestId('analysis-v2-brief-card-attention')).toContainText('哪裡需要先照顧');
    await expect(page.getByTestId('analysis-v2-brief-card-direction')).toContainText('下一步往哪裡靠近');
    await expect(page.getByTestId('analysis-v2-brief-card-strength')).toContainText('Relationship Compass');
    await expect(page.getByTestId('analysis-v2-brief-card-strength')).toContainText('想一起記得那些有走回彼此的時刻。');
    await expect(page.getByTestId('analysis-v2-brief-card-attention')).toContainText('Repair Agreements');
    await expect(page.getByTestId('analysis-v2-brief-card-attention')).toContainText('3/3 個 Repair Agreements');
    await expect(page.getByTestId('analysis-v2-brief-card-direction')).toContainText('Relationship Compass');
    await expect(page.getByTestId('analysis-v2-brief-card-direction')).toContainText('接下來一起靠近更穩定的週末節奏。');

    await page
      .getByTestId('analysis-v2-brief-card-attention')
      .getByRole('button', { name: '查看修復依據' })
      .click();
    const briefEvidencePanel = page.getByTestId('analysis-evidence-panel');
    await expect(
      briefEvidencePanel.getByRole('heading', { level: 3, name: '最近需要先照顧安全感的地方' }),
    ).toBeVisible();

    await page
      .locator('section')
      .filter({
        has: page.getByRole('heading', { level: 2, name: '值得你們優先照看的地方' }),
      })
      .getByRole('button', { name: '查看依據' })
      .first()
      .click();

    const evidencePanel = page.getByTestId('analysis-evidence-panel');
    await expect(
      evidencePanel.getByRole('heading', { level: 3, name: '最近需要先照顧安全感的地方' }),
    ).toBeVisible();
    await expect(evidencePanel.getByText('高張力片段')).toBeVisible();
    await expect(
      evidencePanel.getByText('我需要先被理解，而不是立刻被糾正。'),
    ).toBeVisible();

    await page.getByRole('button', { name: '展開雙方模式依據' }).nth(1).click();
    await expect(
      evidencePanel.getByRole('heading', {
        level: 3,
        name: '你最近更常從「疲憊」進入，伴侶更常從「不安」進入',
      }),
    ).toBeVisible();
    await expect(evidencePanel.getByText('月度主題 · 修復 · 安全感 · 重新靠近')).toBeVisible();

    await page
      .locator('section')
      .filter({
        has: page.getByRole('heading', { level: 2, name: '正在替你們撐住關係的好事' }),
      })
      .getByRole('button', { name: '查看依據' })
      .first()
      .click();

    await expect(
      evidencePanel.getByRole('heading', {
        level: 3,
        name: '好事有被明確說出口，而不是只默默放在心裡',
      }),
    ).toBeVisible();
    await expect(
      evidencePanel.getByText('謝謝你昨天願意先說出自己的真實感受，讓我不用一直猜。'),
    ).toBeVisible();
  });

  test('renders the Analysis V2 brief on the live local stack', async ({ page, context, request, baseURL }) => {
    test.setTimeout(90_000);
    test.skip(
      process.env.ANALYSIS_LIVE_E2E !== '1',
      'Set ANALYSIS_LIVE_E2E=1 to run against the seeded local Postgres stack.',
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
    await page.goto(`${appBaseUrl}/analysis`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('analysis-v2-brief')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '這週的關係讀法' })).toBeVisible();
    await expect(page.getByTestId('analysis-v2-brief-card-current')).toContainText('我們最近怎麼樣');
    await expect(page.getByTestId('analysis-v2-brief-card-strength')).toContainText('什麼正在撐住我們');
    await expect(page.getByTestId('analysis-v2-brief-card-attention')).toContainText('哪裡需要先照顧');
    await expect(page.getByTestId('analysis-v2-brief-card-direction')).toContainText('下一步往哪裡靠近');
    await expect(page.getByTestId('analysis-v2-brief-card-direction')).toContainText('Relationship Compass');
    await expect(page.getByTestId('analysis-v2-brief-card-direction')).toContainText('更穩定的週末節奏');
    await expect(page.getByText('Repair Agreements').first()).toBeVisible();
    await expect(page.getByText('TRANSLATED PARTNER MARKER')).toHaveCount(0);

    const currentAction = page.getByTestId('analysis-v2-brief-card-current').getByRole('button').first();
    await currentAction.click();
    await expect(page.getByTestId('analysis-evidence-panel')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把判讀拆回真正的依據' })).toBeVisible();
  });
});
