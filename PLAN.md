# Haven P1 Delivery Plan (Phase 0)

## 1) System Inventory (Current State)

### Architecture
- Frontend: Next.js App Router + TypeScript (`/frontend/src/app/*`).
- Backend: FastAPI + SQLModel + Alembic (`/backend/app/*`, `/backend/alembic/*`).
- DB: Postgres-compatible schema, local SQLite for gate/testing.
- Auth/session: JWT bearer + WebSocket first-message auth.
- Realtime: WebSocket events + in-app polling fallback.
- Billing: existing state machine + webhook verify + ledger/reconciliation tables (`/backend/app/api/routers/billing.py`, `/backend/app/models/billing.py`).
- CI gates: security gate, release gate, SLO burn-rate check already present (`/.github/workflows/release-gate.yml`).

### Data/Control Flows
- Journal flow: submit -> persist -> AI analyze -> notify partner.
- Deck flow: draw/respond -> session reconciliation -> unlock/reveal.
- Billing flow: command/webhook -> idempotency logs -> entitlement + ledger.
- Health/SLO flow: `/health` + `/health/slo` provides WS SLI/Burn-rate snapshot.

### Existing Gaps vs Requested P1
- Missing standardized P1 docs bundle under `docs/sre`, `docs/push`, `docs/ai`, `docs/billing` (P1 format).
- Missing release-freeze gate contract tied to error budget policy.
- Missing production synthetic CUJ job/evidence pipeline.
- Push (Web Push + VAPID lifecycle) is not implemented.
- Growth feature flag/experiment/referral infra only partially scaffolded.
- AI router/provider abstraction and drift detector not fully implemented.

## 2) Risk Register
- Payment correctness risk: webhook replay/partial failure/reconciliation drift.
- Migration risk: historical Alembic baseline incompatibility on fresh sqlite.
- Security risk: residual logs with identifiers/PII across edge paths.
- Deletion risk: export/erase graph consistency and purge lifecycle drift.
- Release risk: no explicit error-budget freeze gate contract in pipeline.
- Ops risk: no consolidated restore/chaos drill automation package.

## 3) Dependencies
- Stripe: webhook secret + checkout/portal credentials.
- Push provider/browser stack: VAPID keypair + Service Worker runtime.
- Metrics stack: current in-app snapshots; needs durable sink/alerts contract.
- Feature flags: server-side kill-switch + rollout controls.
- Queue/background execution: webhook/notification asynchronous worker policy.
- CI secrets: SLO gate URL/token, billing/push provider test keys.

## 4) PR Slicing (PR1~PR8)

### PR1 — SRE Foundation: SLO docs + error budget freeze gate + CUJ synthetics skeleton
- Scope: P1-A baseline contracts and enforceable gates.
- DoD:
  - `docs/sre/slo.md`, `docs/sre/error-budget.md`, `docs/sre/alerts.md`, `docs/sre/canary.md`, `docs/sre/degradation.md`, `docs/sre/postmortem.md` exist and are cross-linked.
  - Add machine-readable `docs/sre/error-budget-status.json`.
  - Add `backend/scripts/check_error_budget_freeze_gate.py` and tests.
  - Add `scripts/synthetics/*` CUJ probe skeleton + scheduled workflow.
  - Release gate runs burn-rate + error-budget freeze gate.
- Tests:
  - `pytest backend/tests/test_error_budget_freeze_gate.py`
  - `pytest backend/tests/test_cuj_synthetics.py`
  - existing `test_slo_burn_rate_gate.py`
- Rollback:
  - revert workflow/script/doc changes; set gate step to optional.
- Observability:
  - synthetic evidence artifact in `docs/sre/evidence/`.

### PR2 — Billing correctness hardening
- Scope: P1-B entitlement source-of-truth contract, webhook async pipeline skeleton, reconciliation delta policy.
- DoD:
  - billing state machine doc + correctness matrix.
  - idempotent webhook queue handler skeleton.
  - ledger-first reconciliation report includes repair plan output.
- Tests:
  - webhook signature/idempotency/replay tests.
  - entitlement parity server tests.
