# Editorial Differentiation Plan: "Small Wins" DAILY_VIBE Card Family

## Context

Haven is a zh-TW relationship OS. The Home screen offers a "輕鬆聊" (light chat) rotation of DAILY_VIBE depth-1 cards. Five cards in the "small wins / small achievement" family currently feel too similar — all essentially ask "did you accomplish a small thing today?" with only cosmetic variation.

**File to modify**: `/Users/alanzeng/projects/Haven-local/frontend/scripts/data/cards.json`

Cards affected (by id and approximate line):
1. `550e8400-e29b-41d4-a716-446655440009` (~line 138)
2. `550e8400-e29b-41d4-a716-446655440213` (~line 3606)
3. `770e8400-e29b-41d4-a716-446655443008` (~line 12109)
4. `05169361-9685-4cf9-80c4-78d4ca80f7d2` (~line 23667)
5. `523ce00a-c553-464b-ac85-5cc017294162` (~line 25175)

**Fields to change**: title, description, question, tags ONLY.  
**Fields to preserve exactly**: id, deck_id, category, depth_level, difficulty_level, is_ai_generated, created_at.

---

## Chosen Differentiation Axis: "Where the win lives" (Relational Locus)

### Why this axis

The "small wins" family shares a single theme: daily micro-achievement. The prior batch patterns offer precedent:
- **Temporal axis** (past/present/future) worked for the 顏色 cluster because color-as-metaphor naturally varies across time frames.
- **Emotional axis** (tweak/celebrate/wonder) worked for 改變 because change invites different emotional stances.
- **Modality axis** (headline/chapter/word/emoji) worked for today-summary because format variation is the differentiator.
- **Functional axis** (act/presence/retrospective) worked for gratitude because gratitude has distinct modes.

For "small wins," temporal axis would be weak (you cannot meaningfully ask about a future small win vs. a past one at depth-1 without drifting into GROWTH_QUEST territory). Modality axis would feel forced (asking "describe your win as an emoji" is gimmicky for this theme). Emotional axis partially works but risks overlap with the existing 今日小確幸 card nearby.

**The "relational locus" axis works best** because it asks: where does this feeling of competence or accomplishment actually sit in your life? Each card targets a different *domain* of daily life where a win registers differently:

1. **Body / self-care** — the win is physical, you showed up for your own body
2. **Reluctance overcome** — the win is willpower, you did something you resisted
3. **Someone else noticed** — the win is relational, someone saw you being good at something
4. **Quiet competence** — the win is internal craft, you handled something well and only you know
5. **Endurance** — the win is survival, you got through something hard without breaking

This axis guarantees that each card guides toward a *different memory search* in the user's day. A user encountering card 1 on Monday thinks about their body; card 3 on Wednesday thinks about a social moment; card 5 on Friday thinks about resilience. No two cards trigger the same mental retrieval.

### Why alternatives were rejected

| Alternative axis | Reason rejected |
|---|---|
| Temporal (past/present/future win) | "Future small win" is nonsensical at depth-1; becomes planning, not reflection |
| Scale (tiny/medium/big) | All 5 cards are already supposed to be "small" — scale variation contradicts the family identity |
| Modality (headline/emoji/score for your win) | Gimmicky for achievement; works for summary but not for self-affirmation |
| Emotional stance (proud/surprised/relieved) | Better than scale, but still asks the same retrieval ("what did you do?") and just colors the emotion differently — weaker separation |

---

## The 5 Redesigned Cards

### Card 1 (id: 550e8400-e29b-41d4-a716-446655440009, ~line 138)

**Angle label**: Body / self-care win

- **New title**: 身體有被照顧到
- **New description**: 有時候光是好好對待自己的身體，就已經很了不起。
- **New question**: 今天你有做什麼「對身體好的事」嗎？不管是有吃飯、有伸展、有早點睡——什麼都算。
- **New tags**: 身體, 自我照顧, 日常
- **Why it's distinct**: This is the only card that anchors the win in physical self-care rather than task completion or emotional resilience, prompting the user to scan their day for bodily kindness.

### Card 2 (id: 550e8400-e29b-41d4-a716-446655440213, ~line 3606)

**Angle label**: Reluctance overcome

- **New title**: 不想做但還是做了
- **New description**: 有些事光是「開始」就已經贏了。
- **New question**: 今天有沒有一件你本來很不想面對，但最後還是硬著頭皮做了的事？做完之後感覺怎樣？
- **New tags**: 意志力, 拖延, 突破
- **Why it's distinct**: This is the only card focused on overcoming internal resistance — the win is not the task itself but the act of starting despite reluctance, and it adds a follow-up feeling probe that the others lack.

### Card 3 (id: 770e8400-e29b-41d4-a716-446655443008, ~line 12109)

