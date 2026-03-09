# Content Engineering Review Policy

> Covers card content generation, review, and quality assurance for all 8 decks.

---

## 1. Deck Content Overview

| Category | ID | Min Cards | Current | Depth Distribution |
|----------|----|-----------|---------|-------------------|
| 日常共感 | DAILY_VIBE | 100 | TBD | 50% L1 / 35% L2 / 15% L3 |
| 靈魂深潛 | SOUL_DIVE | 100 | TBD | 30% L1 / 40% L2 / 30% L3 |
| 安全屋 | SAFE_ZONE | 100 | TBD | 40% L1 / 40% L2 / 20% L3 |
| 時光機 | MEMORY_LANE | 100 | TBD | 45% L1 / 35% L2 / 20% L3 |
| 共同成長 | GROWTH_QUEST | 100 | TBD | 35% L1 / 40% L2 / 25% L3 |
| 深夜話題 | AFTER_DARK | 100 | TBD | 30% L1 / 40% L2 / 30% L3 |
| 最佳副駕 | CO_PILOT | 100 | TBD | 50% L1 / 35% L2 / 15% L3 |
| 愛情藍圖 | LOVE_BLUEPRINT | 100 | TBD | 35% L1 / 40% L2 / 25% L3 |

---

## 2. Content Generation Pipeline

### Step 1: AI-Assisted Draft Generation

Use OpenAI GPT-4o-mini to generate initial drafts:

```bash
cd frontend
npm run seed:cards:generate -- --category AFTER_DARK --count 20 --depth 2
```

Generation prompt template per category:
- **DAILY_VIBE**: Light, fun, daily life questions that build rapport
- **SOUL_DIVE**: Deep introspective questions about values and identity
- **SAFE_ZONE**: Conflict resolution and repair-oriented questions
- **MEMORY_LANE**: Nostalgia and shared memory questions
- **GROWTH_QUEST**: Future planning and personal growth questions
- **AFTER_DARK**: Intimate but respectful relationship questions
- **CO_PILOT**: Practical life coordination questions (chores, travel, decisions)
- **LOVE_BLUEPRINT**: Long-term planning (finances, family, life goals)

### Step 2: Human Review

Each generated card must pass:

1. **Relevance Check**: Does it fit the deck category?
2. **Depth Accuracy**: Is the depth_level appropriate?
3. **Safety Check**: No triggering content without proper framing
4. **Cultural Sensitivity**: Appropriate for Taiwanese/Chinese-speaking audience
5. **Duplicate Check**: Not too similar to existing cards

### Step 3: Special Review for AFTER_DARK

AFTER_DARK content requires additional review:
- Must be intimate but never explicit/pornographic
- Must respect boundaries and consent
- Must not assume relationship milestones
- Must include opt-out language where appropriate
- All L3 cards require manual approval

### Step 4: CO_PILOT Practical Validation

CO_PILOT cards should:
- Reference real-life scenarios (grocery, travel, finance)
- Have actionable outcomes
- Not assume specific living arrangements

---

## 3. Quality Metrics

- **Schema compliance**: All cards have required fields (question, category, depth_level)
- **Tag coverage**: Each card has 1-3 tags from approved tag list
- **Depth distribution**: Matches target ratio per category (within 10%)
- **Uniqueness**: No two cards with >80% text similarity within same category

---

## 4. Validation Command

```bash
cd frontend && npm run seed:cards:validate -- --strict
```

This validates:
- All 8 categories have cards
- Each category meets minimum count
- Schema fields present
- Depth level in [1, 2, 3]
- No empty question text

### Content Review Gate

```bash
cd frontend && npm run seed:cards:review
```

This review gate enforces:
- Per-category min count (default `SEED_MIN_PER_CATEGORY=100`)
- AFTER_DARK blocked-pattern policy (hard fail)
- CO_PILOT practicality hint coverage (warning + report queue)

Optional hard threshold for CO_PILOT practicality:

```bash
cd frontend && CONTENT_REVIEW_MAX_COPILOT_WEAK=180 npm run seed:cards:review
```

---

## 5. Review Cadence

- **Pre-launch**: Full review of all 800+ cards
- **Monthly**: Spot-check 10% of each category
- **On-demand**: After any batch generation or AI model change
