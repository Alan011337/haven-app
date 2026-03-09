# Haven Execution Plan (PR1~PR12)

Generated: 2026-02-22

## Sequencing Rule
1. P0 blockers first: authz/BOLA + observability + billing correctness + launch gate evidence.
2. Then P1: reliability hardening, push completion, growth, gamification, AI quality, ops.
3. Every PR must include: Why / How / What / DoD / Debug checklist / Risk / Rollback / Dry-run.

## PR1 — Minimum Observability + CUJ Event Ingest + BOLA Skeleton
- Scope
  - Add minimal CUJ events ingest endpoint (server-side dedupe + redaction + kill-switch aware).
  - Fill structured logging context baseline (`partner_id/session_id/mode`) without breaking existing logs.
  - Add checklist-expected BOLA artifacts (`docs/security/authz_matrix.md`, `docs/security/owasp_api_top10_mapping.md` alias, aggregated BOLA matrix test skeleton).
- DoD
  - `POST /api/users/events/cuj` exists and is auth-protected.
  - event payload schema/version/dedupe validated; no PII leakage in logs.
  - security gate includes aggregated BOLA matrix smoke test.
- Tests
  - New backend tests for CUJ ingest authz + dedupe + kill-switch.
  - New `backend/tests/security/test_bola_matrix.py`.
- Observability
  - emit structured ingest log with request_id/user_id/partner_id/session_id/mode.
- Rollback
  - feature flag off (`disable_growth_events_ingest=true`) + revert new endpoint.

## PR2 — OWASP/BOLA Completion + Authz Matrix Coverage Expansion
- Scope
  - Expand authorization matrix rows to cover any missing critical read/write routes.
  - Add illegal subject tests for path-id tampering for each core resource.
- DoD
  - matrix + tests map 1:1 to critical endpoints.
  - CI blocks on missing matrix coverage.
- Tests
  - `test_*authorization_matrix*.py` and policy tests.
- Observability
  - denied access audit event consistency checks.
- Rollback
  - additive tests/docs only; revert if false positive.

## PR3 — Launch Readiness Artifact Unification
- Scope
  - Produce one machine-readable launch signoff artifact combining CUJ/OWASP/billing/drills.
  - Link release gate to artifact freshness check.
- DoD
  - launch artifact generated in CI and required for main release.
- Tests
  - artifact schema validator test.
- Observability
  - release gate summary includes artifact status.
- Rollback
  - revert gate step or set allow-missing in PR mode.

## PR4 — Billing Correctness Edge Cases + Parity Tests
- Scope
  - Add missing refund/chargeback/grace/account-hold edge tests.
  - Add entitlement parity test suite (web/android/ios provider-source simulation at server layer).
- DoD
  - edge cases replay-safe and idempotent.
  - parity tests green.
- Tests
  - extend `test_billing_webhook_security.py`, add `test_billing_entitlement_parity.py`.
- Observability
  - reconciliation report includes edge-case counters.
- Rollback
  - keep unsupported transitions blocked; feature flag provider adapters.

## PR5 — SLO/CUJ Runtime Completion
- Scope
  - wire CUJ ingest data into SLI computation snapshots.
  - finalize SLO-01/SLO-02/SLO-03 formulas with machine-readable output.
- DoD
  - `/health/slo` includes CUJ stage metrics.
- Tests
  - health/sli contract tests.
- Observability
  - CUJ rates and latency percentiles emitted.
- Rollback
  - keep old SLI fields; dual output during transition.

## PR6 — Degradation Matrix Runtime Hooks
- Scope
  - enforce journal/card/push degradation paths in runtime and UI copy hooks.
  - provider outage UX response standardization.
- DoD
  - each degradation path test-covered and observable.
- Tests
  - backend degradation behavior tests + frontend smoke for degraded copy.
- Observability
  - degradation mode counters.
- Rollback
  - config toggles to disable degradation override.

## PR7 — Push Delivery Pipeline Completion
- Scope
  - implement push dispatch worker skeleton (provider-agnostic), TTL/retry taxonomy metrics.
  - integrate dry-run sampling before dispatch.
- DoD
  - active subscriptions can be dry-run validated and dispatched safely.
- Tests
  - push dispatch + cleanup idempotency tests.
- Observability
  - delivery success/fail counters + latency.
- Rollback
  - `PUSH_NOTIFICATIONS_ENABLED=false`.

## PR8 — Growth Core (NSM + Experiment Guardrails)
- Scope
  - implement WRM computation job.
  - add experiment assignment guardrails + kill-switch coverage checks.
- DoD
  - WRM exported and queryable; kill-switch applies to CUJ-impact logic.
- Tests
  - NSM job and feature-flag API tests.
- Observability
  - funnel/experiment guardrail metrics.
- Rollback
  - disable growth flags.

## PR9 — Referral/Activation/Re-engagement
- Scope
  - complete referral funnel and activation dashboard ingestion.
  - add re-engagement trigger scaffolding (time capsule/social-share metadata only, no PII content leakage).
- DoD
  - view->signup->bind attribution complete.
- Tests
  - referral API e2e + authz.
- Observability
  - funnel stage drop-off metrics.
- Rollback
  - referral feature flag off.

## PR10 — Advanced Security + Legal Operations
- Scope
  - field-level encryption design skeleton (non-breaking), KMS runbook, device/session hardening baseline.
  - data-rights fire-drill report template and purge/restore playbook linkage.
- DoD
  - security/legal runbooks runnable and tested in dry-run.
- Tests
  - contract tests for key policy/session hardening.
- Observability
  - security drill evidence freshness checks.
- Rollback
  - keep encryption disabled by default behind flag.

## PR11 — AI Personality/Router/Eval
- Scope
  - persona guardrail runtime validator + dynamic context injection skeleton.
  - provider abstraction interface + single-provider fallback + drift detector scaffold.
- DoD
  - AI routing/policy regression tests in CI.
- Tests
  - new ai router + eval tests.
- Observability
  - provider latency/cost/fallback counters.
- Rollback
  - force OpenAI single-provider mode.

## PR12 — Ops Resilience + Admin + Lifecycle + Cost
- Scope
  - CS admin panel minimal backend APIs (least privilege, status-only).
  - backup/restore drill scripts + chaos drill spec.
  - unbind->solo mode skeleton + per-active-couple cost monitor job.
- DoD
  - ops/admin/lifecycle/cost baselines all have runbooks and smoke tests.
- Tests
  - admin authz tests + solo mode tests + backup drill smoke.
- Observability
  - backup health + cost report outputs.
- Rollback
  - admin/solo/cost features behind flags and can be disabled instantly.

## Estimated File Tree Impact
- Backend
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/users.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/schemas/*.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/models/*.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/services/*.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/alembic/versions/*.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/**/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/*.py`
- Frontend
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/lib/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/services/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/app/**/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/e2e/*`
- CI / docs
  - `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/*.yml`
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/security/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/sre/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/ops/*`
  - `/Users/alanzeng/Desktop/Projects/Haven/docs/plan/*`

## Required env vars for local-safe execution
- Backend minimum stubs
  - `DATABASE_URL=sqlite:///./test.db`
  - `OPENAI_API_KEY=test-key`
  - `SECRET_KEY=01234567890123456789012345678901`
  - `ABUSE_GUARD_STORE_BACKEND=memory`
- Frontend minimum stubs
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - `NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws`

