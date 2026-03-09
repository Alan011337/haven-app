# Phase 0 — Repo Discovery

Generated: 2026-02-22 (audit handoff). Refreshed: 2026-02-21 (evidence-driven audit run).

## A) Repo structure and stack

| Layer | Tech | Paths |
|-------|------|--------|
| **Frontend** | Next.js 16.1.6, React 19.2.3, TypeScript 5, Tailwind 4 | `frontend/src/app/`, `frontend/src/components/`, `frontend/src/services/`, `frontend/src/lib/` |
| **Backend** | FastAPI, SQLModel, Pydantic 2, Alembic | `backend/app/main.py`, `backend/app/api/`, `backend/app/services/`, `backend/app/models/` |
| **DB** | PostgreSQL (Supabase), Alembic migrations | `backend/alembic/versions/*.py` (27 migrations) |
| **CI / gates** | GitHub Actions, security-gate.sh | `.github/workflows/`, `backend/scripts/security-gate.sh`, `scripts/release-gate-local.sh` |
| **Docs / runbooks** | Markdown, JSON policies | `RUNBOOK.md`, `SECURITY.md`, `DATA_RIGHTS.md`, `POLICY_AI.md`, `docs/security/`, `docs/ops/`, `docs/sre/` |

## B) DB and migration tooling

- **DB**: PostgreSQL (via Supabase); connection via `DATABASE_URL` in `backend/.env`.
- **Migrations**: Alembic 1.18.x; versions under `backend/alembic/versions/`.
- **Evidence**: 27 migration files (e.g. `4106a6e78900_init_db_with_users_and_journals.py`, `b2c3d4e5f6a7_add_consent_receipts_and_user_age_fields.py`, `e5f6a7b8c9d0_add_billing_entitlement_and_ledger_tables.py`).

## C) Tests and lint

| Command | Location | Purpose |
|---------|----------|---------|
| Backend tests | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest` (or `pytest` if venv active) | Unit/integration/contract tests |
| Security gate | `cd backend && bash scripts/security-gate.sh` | 39+ checks, 67+ pytest suites, contract/matrix checks |
| Frontend build | `cd frontend && npm run build` | Next.js production build |
| Frontend lint | `cd frontend && npm run lint` | ESLint + console-error + route-collision |
| Frontend typecheck | `cd frontend && npm run typecheck` | `node scripts/typecheck.mjs` |
| E2E | `cd frontend && npm run test:e2e` | Playwright (e2e/smoke.spec.ts, etc.) |

## D) Branch and git status

- **Branch**: `feat/audit-p0-p1-completion`
- **Status**: May be dirty (modified: docs, evidence JSON; untracked: e.g. `backend/_verify_syntax.py`). **If dirty before Phase 2**: Option 1 — create branch and commit WIP snapshot; Option 2 — stash and proceed on clean base. Do not destroy local work.
- **Verify**: `git branch --show-current && git status --short`

## E) Risk smells (from audit)

- Duplicate/stray files: **REMOVED** (main 2.py, package 2.json, package-lock 2.json deleted previously).
- Structured logging: `request_id`, `user_id`, `partner_id`, `session_id`, `mode` injected via middleware; keep new routes on same contract.

## F) Key evidence anchors (verified)

- **Health (UptimeRobot-ready)**: `backend/app/main.py` — `@app.get("/health")` returns JSON with `status`, `checks`, `sli`; 503 when degraded.
- **8 decks (content model)**: `backend/app/models/card.py` — `CardCategory` enum (lines 17–25): DAILY_VIBE, SOUL_DIVE, SAFE_ZONE, MEMORY_LANE, GROWTH_QUEST, AFTER_DARK, CO_PILOT, LOVE_BLUEPRINT.
- **Email notification wiring**: `queue_partner_notification` in `backend/app/services/notification.py`; called from `backend/app/api/journals.py`, `backend/app/api/routers/cards.py`, `backend/app/api/routers/card_decks.py`.
- **Safety UI policy v1**: `docs/safety/safety-ui-policy-v1.md`, `docs/safety/safety-ui-policy-v1.json`; backend contract/tests reference tier 0/1/2/3.

## G) How to run (verification)

| Action | Command |
|--------|--------|
| Backend tests | `cd backend && PYTHONPATH=. pytest` (or `python3 -m pytest` if venv active) |
| Security gate | `cd backend && bash scripts/security-gate.sh` |
| Frontend build | `cd frontend && npm run build` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend typecheck | `cd frontend && npm run typecheck` |
| E2E (Playwright) | `cd frontend && npm run test:e2e` |