- Rollback: disable new worker via flag; keep sync fallback.
- Observability: billing correctness counters + reconciliation diff report.

### PR3 — Notification multi-channel + Web Push skeleton
- Scope: P1-C push subscription model, lifecycle states, abuse budget + cleanup job.
- DoD:
  - subscription table/model + migration.
  - service worker registration path + backend VAPID contract doc.
  - invalid subscription cleanup + dry-run sampler.
- Tests:
  - subscription CRUD/authz + cleanup replay-safe tests.
- Rollback: feature flag off (`PUSH_ENABLED=false`) and disable jobs.
- Observability: delivery/failure taxonomy metrics docs.

### PR4 — Growth infra + feature flags + referral funnel skeleton
- Scope: P1-D NSM/event taxonomy, experiment primitives, referral landing instrumentation.
- DoD:
  - event governance doc + versioning/PII rules.
  - server-side feature flag + kill-switch API contract.
  - referral funnel endpoints/events (`view->signup->bind`).
- Tests:
  - authz, dedupe, attribution integrity tests.
- Rollback: disable rollout flags and referral routes.
- Observability: activation dashboard query specs.

### PR5 — Gamification reliability/anti-cheat
- Scope: P1-E streak/love-bar/levels model + replay protection.
- DoD:
  - streak update logic based on pair completion.
  - idempotent scoring token to block replay.
- Tests:
  - multi-device replay tests + streak edge-day tests.
- Rollback: scoring engine flag off, retain read-only counters.
- Observability: streak computation audit counters.

### PR6 — Security + Legal data-rights operations
- Scope: P1-F + P1-G (key runbook/device hardening/data-rights drill automation).
- DoD:
  - key rotation/KMS runbook.
  - session/device hardening contract.
  - monthly fire-drill script + templates for access/export/erase.
- Tests:
  - data-rights workflow contract tests.
  - session hardening regression tests.
- Rollback: disable hardening enforcement via config gates.
- Observability: drill evidence artifacts + audit trail checks.

### PR7 — AI personality/router/eval/drift
- Scope: P1-H + P1-I provider abstraction and policy guardrails.
- DoD:
  - persona policy doc + dynamic context injection contract.
  - provider router interface + budget guard + fallback.
  - golden set regression gate + drift detector skeleton.
- Tests:
  - router failover + schema/safety regressions.
- Rollback: force single provider mode flag.
- Observability: provider latency/cost/fallback counters.

### PR8 — Ops resilience + CS panel + breakup/solo + unit economics
- Scope: P1-J/K/M/N operational closure.
- DoD:
  - CS admin least-privilege endpoints.
  - backup/restore/chaos drill docs + scripts.
  - unbind->solo mode data/UX behavior.
  - per-active-couple cost monitor spec + job.
- Tests:
  - admin authz matrix + solo-mode behavior tests.
- Rollback: panel disable flag + solo-mode revert gate.
- Observability: restore drill evidence + unit economics report.

## 5) Proposed File Tree (Planned)
```text
PLAN.md
PLAN.json
RELEASE_CHECKLIST.md

docs/
  sre/
    slo.md
    error-budget.md
    error-budget-status.json
    alerts.md
    postmortem.md
    canary.md
    degradation.md
    synthetic-cuj.md
    evidence/
  billing/
    monetization-engine.md
    store-compliance.md
  push/
    vapid.md
    observability.md
  growth/
    nsm.md
    activation-dashboard.md
  ai/
    persona.md
    router.md
  security/
    keys.md
  legal/
    data-rights.md
  ops/
    backups.md
    restore-drill.md
    chaos-drill.md

scripts/
  synthetics/
    run_cuj_synthetics.py

backend/scripts/
  check_error_budget_freeze_gate.py

backend/tests/
  test_error_budget_freeze_gate.py
  test_cuj_synthetics.py

.github/workflows/
  cuj-synthetics.yml
  release-gate.yml (update)
```

## 6) Execution Notes
- All high-risk capabilities (billing/webhook/deletion) stay behind feature flags.
- Each PR includes explicit rollback and dry-run modes.
- No destructive migration introduced without downgrade/runbook.
