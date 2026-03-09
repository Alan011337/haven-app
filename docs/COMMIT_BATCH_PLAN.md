# Commit Batch Plan (P0 MVP)

> Goal: split current working tree into reviewable, low-risk batches.  
> Rule: each batch ships one concern + has test/rollback instructions.

## Batch 1 — Launch Gate + DoD Process

- **Scope**: P0-A/P0-B process landing
- **Files**
  - `docs/P0-DOD-TEMPLATE.md`
  - `docs/P0-LAUNCH-GATE.md`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `CONTRIBUTING.md`
  - `docs/P0-MVP-REPO-INVENTORY.md`
  - `docs/P0-MVP-TODO.md`
  - `docs/FINAL_P0_SIGNOFF.md`
- **Risk**: low (docs/process only)
- **How to test**
  - Open PR page and verify template checklist appears
  - Review links in `docs/P0-LAUNCH-GATE.md`
- **Rollback**
  - Revert listed docs/template files

## Batch 2 — Trust Docs (Security / Runbook / Rights / AI Policy)

- **Scope**: P0-E/P0-G/P0-H policy docs as launch-minimal artifacts
- **Files**
  - `SECURITY.md`
  - `RUNBOOK.md`
  - `DATA_RIGHTS.md`
  - `POLICY_AI.md`
  - `docs/legal/PRIVACY_POLICY.md`
  - `docs/legal/TERMS_OF_SERVICE.md`
- **Risk**: low (docs only, but affects operational expectations)
- **How to test**
  - Validate links resolve from launch gate/readme
  - Verify each doc maps to code/test/CI paths
- **Rollback**
  - Revert docs if wording/policy needs correction

## Batch 3 — Backend Observability + PII Redaction

- **Scope**: P0-H runtime hardening
- **Files**
  - `backend/app/main.py` (mount request context middleware)
  - `backend/app/core/log_redaction.py`
  - `backend/app/services/notification.py` (redacted email logging)
  - `backend/tests/test_log_redaction.py`
- **Risk**: medium (touches runtime middleware and notification logs)
- **How to test**
  - `cd backend && python -m pytest -q -p no:cacheprovider tests/test_log_redaction.py`
  - call any API and verify `x-request-id` response header exists
- **Rollback**
  - Revert middleware mount + redaction callsites

## Batch 4 — AI Contract + Safety Regression Gates

- **Scope**: P0-I schema/safety enforcement
- **Files**
  - `backend/tests/test_ai_schema_contract.py`
  - `backend/tests/test_ai_schema_fuzz.py`
  - `backend/scripts/security-gate.sh`
- **Risk**: medium (CI stricter; may expose existing schema drift)
- **How to test**
  - `cd backend && ./scripts/security-gate.sh`
  - confirm tests listed in gate output include schema + safety + fuzz
- **Rollback**
  - Revert added tests and gate entries

## Batch 5 — Frontend Legal/Age + Library UX

- **Scope**: P0-D/P0-G user-facing UX and legal gating
- **Files**
  - `frontend/src/app/register/page.tsx`
  - `frontend/src/app/legal/terms/page.tsx`
  - `frontend/src/app/legal/privacy/page.tsx`
  - `frontend/src/app/decks/page.tsx`
- **Risk**: medium (changes user entry flow and deck UI layout)
- **How to test**
  - Register page: consent checkbox required before submit
  - `/legal/terms` and `/legal/privacy` pages render
  - `/decks` layout on mobile/tablet/desktop
- **Rollback**
  - Revert register/decks/legal pages to prior version

## Batch 6 — E2E and Release Gate Wiring

- **Scope**: P0-I CUJ e2e + local/CI execution hooks
- **Files**
  - `frontend/package.json`
  - `frontend/package-lock.json`
  - `frontend/playwright.config.ts`
  - `frontend/e2e/smoke.spec.ts`
  - `frontend/.gitignore`
  - `.github/workflows/release-gate.yml`
  - `scripts/release-gate.sh`
  - `README.md`
- **Risk**: medium-high (CI behavior changes; e2e on main is required)
- **How to test**
  - local smoke: `cd frontend && npm run test:e2e` (app running)
  - full gate: `./scripts/release-gate.sh`
  - full gate with e2e: `RUN_E2E=1 ./scripts/release-gate.sh`
- **Rollback**
  - Revert workflow/script e2e wiring; keep tests in repo if needed

---

## Notes on Existing Dirty Tree

- `frontend/src/components/features/PartnerJournalCard.tsx` appears as pre-existing modified file.
- `frontend/src/components/features/ForceLockBanner.tsx`, `SafetyTierGate.tsx`, `frontend/src/lib/safety-policy.ts`, `docs/ops/`, `docs/safety/` were already present as untracked/ongoing items in this working period.
- Keep those changes isolated unless intentionally included in the above batches.
