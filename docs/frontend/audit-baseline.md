# Frontend audit baseline

Last run: 2026-02-23 (Haven Frontend Audit — Optimisation Plan).  
Re-verified: 2026-02-23 (Frontend Full Audit and Phased Optimization): lint 0, typecheck 0, build 0.

## Baseline (frontend)

| Command        | Exit | Notes                                      |
|----------------|------|--------------------------------------------|
| `npm run lint` | 0    | eslint + console-error + route-collision   |
| `npm run typecheck` | 0 | After clean: `rm -rf .next/types .next/cache` if TS6053 cache-life.d.ts |
| `npm run build` | 0  | next build --webpack                       |

## npm audit (read-only, no fix applied)

| Result | Count |
|--------|--------|
| Exit   | 1     |
| High   | 1 (minimatch ReDoS — GHSA-3ppc-4f35-3m26) |
| Critical | 0  |

Fix available via `npm audit fix`; not applied per audit plan (Need decision: dependency upgrades).

## Batches completed this run

1. **Batch 1** — Added focus-visible to Links: analysis, login, register, decks, legal/terms.
2. **Batch 2** — Added focus-visible to DailyCard.tsx two buttons (“抽取今日話題”, “喜歡這次的深度對話嗎？”).
3. **Batch 3** — This baseline + audit record.

## Batches completed (Frontend Full Audit 2026-02-23)

1. **Batch 1** — Added focus-visible to decks page “繼續 [牌組]” Link (`app/decks/page.tsx`).
2. **Batch 2** — Re-verified baseline (lint, typecheck, build); no code fix needed; updated this doc.
3. **Batch 3** — Added missing aria-labels to icon-only Links: decks page back link (`aria-label="返回首頁"`), decks/history page back link (`aria-label="返回牌組"`); added focus-visible to history back link.

## Post motion-cleanup (2026-02-23)

- **Motion**: All interactive/transition motion migrated to Haven tokens (`duration-haven-fast` / `duration-haven` + `ease-haven`). Long durations (500/700/1000ms) for reveal/ritual/ambient are documented in-code as intentional exceptions.
- **Focus-visible**: Applied across interactive elements (buttons, links, inputs, selects) per haven-ui; no remaining `focus:` for ring/outline.
- **Baseline**: lint 0, typecheck 0, build 0 (re-verified 2026-02-23).

## Optional / need-decision (from audit plan)

- **Bundle analyzer**: Add `@next/bundle-analyzer` (or one-off analysis); decision required.
- **npm audit**: 1 high (minimatch ReDoS); fix via `npm audit fix` when dependency upgrade is approved.
- **Server component boundary**: Split `app/page.tsx` so some subtrees are server components; scope/priority decision required.
- **Maintainability**: DailyCard.tsx ~548 lines — extract subcomponents only with explicit decision.
- **TypeScript**: Reduce `: any` usage (run `rg ": any\b" frontend/src`); incremental batches with decision.
