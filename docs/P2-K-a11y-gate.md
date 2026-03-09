# P2-K: A11y automated gate

## Overview

The release gate runs **@axe-core/playwright** on core pages as part of the frontend e2e job. Any WCAG 2.2 Level A/AA violation fails the run.

## Where it runs

- **CI**: `.github/workflows/release-gate.yml` → job `frontend-e2e` → step "Run e2e (smoke + a11y axe)" runs `npm run test:e2e`, which includes `e2e/a11y.spec.ts`.
- **Local**: `cd frontend && npm run test:a11y` (axe only), or `npm run test:e2e` (smoke + axe).

## Core pages (axe scan)

| Path | Name |
|------|------|
| `/` | Home |
| `/login` | Login |
| `/register` | Register |
| `/decks` | Decks library |
| `/legal/terms` | Legal terms |
| `/legal/privacy` | Legal privacy |

## DoD alignment

- **WCAG 2.2 AA**: axe tags `wcag2a`, `wcag2aa` (see `e2e/a11y.spec.ts`).
- **Drag/Swipe alternatives**: Implemented in UI (e.g. TarotCard prev/next buttons); not asserted by axe.
- **Target size 24x24**: Design tokens and components enforce minimum; axe reports where applicable.

## Rollback

To temporarily skip a11y in CI, run only smoke: change the e2e step to `npx playwright test e2e/smoke.spec.ts`. Revert that change to restore the gate.