**Angle label**: Witnessed competence

- **New title**: 被別人看見的瞬間
- **New description**: 有時候被人誇一句，比自己誇自己一百次還有用。
- **New question**: 今天有沒有任何人（同事、朋友、路人都算）對你說了一句讓你覺得「欸，我好像還不錯」的話？
- **New tags**: 被看見, 肯定, 人際
- **Why it's distinct**: This is the only card that locates the win in someone else's recognition rather than self-assessment, shifting reflection from introspection to relational awareness.

### Card 4 (id: 05169361-9685-4cf9-80c4-78d4ca80f7d2, ~line 23667)

**Angle label**: Quiet competence

- **New title**: 只有你自己知道的厲害
- **New description**: 有些事做得好，只有自己心裡清楚。
- **New question**: 今天有沒有一件事，你處理得很好，但大概沒有人會注意到？說來聽聽，讓我當那個知道的人。
- **New tags**: 默默努力, 細節, 被懂
- **Why it's distinct**: This is the only card that specifically targets invisible labor and unrecognized skill — the direct inverse of Card 3 — and adds an intimate invitation ("let me be the one who knows") that reinforces Haven's couple-OS identity.

### Card 5 (id: 523ce00a-c553-464b-ac85-5cc017294162, ~line 25175)

**Angle label**: Endurance / survival win

- **New title**: 今天撐過來了
- **New description**: 有時候「沒有崩潰」本身就是一種成就。
- **New question**: 今天有沒有什麼讓你覺得很累或很難的事？你是怎麼撐過去的？
- **New tags**: 韌性, 撐住, 支持
- **Why it's distinct**: This is the only card that frames the win as endurance rather than accomplishment — surviving difficulty counts — and the two-part question structure (what was hard + how did you cope) invites storytelling rather than a one-word answer.

---

## Differentiation Matrix

| Card | Locus of win | Mental retrieval | Tone | Relationship to partner |
|------|-------------|-----------------|------|------------------------|
| 1 — 身體有被照顧到 | Body | "Did I take care of myself physically?" | Gentle, permissive | Partner witnesses self-care |
| 2 — 不想做但還是做了 | Willpower | "What did I resist but do anyway?" | Proud, slightly humorous | Partner cheers the push |
| 3 — 被別人看見的瞬間 | Social recognition | "Did anyone affirm me today?" | Warm, surprised | Partner learns what others see |
| 4 — 只有你自己知道的厲害 | Internal craft | "What did I handle well invisibly?" | Intimate, confiding | Partner becomes the witness |
| 5 — 今天撐過來了 | Endurance | "What was hard and how did I survive it?" | Tender, supportive | Partner offers comfort |

---

## Implementation Notes

### Edit scope
- Only 4 fields per card: `title`, `description`, `question`, `tags`
- No structural field changes
- Card 5 has `difficulty_level: 2` (slightly higher than the others at 1) — preserve this as-is

### Tag design
- Each card gets 3 tags, all distinct across the family
- No card reuses 成就感 or 肯定 (the old tags that made everything blur together)
- Tags reflect the new angle: 身體/自我照顧, 意志力/拖延/突破, 被看見/人際, 默默努力/細節/被懂, 韌性/撐住/支持

### Validation
- After editing, run `cd frontend && npm run seed:cards:validate -- --strict` to verify schema compliance
- The seed script (`frontend/scripts/seed.ts`) validates: required fields present, depth_level in [1,2,3], non-empty question text, valid category
- Tags are free-form strings (no approved-list constraint in the validator), so new tags are safe

### Adjacency check
- The nearby 今日小確幸 card (id: 64b78843, ~line 25095) asks about small happy moments — this is a happiness/gratitude card, not achievement, so no new overlap is introduced
- The 感恩時刻 card (id: 550e8400...0013, ~line 210) is about gratitude — again distinct from all 5 new angles
- The 成就感來源 card (id at ~line 1978) is in a different depth level and asks about sources of fulfillment generally, not daily micro-wins

---

## Critical Files for Implementation

1. `/Users/alanzeng/projects/Haven-local/frontend/scripts/data/cards.json` — the card data file; all 5 edits happen here
2. `/Users/alanzeng/projects/Haven-local/frontend/scripts/seed.ts` — the seed/validation script to run after edits
3. `/Users/alanzeng/projects/Haven-local/frontend/src/lib/home-daily-depth.ts` — defines the 輕鬆聊 depth-1 presentation context these cards appear in
4. `/Users/alanzeng/projects/Haven-local/docs/content/content-review-policy.md` — content quality policy to verify compliance
5. `/Users/alanzeng/projects/Haven-local/frontend/src/lib/deck-meta.ts` — DAILY_VIBE deck metadata for category context
