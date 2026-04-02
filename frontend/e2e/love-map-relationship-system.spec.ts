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

function apiSuccess(data: unknown, requestId = 'love-map-v1-e2e-req') {
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

async function mockLoveMapApi(page: Page) {
  await page.context().addCookies([
    { name: 'access_token', value: 'love-map-mock-token', url: 'http://127.0.0.1:3000' },
    { name: 'access_token', value: 'love-map-mock-token', url: 'http://localhost:8000' },
  ]);

  const now = Date.now();
  const baselinePayloads: Array<Record<string, unknown>> = [];
  const goalPayloads: Array<Record<string, unknown>> = [];
  const notePayloads: Array<Record<string, unknown>> = [];
  const wishlistPayloads: Array<Record<string, unknown>> = [];
  const generatedSuggestionCalls: Array<Record<string, unknown>> = [];
  const generatedRefinementCalls: string[] = [];
  const generatedCadenceRefinementCalls: string[] = [];
  const generatedRefinementCallCounts: Record<string, number> = {};
  const acceptedSuggestionIds: string[] = [];
  const dismissedSuggestionIds: string[] = [];
  const acceptedRefinementIds: string[] = [];
  const dismissedRefinementIds: string[] = [];

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
        filled_at: new Date(now - 22 * 60 * 60 * 1000).toISOString(),
        scores: {
          intimacy: 4,
          conflict: 3,
          trust: 4,
          communication: 4,
          commitment: 5,
        },
      },
    },
    couple_goal: {
      goal_slug: 'better_communication',
      chosen_at: new Date(now - 18 * 60 * 60 * 1000).toISOString(),
    },
    story: {
      available: true,
      moments: [
        {
          kind: 'appreciation',
          source_id: 'appreciation-1',
          title: '一段被說出口的感謝',
          description: '謝謝你每天早上幫我準備咖啡，這個小習慣讓我每天都很期待起床。',
          occurred_at: new Date(now - 72 * 60 * 60 * 1000).toISOString(),
          badges: ['感恩'],
          why_text: '感謝被留下來時，不只是訊息紀錄，也會變成你們故事裡可回頭看的證據。',
        },
        {
          kind: 'card',
          source_id: 'session-1',
          title: '今天能量',
          description: '如果把你今天的狀態形容成一種天氣，那是晴天、陰天還是暴風雨？為什麼？',
          occurred_at: new Date(now - 96 * 60 * 60 * 1000).toISOString(),
          badges: ['daily_vibe', '雙方都回答了'],
          why_text: '這是一段真的被兩個人一起回答過的對話，不是 Haven 替你們補寫的詮釋。',
        },
        {
          kind: 'journal',
          source_id: 'journal-1',
          title: '☕ 溫暖',
          description: '一年前的今天，我們第一次一起去了那間隱藏在巷子裡的咖啡廳。',
          occurred_at: new Date(now - 365 * 24 * 60 * 60 * 1000).toISOString(),
          badges: ['我寫下', '有照片'],
          why_text: '這是當時真的被寫下或拍下的一刻，不代表整段關係的本質，只代表它曾經重要到值得被留下。',
        },
      ],
      time_capsule: {
        summary_text: '一年前的這幾天（3/21 – 3/27）：1 則日記、1 則共同卡片回憶、1 則感恩。',
        from_date: '2025-03-21',
        to_date: '2025-03-27',
        journals_count: 1,
        cards_count: 1,
        appreciations_count: 1,
      },
    },
    notes: [
      {
        id: 'note-safe',
        layer: 'safe',
        content: '我知道我們最近需要更穩定的回來對話節奏。',
        created_at: new Date(now - 20 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date(now - 10 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: 'note-medium',
        layer: 'medium',
        content: '我希望忙的時候不要只剩下待辦，也還記得彼此在意的是什麼。',
        created_at: new Date(now - 16 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date(now - 8 * 60 * 60 * 1000).toISOString(),
      },
    ],
    wishlist_items: [
      {
        id: 'wish-1',
        title: '每個月留一晚只屬於我們',
        notes: '先把那一晚留給散步和晚餐。',
        created_at: new Date(now - 30 * 60 * 60 * 1000).toISOString(),
        added_by_me: true,
      },
      {
        id: 'wish-2',
        title: '一起去京都看秋天',
        notes: '想慢慢走巷子和神社。',
        created_at: new Date(now - 28 * 60 * 60 * 1000).toISOString(),
        added_by_me: false,
      },
      {
        id: 'wish-3',
        title: '建立我們的衝突後修復儀式',
        notes: '希望每次明顯爭執後，都能慢慢回到同一邊。',
        created_at: new Date(now - 26 * 60 * 60 * 1000).toISOString(),
        added_by_me: true,
      },
    ],
    stats: {
      filled_note_layers: 2,
      baseline_ready_mine: true,
      baseline_ready_partner: true,
      wishlist_count: 3,
      last_activity_at: new Date(now - 8 * 60 * 60 * 1000).toISOString(),
    },
  };

  const cards = {
    safe: [
      {
        id: 'card-safe-1',
        title: '安心時刻',
        description: '描述最近一個讓你感到被接住的片刻。',
        question: '最近哪個小小的舉動，讓你覺得被放在心上？',
        depth_level: 1,
        layer: 'safe',
      },
    ],
    medium: [
      {
        id: 'card-medium-1',
        title: '壓力怎麼被理解',
        description: '談談忙碌時真正需要的是什麼。',
        question: '當你最近壓力很大時，你最希望對方先做什麼？',
        depth_level: 2,
        layer: 'medium',
      },
    ],
    deep: [
      {
        id: 'card-deep-1',
        title: '更深的期待',
        description: '讓核心期待有地方被看見。',
        question: '有什麼長久的期待，是你最近更想被對方理解的？',
        depth_level: 3,
        layer: 'deep',
      },
    ],
  };

  let pendingSuggestions: Array<{
    id: string;
    section: string;
    status: string;
    generator_version: string;
    proposed_title: string;
    proposed_notes: string;
    evidence: Array<{
      source_kind: string;
      source_id: string;
      label: string;
      excerpt: string;
    }>;
    created_at: string;
    reviewed_at: string | null;
    target_wishlist_item_id: string | null;
    accepted_wishlist_item_id: string | null;
  }> = [];

  let pendingRefinements: Array<{
    id: string;
    section: string;
    status: string;
    generator_version: string;
    proposed_title: string;
    proposed_notes: string;
    evidence: Array<{
      source_kind: string;
      source_id: string;
      label: string;
      excerpt: string;
    }>;
    created_at: string;
    reviewed_at: string | null;
    target_wishlist_item_id: string | null;
    accepted_wishlist_item_id: string | null;
  }> = [];

  const apiHandler = async (route: Route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;
    const normalizedPath = path.replace(/\/+$/, '') || '/';

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: resolveMockApiHeaders(route) });
      return;
    }

    if (path.includes('/auth/token') && method === 'POST') {
      await fulfillJson(route, {
        access_token: 'love-map-mock-token',
        token_type: 'bearer',
      });
      return;
    }

    if (path.includes('/users/me') && method === 'GET') {
      await fulfillJson(route, {
        id: 'me',
        email: 'alice@example.com',
        full_name: 'Alice Chen',
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

    if (path.endsWith('/love-map/suggestions/shared-future') && method === 'GET') {
      await fulfillJson(route, pendingSuggestions);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future/refinements') && method === 'GET') {
      await fulfillJson(route, pendingRefinements);
      return;
    }

    if (path.endsWith('/love-map/cards') && method === 'GET') {
      await fulfillJson(route, cards);
      return;
    }

    if (path.endsWith('/baseline') && method === 'POST') {
      const payload = route.request().postDataJSON() as { scores: Record<string, number> };
      baselinePayloads.push(payload);
      system.baseline.mine = {
        ...system.baseline.mine,
        filled_at: new Date().toISOString(),
        scores: payload.scores,
      };
      await fulfillJson(route, system.baseline.mine, 201);
      return;
    }

    if (path.endsWith('/couple-goal') && method === 'POST') {
      const payload = route.request().postDataJSON() as { goal_slug: string };
      goalPayloads.push(payload);
      system.couple_goal = {
        goal_slug: payload.goal_slug,
        chosen_at: new Date().toISOString(),
      };
      await fulfillJson(route, system.couple_goal, 201);
      return;
    }

    if (path.endsWith('/love-map/notes') && method === 'POST') {
      const payload = route.request().postDataJSON() as { layer: string; content: string };
      notePayloads.push(payload);
      const nextNote = {
        id: `note-${payload.layer}`,
        layer: payload.layer,
        content: payload.content,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      system.notes = [
        ...system.notes.filter((note) => note.layer !== payload.layer),
        nextNote,
      ];
      system.stats.filled_note_layers = system.notes.filter((note) => note.content.trim().length > 0).length;
      system.stats.last_activity_at = nextNote.updated_at;
      await fulfillJson(route, nextNote);
      return;
    }

    if (normalizedPath.endsWith('/blueprint') && method === 'POST') {
      const payload = route.request().postDataJSON() as { title: string; notes: string };
      wishlistPayloads.push(payload);
      const nextWish = {
        id: `wish-${system.wishlist_items.length + 1}`,
        title: payload.title,
        notes: payload.notes,
        created_at: new Date().toISOString(),
        added_by_me: true,
      };
      system.wishlist_items = [nextWish, ...system.wishlist_items];
      system.stats.wishlist_count = system.wishlist_items.length;
      system.stats.last_activity_at = nextWish.created_at;
      await fulfillJson(route, nextWish);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future/generate') && method === 'POST') {
      generatedSuggestionCalls.push({});
      if (generatedSuggestionCalls.length === 1) {
        pendingSuggestions = [
          {
            id: 'suggestion-1',
            section: 'shared_future',
            status: 'pending',
            generator_version: 'shared_future_v1',
            proposed_title: '每一百天留一個小慶祝',
            proposed_notes: '把重要的關係節點變成固定會一起回來看的儀式。',
            evidence: [
              {
                source_kind: 'journal',
                source_id: 'journal-source-1',
                label: '你的日記 · 2026-03-29',
                excerpt: '我們約好以後每個一百天都要慶祝一下。',
              },
              {
                source_kind: 'card',
                source_id: 'session-source-1',
                label: '共同卡片 · 今天能量',
                excerpt: '我想一起把每個一百天都變成小小慶祝。',
              },
            ],
            created_at: new Date().toISOString(),
            reviewed_at: null,
            target_wishlist_item_id: null,
            accepted_wishlist_item_id: null,
          },
          {
            id: 'suggestion-2',
            section: 'shared_future',
            status: 'pending',
            generator_version: 'shared_future_v1',
            proposed_title: '一起存旅行基金',
            proposed_notes: '把想去的地方變成更具體的共同計畫。',
            evidence: [
              {
                source_kind: 'card',
                source_id: 'session-source-2',
                label: '共同卡片 · 今天能量',
                excerpt: '我想一起存一筆旅行基金，讓計畫更有形狀。',
              },
              {
                source_kind: 'appreciation',
                source_id: 'appreciation-source-1',
                label: '感恩 · 2026-03-30',
                excerpt: '謝謝你每天早上幫我準備咖啡。',
              },
            ],
            created_at: new Date().toISOString(),
            reviewed_at: null,
            target_wishlist_item_id: null,
            accepted_wishlist_item_id: null,
          },
        ];
      } else {
        pendingSuggestions = [];
      }
      await fulfillJson(route, pendingSuggestions);
      return;
    }

    if (path.includes('/love-map/suggestions/shared-future/refinements/') && path.endsWith('/generate') && method === 'POST') {
      const wishlistItemId = path.split('/').at(-2) ?? '';
      generatedRefinementCalls.push(wishlistItemId);
      generatedRefinementCallCounts[wishlistItemId] = (generatedRefinementCallCounts[wishlistItemId] ?? 0) + 1;
      const targetItem = system.wishlist_items.find((item) => item.id === wishlistItemId);
      if (!targetItem) {
        await fulfillJson(route, [], 404);
        return;
      }
      if (pendingRefinements.some((item) => item.target_wishlist_item_id === wishlistItemId)) {
        await fulfillJson(
          route,
          pendingRefinements.filter((item) => item.target_wishlist_item_id === wishlistItemId),
        );
        return;
      }
      if (wishlistItemId === 'wish-2' && generatedRefinementCallCounts[wishlistItemId] > 1) {
        await fulfillJson(route, []);
        return;
      }

      const nextSuggestion =
        wishlistItemId === 'wish-2'
          ? {
              id: 'refinement-kyoto',
              section: 'shared_future_refinement',
              status: 'pending',
              generator_version: 'shared_future_refinement_next_step_v1',
              proposed_title: '',
              proposed_notes: '先一起挑一個想看的楓葉週，再把機票提醒設進行事曆。',
              evidence: [
                {
                  source_kind: 'shared_future_item',
                  source_id: 'wish-2',
                  label: '目前的 Shared Future',
                  excerpt: '一起去京都看秋天｜想慢慢走巷子和神社。',
                },
              ],
              created_at: new Date().toISOString(),
              reviewed_at: null,
              target_wishlist_item_id: 'wish-2',
              accepted_wishlist_item_id: null,
            }
          : {
              id: 'refinement-monthly',
              section: 'shared_future_refinement',
              status: 'pending',
              generator_version: 'shared_future_refinement_next_step_v1',
              proposed_title: '',
              proposed_notes: '先把每月第二個週五晚上固定留給彼此。',
              evidence: [
                {
                  source_kind: 'shared_future_item',
                  source_id: 'wish-1',
                  label: '目前的 Shared Future',
                  excerpt: '每個月留一晚只屬於我們｜先把那一晚留給散步和晚餐。',
                },
              ],
              created_at: new Date().toISOString(),
              reviewed_at: null,
              target_wishlist_item_id: 'wish-1',
              accepted_wishlist_item_id: null,
            };
      pendingRefinements = [...pendingRefinements, nextSuggestion];
      await fulfillJson(route, [nextSuggestion]);
      return;
    }

    if (path.includes('/love-map/suggestions/shared-future/refinements/') && path.endsWith('/generate-cadence') && method === 'POST') {
      const wishlistItemId = path.split('/').at(-2) ?? '';
      generatedCadenceRefinementCalls.push(wishlistItemId);
      generatedRefinementCallCounts[`cadence:${wishlistItemId}`] = (generatedRefinementCallCounts[`cadence:${wishlistItemId}`] ?? 0) + 1;
      const targetItem = system.wishlist_items.find((item) => item.id === wishlistItemId);
      if (!targetItem) {
        await fulfillJson(route, [], 404);
        return;
      }
      if (pendingRefinements.some((item) => item.target_wishlist_item_id === wishlistItemId)) {
        await fulfillJson(
          route,
          pendingRefinements.filter((item) => item.target_wishlist_item_id === wishlistItemId),
        );
        return;
      }
      if (wishlistItemId === 'wish-2') {
        await fulfillJson(route, []);
        return;
      }
      if (wishlistItemId === 'wish-1' && generatedRefinementCallCounts[`cadence:${wishlistItemId}`] > 1) {
        await fulfillJson(route, []);
        return;
      }

      const nextSuggestion =
        wishlistItemId === 'wish-3'
          ? {
              id: 'refinement-repair-cadence',
              section: 'shared_future_refinement',
              status: 'pending',
              generator_version: 'shared_future_refinement_cadence_v1',
              proposed_title: '',
              proposed_notes: '每次明顯爭執後 24 小時內安排一次短暫復盤。',
              evidence: [
                {
                  source_kind: 'shared_future_item',
                  source_id: 'wish-3',
                  label: '目前的 Shared Future',
                  excerpt: '建立我們的衝突後修復儀式｜希望每次明顯爭執後，都能慢慢回到同一邊。',
                },
              ],
              created_at: new Date().toISOString(),
              reviewed_at: null,
              target_wishlist_item_id: 'wish-3',
              accepted_wishlist_item_id: null,
            }
          : {
              id: 'refinement-monthly-cadence',
              section: 'shared_future_refinement',
              status: 'pending',
              generator_version: 'shared_future_refinement_cadence_v1',
              proposed_title: '',
              proposed_notes: '每月第二個週五晚上留給彼此。',
              evidence: [
                {
                  source_kind: 'shared_future_item',
                  source_id: 'wish-1',
                  label: '目前的 Shared Future',
                  excerpt: '每個月留一晚只屬於我們｜先把那一晚留給散步和晚餐。',
                },
              ],
              created_at: new Date().toISOString(),
              reviewed_at: null,
              target_wishlist_item_id: 'wish-1',
              accepted_wishlist_item_id: null,
            };
      pendingRefinements = [...pendingRefinements, nextSuggestion];
      await fulfillJson(route, [nextSuggestion]);
      return;
    }

    if (path.includes('/love-map/suggestions/') && path.endsWith('/dismiss') && method === 'POST') {
      const suggestionId = path.split('/').at(-2) ?? '';
      const suggestion = pendingSuggestions.find((item) => item.id === suggestionId);
      if (suggestion) {
        dismissedSuggestionIds.push(suggestionId);
        pendingSuggestions = pendingSuggestions.filter((item) => item.id !== suggestionId);
        await fulfillJson(route, {
          ...suggestion,
          status: 'dismissed',
          reviewed_at: new Date().toISOString(),
        });
        return;
      }

      const refinement = pendingRefinements.find((item) => item.id === suggestionId);
      dismissedRefinementIds.push(suggestionId);
      pendingRefinements = pendingRefinements.filter((item) => item.id !== suggestionId);
      await fulfillJson(route, {
        ...(refinement ?? {
          id: suggestionId,
          section: 'shared_future_refinement',
          status: 'dismissed',
          generator_version: 'shared_future_refinement_next_step_v1',
          proposed_title: '',
          proposed_notes: '',
          evidence: [],
          target_wishlist_item_id: null,
          accepted_wishlist_item_id: null,
        }),
        status: 'dismissed',
        reviewed_at: new Date().toISOString(),
      });
      return;
    }

    if (path.includes('/love-map/suggestions/') && path.endsWith('/accept') && method === 'POST') {
      const suggestionId = path.split('/').at(-2) ?? '';
      const acceptedSuggestion = pendingSuggestions.find((item) => item.id === suggestionId);
      if (acceptedSuggestion) {
        acceptedSuggestionIds.push(suggestionId);
        pendingSuggestions = pendingSuggestions.filter((item) => item.id !== suggestionId);
        const nextWish = {
          id: `wish-${system.wishlist_items.length + 1}`,
          title: acceptedSuggestion.proposed_title,
          notes: acceptedSuggestion.proposed_notes,
          created_at: new Date().toISOString(),
          added_by_me: true,
        };
        system.wishlist_items = [nextWish, ...system.wishlist_items];
        system.stats.wishlist_count = system.wishlist_items.length;
        system.stats.last_activity_at = nextWish.created_at;
        await fulfillJson(route, nextWish);
        return;
      }

      const acceptedRefinement = pendingRefinements.find((item) => item.id === suggestionId);
      acceptedRefinementIds.push(suggestionId);
      pendingRefinements = pendingRefinements.filter((item) => item.id !== suggestionId);
      const targetId = acceptedRefinement?.target_wishlist_item_id;
      const refinementLine = acceptedRefinement?.proposed_notes
        ? `${
            acceptedRefinement.generator_version === 'shared_future_refinement_cadence_v1' ? '節奏' : '下一步'
          }：${acceptedRefinement.proposed_notes}`
        : '';
      if (targetId && refinementLine) {
        system.wishlist_items = system.wishlist_items.map((item) =>
          item.id !== targetId || item.notes.includes(refinementLine)
            ? item
            : {
                ...item,
                notes: item.notes ? `${item.notes}\n\n${refinementLine}` : refinementLine,
              },
        );
      }
      const updatedTarget = system.wishlist_items.find((item) => item.id === targetId);
      system.stats.last_activity_at = new Date().toISOString();
      await fulfillJson(route, updatedTarget ?? {});
      return;
    }

    await fulfillJson(route, {});
  };

  await page.route('**/api/**', apiHandler);

  return {
    baselinePayloads,
    generatedSuggestionCalls,
    goalPayloads,
    notePayloads,
    acceptedSuggestionIds,
    dismissedSuggestionIds,
    generatedRefinementCalls,
    generatedCadenceRefinementCalls,
    acceptedRefinementIds,
    dismissedRefinementIds,
    wishlistPayloads,
  };
}

type LiveStoryMoment = {
  kind: 'appreciation' | 'card' | 'journal';
  title: string;
  description: string;
  occurred_at: string;
  source_id?: string | null;
};

function memoryStoryHref(moment: LiveStoryMoment) {
  const date = moment.occurred_at.slice(0, 10);
  return `/memory?date=${date}&kind=${moment.kind}&id=${moment.source_id}`;
}

async function expectFocusedMemoryCardInViewport(page: Page, kind: 'appreciation' | 'card') {
  const focusedCards = page.locator('[data-memory-focused="true"]');
  await expect(focusedCards).toHaveCount(1);
  const focusedCard = focusedCards.first();
  await expect(focusedCard).toHaveAttribute('data-memory-kind', kind);
  await expect(focusedCard).toBeVisible();
  await expect(focusedCard).toBeInViewport();

  return focusedCard;
}

test.describe('Love Map / Relationship System v1', () => {
  test.use({ bypassCSP: true });

  test('renders real relationship sections and saves structured edits', async ({ page }) => {
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Love Map spec.',
    );

    const apiState = await mockLoveMapApi(page);
    await page.goto('/love-map');

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: '把 Haven 已經知道、仍在學、以及你們想一起走向的未來，放回同一個地方。',
      }),
    ).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '先把目前的共同方向看清楚。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把真正被留下來的 shared memory，放回你們的關係故事裡。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把你的 relationship reflections 留成可回讀的內在地圖。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把你們想一起靠近的生活，放進同一張藍圖裡。' })).toBeVisible();
    await expect(page.getByText('目前的關係脈動與北極星方向')).toBeVisible();
    await expect(page.getByText('謝謝你每天早上幫我準備咖啡')).toBeVisible();
    await expect(page.getByText('一年前的這幾天（3/21 – 3/27）：1 則日記、1 則共同卡片回憶、1 則感恩。')).toBeVisible();
    await expect(page.getByText('目前沒有待你審核的 Shared Future 建議。')).toBeVisible();

    const intimacySelect = page.locator('#love-map-baseline-intimacy');
    await intimacySelect.evaluate((node) => {
      const select = node as HTMLSelectElement;
      select.value = '5';
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await expect(intimacySelect).toHaveValue('5');
    await page.getByRole('button', { name: '保存 Relationship Pulse' }).click();
    await expect.poll(() => apiState.baselinePayloads.length).toBe(1);
    expect(apiState.baselinePayloads[0]).toEqual({
      scores: {
        intimacy: 5,
        conflict: 3,
        trust: 5,
        communication: 4,
        commitment: 5,
      },
    });

    await page.getByRole('button', { name: '更多信任' }).click();
    const saveGoalButton = page.getByRole('button', { name: '保存共同方向' });
    await saveGoalButton.scrollIntoViewIfNeeded();
    await saveGoalButton.click();
    await expect.poll(() => apiState.goalPayloads.length).toBe(1);
    expect(apiState.goalPayloads[0]).toEqual({ goal_slug: 'more_trust' });

    const safeLayerNote = page.getByLabel('安全層 筆記');
    await expect(safeLayerNote).toHaveValue('我知道我們最近需要更穩定的回來對話節奏。');
    await page.getByRole('button', { name: '保存這一層' }).first().click();
    await expect.poll(() => apiState.notePayloads.length).toBe(1);
    expect(apiState.notePayloads[0]).toEqual({
      layer: 'safe',
      content: '我知道我們最近需要更穩定的回來對話節奏。',
    });

    await page.getByLabel('未來片段標題').fill('一起把週日早晨留給散步');
    await page.getByLabel('補充（選填）').fill('想把那段時間變成固定的安靜儀式。');
    await page.getByRole('button', { name: '放進共同藍圖' }).click();
    await expect.poll(() => apiState.wishlistPayloads.length).toBe(1);
    expect(apiState.wishlistPayloads[0]).toEqual({
      title: '一起把週日早晨留給散步',
      notes: '想把那段時間變成固定的安靜儀式。',
    });
    await expect(page.getByText('一起把週日早晨留給散步')).toBeVisible();

    await page.getByRole('button', { name: '讓 Haven 提出 Shared Future 建議' }).click();
    await expect.poll(() => apiState.generatedSuggestionCalls.length).toBe(1);
    await expect(page.getByText('每一百天留一個小慶祝')).toBeVisible();
    await expect(page.getByText('一起存旅行基金')).toBeVisible();
    await expect(page.getByText('只有你看得到，按下接受前不會變成 shared truth。')).toHaveCount(2);

    await page.getByRole('button', { name: '略過' }).first().click();
    await expect.poll(() => apiState.dismissedSuggestionIds.length).toBe(1);
    await expect(page.getByText('每一百天留一個小慶祝')).not.toBeVisible();

    await page.getByRole('button', { name: '接受' }).first().click();
    await expect.poll(() => apiState.acceptedSuggestionIds.length).toBe(1);
    await expect(page.getByText('一起存旅行基金')).toBeVisible();

    await page.getByRole('button', { name: '讓 Haven 提出 Shared Future 建議' }).click();
    await expect.poll(() => apiState.generatedSuggestionCalls.length).toBe(2);
    await expect(page.getByText('目前沒有待你審核的 Shared Future 建議。')).toBeVisible();
    await expect(page.getByText('每一百天留一個小慶祝')).not.toBeVisible();

    const kyotoCard = page.locator('[data-shared-future-item-id="wish-2"]');
    await expect(kyotoCard.getByRole('button', { name: '讓 Haven 幫這個片段補節奏' })).toHaveCount(0);
    await kyotoCard.getByRole('button', { name: '讓 Haven 幫這個片段補下一步' }).click();
    await expect.poll(() => apiState.generatedRefinementCalls.includes('wish-2')).toBe(true);
    await expect(page.getByText('建議補上的下一步：先一起挑一個想看的楓葉週，再把機票提醒設進行事曆。')).toBeVisible();
    await expect(page.getByText('只有你看得到；接受前不會改動這個 Shared Future 片段。')).toBeVisible();

    await page.getByRole('button', { name: '略過' }).last().click();
    await expect.poll(() => apiState.dismissedRefinementIds.length).toBe(1);
    await expect(page.getByText('建議補上的下一步：先一起挑一個想看的楓葉週，再把機票提醒設進行事曆。')).not.toBeVisible();

    await kyotoCard.getByRole('button', { name: '讓 Haven 幫這個片段補下一步' }).click();
    await expect.poll(() => apiState.generatedRefinementCalls.filter((id) => id === 'wish-2').length).toBe(2);
    await expect(page.getByText('建議補上的下一步：先一起挑一個想看的楓葉週，再把機票提醒設進行事曆。')).not.toBeVisible();

    const monthlyCard = page.locator('[data-shared-future-item-id="wish-1"]');
    await expect(monthlyCard.getByRole('button', { name: '讓 Haven 幫這個片段補節奏' })).toBeVisible();
    await monthlyCard.getByRole('button', { name: '讓 Haven 幫這個片段補節奏' }).click();
    await expect.poll(() => apiState.generatedCadenceRefinementCalls.includes('wish-1')).toBe(true);
    await expect(page.getByText('建議補上的節奏：每月第二個週五晚上留給彼此。')).toBeVisible();
    await page.getByRole('button', { name: '略過' }).last().click();
    await expect.poll(() => apiState.dismissedRefinementIds.length).toBe(2);
    await expect(page.getByText('建議補上的節奏：每月第二個週五晚上留給彼此。')).not.toBeVisible();

    await monthlyCard.getByRole('button', { name: '讓 Haven 幫這個片段補節奏' }).click();
    await expect.poll(() => apiState.generatedCadenceRefinementCalls.filter((id) => id === 'wish-1').length).toBe(2);
    await expect(page.getByText('建議補上的節奏：每月第二個週五晚上留給彼此。')).not.toBeVisible();

    const repairCard = page.locator('[data-shared-future-item-id="wish-3"]');
    await expect(repairCard.getByRole('button', { name: '讓 Haven 幫這個片段補節奏' })).toBeVisible();
    await repairCard.getByRole('button', { name: '讓 Haven 幫這個片段補節奏' }).click();
    await expect.poll(() => apiState.generatedCadenceRefinementCalls.includes('wish-3')).toBe(true);
    await expect(page.getByText('建議補上的節奏：每次明顯爭執後 24 小時內安排一次短暫復盤。')).toBeVisible();
    await page.getByRole('button', { name: '接受' }).last().click();
    await expect.poll(() => apiState.acceptedRefinementIds.length).toBe(1);
    await expect(page.getByText('節奏：每次明顯爭執後 24 小時內安排一次短暫復盤。')).toBeVisible();
  });

  test('renders the memory-backed Story slice on the live local stack', async ({ page, context, request, baseURL }) => {
    test.setTimeout(90_000);
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
    const systemResponse = await request.get('http://127.0.0.1:8000/api/love-map/system', {
      headers: {
        Authorization: `Bearer ${authPayload.access_token}`,
      },
    });
    expect(systemResponse.ok()).toBeTruthy();
    const systemPayload = (await systemResponse.json()) as {
      data: {
        story: {
          moments: LiveStoryMoment[];
        };
      };
    };
    const storyMoments = systemPayload.data.story.moments;
    const appreciationMoment = storyMoments.find((moment) => moment.kind === 'appreciation');
    const cardMoment = storyMoments.find((moment) => moment.kind === 'card');
    const journalMoment = storyMoments.find((moment) => moment.kind === 'journal');
    expect(appreciationMoment?.source_id).toBeTruthy();
    expect(cardMoment?.source_id).toBeTruthy();
    expect(journalMoment?.source_id).toBeTruthy();

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

    await expect(page.getByRole('heading', { level: 2, name: '先把目前的共同方向看清楚。' })).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 2,
        name: '把真正被留下來的 shared memory，放回你們的關係故事裡。',
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 2,
        name: '把你的 relationship reflections 留成可回讀的內在地圖。',
      }),
    ).toBeVisible();

    const sectionHeadings = await page.locator('h2').allTextContents();
    const pulseIndex = sectionHeadings.indexOf('先把目前的共同方向看清楚。');
    const storyIndex = sectionHeadings.indexOf('把真正被留下來的 shared memory，放回你們的關係故事裡。');
    const innerLandscapeIndex = sectionHeadings.indexOf('把你的 relationship reflections 留成可回讀的內在地圖。');
    expect(storyIndex).toBeGreaterThan(pulseIndex);
    expect(innerLandscapeIndex).toBeGreaterThan(storyIndex);

    await expect(page.getByText('你昨天主動洗碗讓我很感動，我知道你也很累了。')).toBeVisible();
    await expect(page.getByText('一年前的今天')).toBeVisible();
    await expect(page.getByText('1 則日記、1 則共同卡片回憶、1 則感恩。')).toBeVisible();
    await expect(page.getByText('雙方都回答了')).toBeVisible();
    await expect(page.getByText('只來自 Haven 已經留下的 shared memory')).toBeVisible();

    const appreciationHref = memoryStoryHref(appreciationMoment!);
    await page.locator(`a[href="${appreciationHref}"]`).evaluate((node) => {
      window.location.assign((node as HTMLAnchorElement).href);
    });
    await expect.poll(() => {
      const url = new URL(page.url());
      return JSON.stringify({
        path: url.pathname,
        date: url.searchParams.get('date'),
        kind: url.searchParams.get('kind'),
        id: url.searchParams.get('id'),
      });
    }).toBe(JSON.stringify({
      path: '/memory',
      date: appreciationMoment!.occurred_at.slice(0, 10),
      kind: 'appreciation',
      id: appreciationMoment!.source_id,
    }));
    await expect(page.getByText('Day Spotlight')).toBeVisible();
    await expect(
      page.getByText('把月份裡的一天打開來看，不只是知道那天有痕跡，而是真的看見那天留下了什麼。'),
    ).toBeVisible();
    const focusedAppreciationCard = await expectFocusedMemoryCardInViewport(page, 'appreciation');
    await expect(focusedAppreciationCard).toContainText(appreciationMoment!.description);

    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    const cardHref = memoryStoryHref(cardMoment!);
    await page.locator(`a[href="${cardHref}"]`).evaluate((node) => {
      window.location.assign((node as HTMLAnchorElement).href);
    });
    await expect.poll(() => {
      const url = new URL(page.url());
      return JSON.stringify({
        path: url.pathname,
        date: url.searchParams.get('date'),
        kind: url.searchParams.get('kind'),
        id: url.searchParams.get('id'),
      });
    }).toBe(JSON.stringify({
      path: '/memory',
      date: cardMoment!.occurred_at.slice(0, 10),
      kind: 'card',
      id: cardMoment!.source_id,
    }));
    await expect(page.getByText('Day Spotlight')).toBeVisible();
    await expect(
      page.getByText('把月份裡的一天打開來看，不只是知道那天有痕跡，而是真的看見那天留下了什麼。'),
    ).toBeVisible();
    const focusedCardMemory = await expectFocusedMemoryCardInViewport(page, 'card');
    await expect(focusedCardMemory).toContainText(cardMoment!.description);
    await expect(focusedCardMemory).toContainText('雙方都回答了');

    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    const journalLink = page.locator(`a[href="/journal/${journalMoment!.source_id}"]`);
    await expect(journalLink).toBeVisible();
    await journalLink.evaluate((node) => {
      window.location.assign((node as HTMLAnchorElement).href);
    });
    await expect(page).toHaveURL(new RegExp(`/journal/${journalMoment!.source_id}$`));
  });
});
