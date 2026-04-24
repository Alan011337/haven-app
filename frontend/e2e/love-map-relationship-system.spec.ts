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
  const identityPayloads: Array<Record<string, unknown>> = [];
  const compassPayloads: Array<Record<string, unknown>> = [];
  const heartProfilePayloads: Array<Record<string, unknown>> = [];
  const repairAgreementPayloads: Array<Record<string, unknown>> = [];
  let weeklyTaskCompletionCount = 0;
  const generatedSuggestionCalls: Array<Record<string, unknown>> = [];
  const generatedCompassSuggestionCalls: Array<Record<string, unknown>> = [];
  const generatedStoryRitualCalls: Array<Record<string, unknown>> = [];
  const generatedRefinementCalls: string[] = [];
  const generatedCadenceRefinementCalls: string[] = [];
  const generatedRefinementCallCounts: Record<string, number> = {};
  const acceptedSuggestionIds: string[] = [];
  const dismissedSuggestionIds: string[] = [];
  const acceptedCompassSuggestionIds: string[] = [];
  const dismissedCompassSuggestionIds: string[] = [];
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
    relationship_compass: {
      identity_statement: '我們是在忙裡仍願意回來對話的伴侶。',
      story_anchor: '想一起記得那些有走回彼此的時刻。',
      future_direction: '接下來一起靠近更穩定的週末節奏。',
      updated_by_name: 'Alice Chen',
      updated_at: new Date(now - 9 * 60 * 60 * 1000).toISOString(),
    },
    // Seed a single prior history entry so the Compass timeline renders on
    // first load. Server ordering is most-recent-first; this represents
    // the first time the current Compass wording was written down.
    relationship_compass_history: [
      {
        id: 'compass-change-seed-1',
        changed_at: new Date(now - 9 * 60 * 60 * 1000).toISOString(),
        changed_by_name: 'Alice Chen',
        origin_kind: 'manual_edit',
        fields: [
          {
            key: 'identity_statement',
            label: '身份',
            change_kind: 'added',
            before_text: null,
            after_text: '我們是在忙裡仍願意回來對話的伴侶。',
          },
          {
            key: 'story_anchor',
            label: '故事',
            change_kind: 'added',
            before_text: null,
            after_text: '想一起記得那些有走回彼此的時刻。',
          },
          {
            key: 'future_direction',
            label: '未來',
            change_kind: 'added',
            before_text: null,
            after_text: '接下來一起靠近更穩定的週末節奏。',
          },
        ],
        revision_note: null,
      },
    ] as Array<{
      id: string;
      changed_at: string;
      changed_by_name: string;
      origin_kind: 'manual_edit' | 'accepted_suggestion';
      fields: Array<{
        key: string;
        label: string;
        change_kind: 'added' | 'updated' | 'cleared';
        before_text: string | null;
        after_text: string | null;
      }>;
      revision_note: string | null;
    }>,
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
    essentials: {
      my_care_preferences: {
        primary: 'words',
        secondary: 'time',
        updated_at: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      },
      my_care_profile: {
        support_me: '先讓我安靜五分鐘，再陪我慢慢整理。',
        avoid_when_stressed: '不要立刻逼我給答案。',
        small_delights: '回家時先抱我一下。',
        updated_at: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      },
      partner_care_preferences: {
        primary: 'acts',
        secondary: 'touch',
        updated_at: new Date(now - 14 * 60 * 60 * 1000).toISOString(),
      },
      partner_care_profile: {
        support_me: '先幫我把桌面收乾淨，我會比較能慢慢說。',
        avoid_when_stressed: '不要用玩笑帶過我真的在意的事。',
        small_delights: '如果你先幫我泡熱茶，我會覺得被照顧。',
        updated_at: new Date(now - 14 * 60 * 60 * 1000).toISOString(),
      },
      repair_agreements: {
        protect_what_matters: '先保護彼此的安全感，不在最高張力時替對方下定論。',
        avoid_in_conflict: '避免翻舊帳，也避免在還很急的時候一直逼對方給答案。',
        repair_reentry: '先留一段空氣，再在 24 小時內回來把感受與需要說清楚。',
        updated_by_name: 'Alice Chen',
        updated_at: new Date(now - 11 * 60 * 60 * 1000).toISOString(),
      },
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

  type MockSuggestion = {
    id: string;
    section: string;
    status: string;
    generator_version: string;
    proposed_title: string;
    proposed_notes: string;
    relationship_compass_candidate?: {
      identity_statement: string | null;
      story_anchor: string | null;
      future_direction: string | null;
    } | null;
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
  };

  let pendingSuggestions: MockSuggestion[] = [];
  let pendingCompassSuggestions: MockSuggestion[] = [];
  let pendingRefinements: MockSuggestion[] = [];
  let servedNoopCompassSuggestion = false;
  let servedDuplicateTitleSuggestion = false;

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
        full_name: system.me.full_name,
        is_active: true,
        partner_id: 'partner-1',
        partner_name: 'Bob',
        savings_score: 42,
      });
      return;
    }

    if (path.endsWith('/users/me') && method === 'PATCH') {
      const payload = route.request().postDataJSON() as { full_name?: string | null };
      identityPayloads.push(payload);
      system.me.full_name = payload.full_name?.trim() || null;
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

    if (path.endsWith('/love-map/identity/compass') && method === 'PUT') {
      const payload = route.request().postDataJSON() as {
        identity_statement?: string | null;
        story_anchor?: string | null;
        future_direction?: string | null;
        revision_note?: string | null;
      };
      compassPayloads.push(payload);

      // Mirror backend semantics: derive per-field before/after from the
      // previous compass vs. the incoming payload, drop unchanged fields,
      // and skip the history row entirely when nothing moved. Whitespace-
      // only revision_note normalizes to null. This keeps the e2e path
      // honest about the no-op guard the server enforces.
      const prev = system.relationship_compass ?? {
        identity_statement: null,
        story_anchor: null,
        future_direction: null,
        updated_by_name: null,
        updated_at: null,
      };
      const normalizedFields = {
        identity_statement: payload.identity_statement?.trim() || null,
        story_anchor: payload.story_anchor?.trim() || null,
        future_direction: payload.future_direction?.trim() || null,
      } as const;
      const fieldLabels: Record<keyof typeof normalizedFields, string> = {
        identity_statement: '身份',
        story_anchor: '故事',
        future_direction: '未來',
      };
      const changedFields: Array<{
        key: string;
        label: string;
        change_kind: 'added' | 'updated' | 'cleared';
        before_text: string | null;
        after_text: string | null;
      }> = [];
      (Object.keys(normalizedFields) as Array<keyof typeof normalizedFields>).forEach((key) => {
        const before = prev[key] ?? null;
        const after = normalizedFields[key];
        if (before === after) return;
        let changeKind: 'added' | 'updated' | 'cleared';
        if (before === null) changeKind = 'added';
        else if (after === null) changeKind = 'cleared';
        else changeKind = 'updated';
        changedFields.push({
          key,
          label: fieldLabels[key],
          change_kind: changeKind,
          before_text: before,
          after_text: after,
        });
      });

      const trimmedRevisionNote = payload.revision_note?.trim() ?? '';
      const normalizedRevisionNote = trimmedRevisionNote.length > 0 ? trimmedRevisionNote : null;
      const savedAtIso = new Date().toISOString();

      if (changedFields.length > 0) {
        system.relationship_compass = {
          ...normalizedFields,
          updated_by_name: system.me.full_name,
          updated_at: savedAtIso,
        };
        system.stats.last_activity_at = savedAtIso;

        system.relationship_compass_history = [
          {
            id: `compass-change-${system.relationship_compass_history.length + 1}`,
            changed_at: savedAtIso,
            changed_by_name: system.me.full_name,
            origin_kind: 'manual_edit',
            fields: changedFields,
            revision_note: normalizedRevisionNote,
          },
          ...system.relationship_compass_history,
        ];
      }

      await fulfillJson(route, system.relationship_compass);
      return;
    }

    if (path.endsWith('/love-map/essentials/heart-profile') && method === 'PUT') {
      const payload = route.request().postDataJSON() as {
        primary?: string | null;
        secondary?: string | null;
        support_me?: string | null;
        avoid_when_stressed?: string | null;
        small_delights?: string | null;
      };
      heartProfilePayloads.push(payload);
      system.essentials.my_care_preferences = {
        primary: payload.primary ?? null,
        secondary: payload.secondary ?? null,
        updated_at: new Date().toISOString(),
      };
      system.essentials.my_care_profile = {
        support_me: payload.support_me?.trim() || null,
        avoid_when_stressed: payload.avoid_when_stressed?.trim() || null,
        small_delights: payload.small_delights?.trim() || null,
        updated_at: system.essentials.my_care_preferences.updated_at,
      };
      system.stats.last_activity_at = system.essentials.my_care_preferences.updated_at;
      await fulfillJson(route, {
        care_preferences: {
          primary: system.essentials.my_care_preferences.primary,
          secondary: system.essentials.my_care_preferences.secondary,
          updated_at: system.essentials.my_care_preferences.updated_at,
        },
        care_profile: system.essentials.my_care_profile,
      });
      return;
    }

    if (path.endsWith('/love-map/essentials/repair-agreements') && method === 'PUT') {
      const payload = route.request().postDataJSON() as {
        protect_what_matters?: string | null;
        avoid_in_conflict?: string | null;
        repair_reentry?: string | null;
      };
      repairAgreementPayloads.push(payload);
      system.essentials.repair_agreements = {
        protect_what_matters: payload.protect_what_matters?.trim() || null,
        avoid_in_conflict: payload.avoid_in_conflict?.trim() || null,
        repair_reentry: payload.repair_reentry?.trim() || null,
        updated_by_name: system.me.full_name,
        updated_at: new Date().toISOString(),
      };
      system.stats.last_activity_at = system.essentials.repair_agreements.updated_at;
      await fulfillJson(route, system.essentials.repair_agreements);
      return;
    }

    if (path.endsWith('/love-languages/preference') && method === 'PUT') {
      const payload = route.request().postDataJSON() as {
        preference: { primary?: string | null; secondary?: string | null };
      };
      heartProfilePayloads.push(payload.preference);
      system.essentials.my_care_preferences = {
        primary: payload.preference.primary ?? null,
        secondary: payload.preference.secondary ?? null,
        updated_at: new Date().toISOString(),
      };
      await fulfillJson(route, {
        preference: {
          primary: system.essentials.my_care_preferences.primary,
          secondary: system.essentials.my_care_preferences.secondary,
        },
        updated_at: system.essentials.my_care_preferences.updated_at,
      });
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

    if (path.endsWith('/love-map/suggestions/relationship-compass') && method === 'GET') {
      await fulfillJson(route, pendingCompassSuggestions);
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
      const payload = route.request().postDataJSON() as {
        scores: {
          intimacy: number;
          conflict: number;
          trust: number;
          communication: number;
          commitment: number;
        };
      };
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

    if (normalizedPath.endsWith('/blueprint') && method === 'GET') {
      await fulfillJson(route, system.wishlist_items);
      return;
    }

    if (path.endsWith('/love-map/suggestions/relationship-compass/generate') && method === 'POST') {
      generatedCompassSuggestionCalls.push({});
      const suffix = generatedCompassSuggestionCalls.length === 1 ? 'dismiss' : 'accept';
      const shouldReturnNoop = generatedCompassSuggestionCalls.length >= 3 && !servedNoopCompassSuggestion;
      const nextSuggestion: MockSuggestion = {
        id: shouldReturnNoop ? 'compass-suggestion-noop' : `compass-suggestion-${suffix}`,
        section: 'relationship_compass',
        status: 'pending',
        generator_version: 'relationship_compass_v1',
        proposed_title: 'Relationship Compass 建議更新',
        proposed_notes: 'Haven 根據最近留下的片段整理出一版可審核的 Compass 更新。',
        relationship_compass_candidate: {
          identity_statement: shouldReturnNoop
            ? system.relationship_compass.identity_statement
            : suffix === 'accept'
              ? '我們是在忙裡仍願意慢慢回來對話的伴侶。'
              : '我們是在忙裡仍願意先把語氣慢下來的伴侶。',
          story_anchor: shouldReturnNoop
            ? system.relationship_compass.story_anchor
            : '想一起記得晚餐後散步，讓我們又回到彼此身邊。',
          future_direction: shouldReturnNoop
            ? system.relationship_compass.future_direction
            : '接下來一起把週末留給散步和真正對話。',
        },
        evidence: [
          {
            source_kind: 'journal',
            source_id: 'a0000000-0000-4000-8000-0000000000a1',
            label: '你的日記 · 2026-03-29',
            excerpt: '散步時把壓力慢慢說完。',
          },
          {
            source_kind: 'appreciation',
            source_id: 'appreciation-compass-source-1',
            label: '感謝片段',
            excerpt: '謝謝你晚餐後陪我散步。',
          },
        ],
        created_at: new Date().toISOString(),
        reviewed_at: null,
        target_wishlist_item_id: null,
        accepted_wishlist_item_id: null,
      };
      pendingCompassSuggestions = [nextSuggestion];
      if (shouldReturnNoop) {
        servedNoopCompassSuggestion = true;
      }
      await fulfillJson(route, pendingCompassSuggestions);
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
                source_kind: 'card',
                source_id: 'session-source-1',
                label: '共同卡片 · 今天能量',
                excerpt: '我想一起把每個一百天都變成小小慶祝。',
              },
              {
                source_kind: 'appreciation',
                source_id: 'appreciation-source-2',
                label: '感恩 · 2026-03-30',
                excerpt: '謝謝你每天早上幫我準備咖啡。',
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
      } else if (generatedSuggestionCalls.length === 2 && !servedDuplicateTitleSuggestion) {
        pendingSuggestions = [
          {
            id: 'suggestion-dup-1',
            section: 'shared_future',
            status: 'pending',
            generator_version: 'shared_future_v1',
            proposed_title: system.wishlist_items[0]?.title ?? '每個月留一晚只屬於我們',
            proposed_notes: '這個標題已存在於 Shared Future。',
            evidence: [
              {
                source_kind: 'card',
                source_id: 'session-source-dup',
                label: '共同卡片 · 今天能量',
                excerpt: '我們是不是可以把這件事固定留下來？',
              },
            ],
            created_at: new Date().toISOString(),
            reviewed_at: null,
            target_wishlist_item_id: null,
            accepted_wishlist_item_id: null,
          },
        ];
        servedDuplicateTitleSuggestion = true;
      } else {
        pendingSuggestions = [];
      }
      await fulfillJson(route, pendingSuggestions);
      return;
    }

    if (path.endsWith('/love-map/suggestions/shared-future/generate-story-ritual') && method === 'POST') {
      generatedStoryRitualCalls.push({});
      const existingPendingStoryRitual = pendingSuggestions.filter(
        (item) => item.generator_version === 'shared_future_story_ritual_v1',
      );
      if (existingPendingStoryRitual.length > 0) {
        await fulfillJson(route, existingPendingStoryRitual);
        return;
      }

      const storySuggestion = {
        id: `story-ritual-${generatedStoryRitualCalls.length}`,
        section: 'shared_future',
        status: 'pending',
        generator_version: 'shared_future_story_ritual_v1',
        proposed_title: '每逢紀念日一起重看一則回憶',
        proposed_notes: '在接近這段回聲的日子裡，一起重看一則回憶，交換現在的感受。',
        evidence: [
          {
            source_kind: 'story_time_capsule',
            source_id: '2025-03-21:2025-03-27',
            label: 'Story Time Capsule',
            excerpt: '一年前的這幾天（3/21 – 3/27）：1 則日記、1 則共同卡片回憶、1 則感恩。',
          },
          {
            source_kind: 'time_capsule_item',
            source_id: 'journal-1',
            label: 'Time Capsule · 日記',
            excerpt: '一年前的今天，我們第一次一起去了那間隱藏在巷子裡的咖啡廳。',
          },
        ],
        created_at: new Date().toISOString(),
        reviewed_at: null,
        target_wishlist_item_id: null,
        accepted_wishlist_item_id: null,
      };
      pendingSuggestions = [storySuggestion, ...pendingSuggestions];
      await fulfillJson(route, [storySuggestion]);
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

    if (path.includes('/love-map/suggestions/relationship-compass/') && path.endsWith('/dismiss') && method === 'POST') {
      const suggestionId = path.split('/').at(-2) ?? '';
      const suggestion = pendingCompassSuggestions.find((item) => item.id === suggestionId);
      dismissedCompassSuggestionIds.push(suggestionId);
      pendingCompassSuggestions = pendingCompassSuggestions.filter((item) => item.id !== suggestionId);
      await fulfillJson(route, {
        ...(suggestion ?? {
          id: suggestionId,
          section: 'relationship_compass',
          status: 'dismissed',
          generator_version: 'relationship_compass_v1',
          proposed_title: 'Relationship Compass 建議更新',
          proposed_notes: '',
          relationship_compass_candidate: null,
          evidence: [],
          target_wishlist_item_id: null,
          accepted_wishlist_item_id: null,
        }),
        status: 'dismissed',
        reviewed_at: new Date().toISOString(),
      });
      return;
    }

    if (path.includes('/love-map/suggestions/relationship-compass/') && path.endsWith('/accept') && method === 'POST') {
      const suggestionId = path.split('/').at(-2) ?? '';
      if (acceptedCompassSuggestionIds.includes(suggestionId)) {
        await fulfillJson(route, system.relationship_compass);
        return;
      }
      const suggestion = pendingCompassSuggestions.find((item) => item.id === suggestionId);
      acceptedCompassSuggestionIds.push(suggestionId);
      pendingCompassSuggestions = pendingCompassSuggestions.filter((item) => item.id !== suggestionId);
      const candidate = suggestion?.relationship_compass_candidate;
      const previous = system.relationship_compass;
      const savedAtIso = new Date().toISOString();
      if (candidate && previous) {
        system.relationship_compass = {
          identity_statement: candidate.identity_statement ?? previous.identity_statement,
          story_anchor: candidate.story_anchor ?? previous.story_anchor,
          future_direction: candidate.future_direction ?? previous.future_direction,
          updated_by_name: system.me.full_name,
          updated_at: savedAtIso,
        };
        system.relationship_compass_history = [
          {
            id: `compass-suggestion-change-${acceptedCompassSuggestionIds.length}`,
            changed_at: savedAtIso,
            changed_by_name: system.me.full_name,
            origin_kind: 'accepted_suggestion',
            fields: [
              {
                key: 'identity_statement',
                label: '身份',
                change_kind: 'updated',
                before_text: previous.identity_statement,
                after_text: system.relationship_compass.identity_statement,
              },
              {
                key: 'story_anchor',
                label: '故事',
                change_kind: 'updated',
                before_text: previous.story_anchor,
                after_text: system.relationship_compass.story_anchor,
              },
              {
                key: 'future_direction',
                label: '未來',
                change_kind: 'updated',
                before_text: previous.future_direction,
                after_text: system.relationship_compass.future_direction,
              },
            ],
            revision_note: null,
          },
          ...system.relationship_compass_history,
        ];
        system.stats.last_activity_at = savedAtIso;
      }
      await fulfillJson(route, system.relationship_compass);
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
    identityPayloads,
    compassPayloads,
    heartProfilePayloads,
    repairAgreementPayloads,
    get weeklyTaskCompletionCount() {
      return weeklyTaskCompletionCount;
    },
    generatedCompassSuggestionCalls,
    generatedSuggestionCalls,
    goalPayloads,
    notePayloads,
    acceptedCompassSuggestionIds,
    dismissedCompassSuggestionIds,
    acceptedSuggestionIds,
    dismissedSuggestionIds,
    generatedStoryRitualCalls,
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

async function expectGuidePrimaryHref(page: Page, testId: string, href: string) {
  await expect(page.getByTestId(`${testId}-primary-action`)).toHaveAttribute('href', href);
}

async function expectGuideSecondaryHref(page: Page, testId: string, href: string) {
  await expect(page.getByTestId(`${testId}-secondary-action`)).toHaveAttribute('href', href);
}

test.describe('Relationship System naming and IA polish', () => {
  test.use({ bypassCSP: true });

  test('renders real relationship sections and saves structured edits', async ({ page }) => {
    test.setTimeout(60_000);
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Relationship System spec.',
    );

    const apiState = await mockLoveMapApi(page);
    await page.goto('/love-map');

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: '你們的關係地圖',
      }),
    ).toBeVisible();
    await expect(page.getByTestId('relationship-system-cover')).toContainText('已保存的共同真相');
    await expect(page.getByTestId('relationship-system-status-saved')).toContainText('4/4');
    await expect(page.getByTestId('relationship-system-status-pending')).toContainText('0 則');
    await expect(page.getByTestId('relationship-system-status-evolving')).toContainText('1 次');
    await expect(page.getByTestId('relationship-system-section-nav')).toBeVisible();
    await expect(page.getByTestId('relationship-system-section-nav-identity')).toHaveAttribute('href', '#identity');
    await expect(page.getByTestId('relationship-system-section-nav-identity')).toContainText('最近有更新');
    await expect(page.getByTestId('relationship-system-section-nav-heart')).toHaveAttribute('href', '#heart');
    await expect(page.getByTestId('relationship-system-section-nav-future')).toHaveAttribute('href', '#future');
    await expect(page.getByTestId('relationship-system-section-nav-recent-evolution')).toHaveAttribute('href', '#identity');
    await expect(page.getByTestId('relationship-system-next-action')).toContainText('回看最近演進');
    await expect(page.getByRole('heading', { level: 2, name: 'Identity / Heart / Story / Future' })).toBeVisible();
    await expect(page.getByText('Relationship System', { exact: true }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Blueprint 工作台' })).toBeVisible();
    await expect(page.getByRole('link', { name: '進入 Memory（完整 Story archive）' })).toBeVisible();
    await expect(page.getByTestId('relationship-system-guide-identity')).toContainText('我們是誰，現在往哪裡走。');
    await expect(page.getByTestId('relationship-system-guide-identity')).toContainText('關係系統入口');
    await expect(page.getByTestId('relationship-system-guide-heart')).toContainText('我們怎麼照顧彼此，現在感覺如何。');
    await expect(page.getByTestId('relationship-system-guide-heart')).toContainText('分層信任');
    await expect(page.getByTestId('relationship-system-guide-heart')).toContainText('照顧 5/5 · 修復 3/3');
    await expect(page.getByTestId('relationship-system-guide-story')).toContainText('哪些記憶真正定義了我們。');
    await expect(page.getByTestId('relationship-system-guide-story')).toContainText('記憶支撐');
    await expect(page.getByTestId('relationship-system-guide-future')).toContainText('你們正在一起建造什麼生活。');
    await expect(page.getByTestId('relationship-system-guide-future')).toContainText('已保存的共同真相');
    await expectGuidePrimaryHref(page, 'relationship-system-guide-identity', '#identity');
    await expectGuidePrimaryHref(page, 'relationship-system-guide-heart', '#heart');
    await expectGuidePrimaryHref(page, 'relationship-system-guide-story', '#story');
    await expectGuidePrimaryHref(page, 'relationship-system-guide-future', '#future');
    await expectGuideSecondaryHref(page, 'relationship-system-guide-identity', '/settings#settings-relationship');
    await expectGuideSecondaryHref(page, 'relationship-system-guide-heart', '/journal');
    await expectGuideSecondaryHref(page, 'relationship-system-guide-story', '/memory');
    await expectGuideSecondaryHref(page, 'relationship-system-guide-future', '/blueprint');

    await page.getByTestId('relationship-system-guide-identity-primary-action').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#identity');
    await page.goto('/love-map');
    await page.getByTestId('relationship-system-guide-heart-primary-action').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#heart');
    await page.goto('/love-map');
    await page.getByTestId('relationship-system-guide-story-primary-action').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#story');
    await page.goto('/love-map');
    await page.getByTestId('relationship-system-guide-future-primary-action').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#future');
    await page.goto('/love-map');
    await page.getByTestId('relationship-system-section-nav-heart').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#heart');
    await page.goto('/love-map');

    await expect(page.getByRole('heading', { level: 2, name: '把你們是誰、目前在往哪裡走，固定成系統首頁。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把關係現在的感受、照顧方式與私人理解，放回同一層。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '讓真正被留下來的 shared memory，變成可回來看的關係敘事。' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: '把你們想一起靠近的生活，留在能持續維護的共享藍圖裡。' })).toBeVisible();
    await expect(page.getByText('共享、伴侶可見與私人反思，分開呈現。')).toBeVisible();
    await expect(page.getByTestId('relationship-identity-compass-card')).toContainText('Relationship Compass');
    await expect(page.getByTestId('relationship-identity-compass-card')).toContainText('我們是在忙裡仍願意回來對話的伴侶。');
    await expect(page.getByTestId('relationship-identity-compass-updated-by')).toContainText('Alice Chen');
    await expect(page.getByText('謝謝你每天早上幫我準備咖啡')).toBeVisible();
    await expect(page.getByText('一年前的這幾天（3/21 – 3/27）：1 則日記、1 則共同卡片回憶、1 則感恩。')).toBeVisible();
    await expect(page.getByTestId('relationship-story-compass-echo-card')).toContainText('想一起記得那些有走回彼此的時刻。');
    await expect(page.getByTestId('relationship-future-compass-echo-card')).toContainText('接下來一起靠近更穩定的週末節奏。');
    await expect(page.getByTestId('shared-future-suggestion-empty')).toBeVisible();
    await expect(page.getByRole('button', { name: '讓 Haven 從這段故事提出 ritual' })).toBeVisible();

    await page.getByLabel('My name in Haven').fill('Alice System');
    await page.getByRole('button', { name: '保存名稱' }).click();
    await expect.poll(() => apiState.identityPayloads.length).toBe(1);
    expect(apiState.identityPayloads[0]).toEqual({ full_name: 'Alice System' });
    await expect(page.getByTestId('relationship-system-guide-identity')).toContainText('Alice System × Bob');

    await page.getByLabel('我們現在是什麼樣的關係').fill('我們是願意把重要事情留下來、也願意回來調整的伴侶。');
    await page.getByLabel('我們想一起記得哪段故事').fill('想一起記得那段忙到快散掉、但仍然靠咖啡和散步回來的週末。');
    await page.getByLabel('接下來一起靠近什麼').fill('接下來一起靠近更穩定的週日早晨節奏。');
    await page.getByRole('button', { name: '保存 Relationship Compass' }).click();
    await expect.poll(() => apiState.compassPayloads.length).toBe(1);
    expect(apiState.compassPayloads[0]).toEqual({
      identity_statement: '我們是願意把重要事情留下來、也願意回來調整的伴侶。',
      story_anchor: '想一起記得那段忙到快散掉、但仍然靠咖啡和散步回來的週末。',
      future_direction: '接下來一起靠近更穩定的週日早晨節奏。',
      // Client always sends this field; `null` when no note was typed.
      revision_note: null,
    });
    await expect(page.getByTestId('relationship-story-compass-echo-card')).toContainText('想一起記得那段忙到快散掉');
    await expect(page.getByTestId('relationship-future-compass-echo-card')).toContainText('更穩定的週日早晨節奏');

    // Timeline renders with a fresh entry after the save. The seeded entry
    // gets pushed down but stays within the last-3 window, and the new
    // update has no revision note, so no italic quote under it. The display
    // name stamped on the new row reflects the identity rename that happened
    // earlier in the flow ('Alice System'); the seed row was authored before
    // the rename and still reads 'Alice Chen'.
    await expect(page.getByTestId('relationship-identity-compass-history')).toBeVisible();
    await expect(page.getByTestId('relationship-identity-compass-history-entry')).toHaveCount(2);
    await expect(
      page.getByTestId('relationship-identity-compass-history-entry').first(),
    ).toContainText('Alice System');
    await expect(
      page.getByTestId('relationship-identity-compass-history-entry').first(),
    ).toContainText('調整了');
    await expect(
      page.getByTestId('relationship-identity-compass-history-entry').nth(1),
    ).toContainText('Alice Chen');
    await expect(page.getByTestId('relationship-identity-compass-history-note')).toHaveCount(0);

    await expect(page.getByTestId('relationship-heart-playbook-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-updated-by')).toContainText('Alice Chen');
    await expect(page.getByLabel('當張力升高時，我們想保護什麼')).toHaveValue(
      '先保護彼此的安全感，不在最高張力時替對方下定論。',
    );
    await expect(page.getByTestId('relationship-heart-playbook-partner-card')).toContainText('伴侶目前留下的 Heart Care Playbook');
    await expect(page.getByTestId('relationship-heart-playbook-partner-preferences')).toContainText('服務行動 · 次要是 身體接觸');
    await expect(page.getByTestId('relationship-heart-playbook-partner-support')).toContainText('先幫我把桌面收乾淨，我會比較能慢慢說。');
    await page.locator('#love-map-care-primary').selectOption('acts');
    await page.locator('#love-map-care-secondary').selectOption('time');
    await page.getByLabel('當我過載時，先怎麼幫我').fill('先幫我把手機放遠一點。');
    await page.getByLabel('我壓力大時，先避免什麼').fill('不要立刻逼我做決定。');
    await page.getByLabel('哪些小動作最能讓我感到被照顧').fill('回家時先抱我一下。');
    await page.getByRole('button', { name: '保存 Heart Care Playbook' }).click();
    await expect.poll(() => apiState.heartProfilePayloads.length).toBe(1);
    expect(apiState.heartProfilePayloads[0]).toEqual({
      primary: 'acts',
      secondary: 'time',
      support_me: '先幫我把手機放遠一點。',
      avoid_when_stressed: '不要立刻逼我做決定。',
      small_delights: '回家時先抱我一下。',
    });
    await expect(page.getByText('已留下 5/5 個 care cues').first()).toBeVisible();

    await page.getByRole('button', { name: '標記本週任務完成' }).click();
    await expect.poll(() => apiState.weeklyTaskCompletionCount).toBe(1);
    await expect(page.getByTestId('relationship-heart-weekly-task-card').getByText('本週任務已完成')).toBeVisible();

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
    await expect(
      page.locator('[data-shared-future-item-id]').filter({ hasText: '一起把週日早晨留給散步' }).first(),
    ).toBeVisible();

    await page.getByRole('button', { name: '讓 Haven 從這段故事提出 ritual' }).click();
    await expect.poll(() => apiState.generatedStoryRitualCalls.length).toBe(1);
    await expect(page.getByTestId('shared-future-suggestion-card').first().getByText('Haven 建議')).toBeVisible();
    await expect(page.getByRole('heading', { name: '每逢紀念日一起重看一則回憶' })).toBeVisible();
    await expect(page.getByText('根據可共同看見的片段')).toBeVisible();
    await expect(page.getByText('Story Time Capsule')).toBeVisible();
    await expect(page.getByText('Time Capsule · 日記')).toBeVisible();

    await page.getByRole('button', { name: '先略過' }).first().click();
    await expect.poll(() => apiState.dismissedSuggestionIds.length).toBe(1);
    await expect(page.getByRole('heading', { name: '每逢紀念日一起重看一則回憶' })).not.toBeVisible();

    await page.getByRole('button', { name: '讓 Haven 從這段故事提出 ritual' }).click();
    await expect.poll(() => apiState.generatedStoryRitualCalls.length).toBe(2);
    await expect(page.getByRole('heading', { name: '每逢紀念日一起重看一則回憶' })).toBeVisible();
    await page.getByRole('button', { name: '接受並寫入 Future' }).first().click();
    await expect.poll(() => apiState.acceptedSuggestionIds.length).toBe(1);
    // Accepted ritual lands as a new Shared Future wishlist item. Scope the
    // assertion to the Future section card — the compass's Nearby Future
    // sidebar also mirrors wishlist_items[0].title, which would otherwise
    // make `getByText` ambiguous.
    await expect(
      page.locator('[data-shared-future-item-id]').filter({ hasText: '每逢紀念日一起重看一則回憶' }).first(),
    ).toBeVisible();

    await page.getByTestId('shared-future-suggestion-empty-action').click();
    await expect.poll(() => apiState.generatedSuggestionCalls.length).toBe(1);
    await expect(page.getByRole('heading', { name: '每一百天留一個小慶祝' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '一起存旅行基金' })).toBeVisible();
    await expect(page.getByText('這是建議，不是已保存的共同未來')).toHaveCount(2);
    await expect(page.getByText('僅你可見（待審核）；伴侶只會看到你接受之後真正進入 Shared Future 的內容。')).toBeVisible();
    await expect(page.getByText('TRANSLATED PARTNER MARKER')).toHaveCount(0);
    // Shared Future evidence is pair-visible only; should never show Journal evidence.
    await expect(page.getByTestId('shared-future-suggestion-card').first()).toBeVisible();
    await expect(page.getByTestId('shared-future-suggestion-card').first().getByText('你的日記')).toHaveCount(0);
    await expect(page.getByTestId('shared-future-suggestion-card').first().getByText('journal')).toHaveCount(0);

    await page.getByRole('button', { name: '先略過' }).first().click();
    await expect.poll(() => apiState.dismissedSuggestionIds.length).toBe(2);
    await expect(page.getByRole('heading', { name: '每一百天留一個小慶祝' })).not.toBeVisible();

    await page.getByRole('button', { name: '接受並寫入 Future' }).first().click();
    await expect.poll(() => apiState.acceptedSuggestionIds.length).toBe(2);
    await expect(
      page.locator('[data-shared-future-item-id]').filter({ hasText: '一起存旅行基金' }).first(),
    ).toBeVisible();

    await page.getByTestId('shared-future-suggestion-empty-action').click();
    await expect.poll(() => apiState.generatedSuggestionCalls.length).toBe(2);
    // Second generate call returns a duplicate-title suggestion. Accept should be disabled.
    await expect(page.getByTestId('shared-future-suggestion-noop')).toBeVisible();
    await expect(page.getByRole('button', { name: '已存在於 Shared Future' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '每一百天留一個小慶祝' })).not.toBeVisible();

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
    await monthlyCard.getByRole('button', { name: '讓 Haven 幫這個片段補下一步' }).click();
    await expect.poll(() => apiState.generatedRefinementCalls.includes('wish-1')).toBe(true);
    await expect(page.getByText('建議補上的下一步：先把每月第二個週五晚上固定留給彼此。')).toBeVisible();
    await page.getByRole('button', { name: '接受' }).last().click();
    await expect.poll(() => apiState.acceptedRefinementIds.length).toBe(1);
    await expect(monthlyCard.getByText('補充', { exact: true })).toBeVisible();
    await expect(monthlyCard.getByText('下一步', { exact: true })).toBeVisible();
    await expect(monthlyCard.getByText('先把每月第二個週五晚上固定留給彼此。')).toBeVisible();
    await expect(monthlyCard.getByText('先把那一晚留給散步和晚餐。')).toBeVisible();
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
    await expect.poll(() => apiState.acceptedRefinementIds.length).toBe(2);
    await expect(repairCard.getByText('補充', { exact: true })).toBeVisible();
    await expect(repairCard.getByText('節奏', { exact: true })).toBeVisible();
    await expect(repairCard.getByText('每次明顯爭執後 24 小時內安排一次短暫復盤。')).toBeVisible();
    await expect(repairCard.getByText('希望每次明顯爭執後，都能慢慢回到同一邊。')).toBeVisible();
    await expect(kyotoCard.getByText('想慢慢走巷子和神社。')).toBeVisible();
    await expect(kyotoCard.getByText('補充', { exact: true })).toHaveCount(0);
    await expect(page.getByText('完整 Shared Future', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: '進入 Blueprint（完整 Shared Future）' })).toBeVisible();

  });

  test('relationship compass suggestions stay separate until accepted or dismissed', async ({ page }) => {
    test.setTimeout(45_000);
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Relationship System spec.',
    );

    const apiState = await mockLoveMapApi(page);
    await page.goto('/love-map#identity');

    await expect(page.getByTestId('relationship-identity-compass-card')).toContainText('Relationship Compass');
    await expect(page.getByText('目前沒有待審核的 Compass 建議。')).toBeVisible();
    await page.getByTestId('relationship-compass-suggestion-empty-action').click();
    await expect.poll(() => apiState.generatedCompassSuggestionCalls.length).toBe(1);
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toContainText('建議更新');
    await expect(page.getByTestId('relationship-compass-suggestion-compare')).toBeVisible();
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toContainText('目前保存');
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toContainText('建議');
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toContainText(
      '這是建議更新，不是已保存的共同真相',
    );
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toContainText('散步時把壓力慢慢說完');
    await expect(page.getByTestId('relationship-compass-suggestion-evidence-link')).toHaveAttribute(
      'href',
      '/journal/a0000000-0000-4000-8000-0000000000a1',
    );
    await page.getByRole('button', { name: '先略過' }).click();
    await expect.poll(() => apiState.dismissedCompassSuggestionIds).toEqual(['compass-suggestion-dismiss']);
    await expect(page.getByLabel('我們現在是什麼樣的關係')).toHaveValue('我們是在忙裡仍願意回來對話的伴侶。');

    await page.getByTestId('relationship-compass-suggestion-empty-action').click();
    await expect.poll(() => apiState.generatedCompassSuggestionCalls.length).toBe(2);
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toContainText(
      '我們是在忙裡仍願意慢慢回來對話的伴侶。',
    );
    await page.getByRole('button', { name: '接受並寫入 Compass' }).click();
    await expect.poll(() => apiState.acceptedCompassSuggestionIds).toEqual(['compass-suggestion-accept']);
    await expect(page.getByLabel('我們現在是什麼樣的關係')).toHaveValue(
      '我們是在忙裡仍願意慢慢回來對話的伴侶。',
    );
    await expect(page.getByTestId('relationship-identity-compass-history-entry').first()).toContainText(
      'Haven 建議 · 已接受',
    );
    await page.evaluate(async () => {
      await fetch('/api/love-map/suggestions/relationship-compass/compass-suggestion-accept/accept', { method: 'POST' });
    });
    await expect(page.getByText('Haven 建議 · 已接受')).toHaveCount(1);
    await expect(page.getByTestId('relationship-story-compass-echo-card')).toContainText(
      '想一起記得晚餐後散步',
    );
    await expect(page.getByText('這是建議更新，不是已保存的共同真相')).not.toBeVisible();

    // Generate a no-op suggestion (candidate equals saved). Accept should be disabled.
    await page.getByTestId('relationship-compass-suggestion-empty-action').click();
    await expect.poll(() => apiState.generatedCompassSuggestionCalls.length).toBe(3);
    await expect(page.getByRole('button', { name: '已和目前保存一致' })).toBeVisible();
  });

  test('compass save with revision note renders italic quote in timeline', async ({ page }) => {
    test.setTimeout(45_000);
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Relationship System spec.',
    );

    const apiState = await mockLoveMapApi(page);
    await page.goto('/love-map');

    // Timeline already renders with the seeded entry before any save.
    await expect(page.getByTestId('relationship-identity-compass-history')).toBeVisible();
    await expect(page.getByTestId('relationship-identity-compass-history-entry')).toHaveCount(1);

    await page.getByLabel('我們現在是什麼樣的關係').fill('我們是慢下來也還找得到彼此的伴侶。');
    await page.getByLabel('我們想一起記得哪段故事').fill('想一起記得那個清晨沒急著說話、只是一起煮咖啡的早上。');
    await page.getByLabel('接下來一起靠近什麼').fill('接下來不趕，讓一個下午只屬於我們。');
    await page.getByTestId('relationship-identity-compass-revision-note-input')
      .fill('這次不是重寫，是因為我們開始相信自己可以慢一點。');

    await page.getByRole('button', { name: '保存 Relationship Compass' }).click();

    await expect.poll(() => apiState.compassPayloads.length).toBe(1);
    expect(apiState.compassPayloads[0]).toEqual({
      identity_statement: '我們是慢下來也還找得到彼此的伴侶。',
      story_anchor: '想一起記得那個清晨沒急著說話、只是一起煮咖啡的早上。',
      future_direction: '接下來不趕，讓一個下午只屬於我們。',
      revision_note: '這次不是重寫，是因為我們開始相信自己可以慢一點。',
    });

    // New top entry shows up with the typed note rendered as italic quote.
    await expect(page.getByTestId('relationship-identity-compass-history-entry')).toHaveCount(2);
    const note = page.getByTestId('relationship-identity-compass-history-note').first();
    await expect(note).toBeVisible();
    await expect(note).toContainText('這次不是重寫，是因為我們開始相信自己可以慢一點。');

    // Draft clears after a successful save so the next save must be
    // deliberate.
    await expect(page.getByTestId('relationship-identity-compass-revision-note-input'))
      .toHaveValue('');
  });

  test('mobile viewport keeps the Relationship OS cover, section nav, and suggestion review readable', async ({ page }) => {
    test.setTimeout(45_000);
    test.skip(
      process.env.LOVE_MAP_LIVE_E2E === '1',
      'Live localhost mode skips the mocked Relationship System spec.',
    );

    const apiState = await mockLoveMapApi(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/love-map');

    await expect(page.getByTestId('relationship-system-cover')).toContainText('你們的關係地圖');
    await expect(page.getByTestId('relationship-system-status-saved')).toBeVisible();
    await expect(page.getByTestId('relationship-system-status-pending')).toBeVisible();
    await expect(page.getByTestId('relationship-system-section-nav')).toBeVisible();
    await expect(page.getByTestId('relationship-system-section-nav-future')).toContainText('Future');

    await page.getByTestId('relationship-system-section-nav-future').click();
    await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#future');
    await expect(page.getByTestId('shared-future-suggestion-empty')).toBeVisible();

    await page.getByTestId('shared-future-suggestion-empty-action').click();
    await expect.poll(() => apiState.generatedSuggestionCalls.length).toBe(1);
    await expect(page.getByTestId('shared-future-suggestion-card').first()).toBeVisible();
    await expect(page.getByTestId('shared-future-suggestion-card').first()).toContainText('僅你可見（待審核）');
    await expect(page.getByText('TRANSLATED PARTNER MARKER')).toHaveCount(0);
    await expect(page.getByTestId('shared-future-suggestion-card').first().getByText('你的日記')).toHaveCount(0);
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
    expect(appreciationMoment?.source_id).toBeTruthy();

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

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: '你們的關係地圖',
      }),
    ).toBeVisible();
    await expect(page.getByTestId('relationship-system-cover')).toContainText('已保存的共同真相');
    await expect(page.getByTestId('relationship-system-section-nav')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'Identity / Heart / Story / Future' })).toBeVisible();
    await expect(page.getByTestId('relationship-system-guide-identity')).toBeVisible();
    await expect(page.getByTestId('relationship-system-guide-heart')).toBeVisible();
    await expect(page.getByTestId('relationship-system-guide-story')).toBeVisible();
    await expect(page.getByTestId('relationship-system-guide-future')).toBeVisible();
    await expect(page.getByTestId('relationship-system-guide-heart')).toContainText('分層信任');
    await expect(page.getByTestId('relationship-system-guide-story')).toContainText('記憶支撐');
    await expect(page.getByTestId('relationship-system-guide-future')).toContainText('已保存的共同真相');
    await expectGuidePrimaryHref(page, 'relationship-system-guide-heart', '#heart');
    await expectGuidePrimaryHref(page, 'relationship-system-guide-story', '#story');
    await expectGuideSecondaryHref(page, 'relationship-system-guide-story', '/memory');
    await expectGuideSecondaryHref(page, 'relationship-system-guide-future', '/blueprint');

    await page.getByTestId('relationship-system-guide-identity-primary-action').click();
    await expect(page).toHaveURL(/\/love-map#identity$/);
    await expect(page.getByTestId('relationship-identity-compass-card')).toContainText('Relationship Compass');
    await expect(page.getByTestId('relationship-identity-compass-card')).toContainText('我們是在忙裡仍願意回來對話');
    await expect(page.getByText('TRANSLATED PARTNER MARKER')).toHaveCount(0);
    await expect(page.getByTestId('relationship-compass-suggestion-card').first()).toBeVisible();
    await expect(page.getByText('這是建議更新，不是已保存的共同真相').first()).toBeVisible();
    await page.getByRole('button', { name: '先略過' }).first().click();
    await expect(page.getByTestId('relationship-compass-suggestion-card').first()).toBeVisible();
    await page.getByRole('button', { name: '接受並寫入 Compass' }).first().click();
    await expect(page.getByTestId('relationship-compass-suggestion-card')).toHaveCount(0);
    await page.getByLabel('我們現在是什麼樣的關係').fill('Live compass identity proof：我們願意把重要事情留下來。');
    await page.getByLabel('我們想一起記得哪段故事').fill('Live compass story proof：咖啡、散步和感謝把我們帶回來。');
    await page.getByLabel('接下來一起靠近什麼').fill('Live compass future proof：每個月至少留一晚給彼此。');
    await page.getByRole('button', { name: '保存 Relationship Compass' }).click();
    await expect(page.getByTestId('relationship-identity-compass-updated-by')).toContainText('Alice Chen');
    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByLabel('我們現在是什麼樣的關係')).toHaveValue('Live compass identity proof：我們願意把重要事情留下來。');
    await expect(page.getByTestId('relationship-story-compass-echo-card')).toContainText('Live compass story proof');
    await expect(page.getByTestId('relationship-future-compass-echo-card')).toContainText('Live compass future proof');

    await page.getByTestId('relationship-system-guide-heart-primary-action').click();
    await expect(page).toHaveURL(/\/love-map#heart$/);

    await expect(page.getByTestId('relationship-heart-playbook-card')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-repair-agreements-card')).toBeVisible();
    await expect(page.getByText('我們的 Repair Agreements')).toBeVisible();
    await expect(page.getByText('我的 Heart Care Playbook')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-playbook-partner-card')).toBeVisible();
    await expect(page.getByText('把關係現在的感受、照顧方式與私人理解，放回同一層。')).toBeVisible();
    await expect(page.getByTestId('relationship-heart-weekly-task-card')).toBeVisible();

    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    await page.getByTestId('relationship-system-guide-story-primary-action').click();
    await expect(page).toHaveURL(/\/love-map#story$/);
    await expect(page.getByText('讓真正被留下來的 shared memory，變成可回來看的關係敘事。')).toBeVisible();
    await expect(page.getByText('只引用真的被留下的 shared memory，讓故事能被再次打開，而不是被補寫。')).toBeVisible();

    await page.getByRole('link', { name: '進入 Memory（完整 Story archive）' }).click();
    await expect(page).toHaveURL(/\/memory/);
    await expect(page.getByText('Memory / Shared Archive')).toBeVisible();
    await expect(
      page.getByText('這裡不是檔案庫，也不只是把內容排好。它是 Haven 的完整 Shared Archive；Relationship System 的 Story 只會從這裡挑出真正值得回來重看的故事錨點，而更完整的生活輪廓仍保留在這條長廊裡。'),
    ).toBeVisible();
    await page.getByRole('link', { name: 'Relationship System 故事摘要' }).click();
    await expect(page).toHaveURL(/\/love-map#story$/);

    await page.goto(`${appBaseUrl}/love-map`, { waitUntil: 'domcontentloaded' });
    await page.getByTestId('relationship-system-guide-future-secondary-action').click();
    await expect(page).toHaveURL(/\/blueprint$/);
    await expect(page.getByText('Shared Future / Blueprint', { exact: true })).toBeVisible();
  });
});
