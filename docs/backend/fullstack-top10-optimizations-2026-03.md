# Haven Full-Stack Top 10 Optimizations (2026-03)

## Scope
This bundle operationalizes the top 10 ROI optimizations with low-risk, testable contracts:

1. API contract single source-of-truth gate.
1. Frontend contract type generation from API inventory (auto-check in release gate).
2. Mutating API idempotency coverage gate.
3. Durable outbox SLO warning gate.
4. AI runtime determinism gate.
5. Observability payload contract gate.
6. BOLA baseline coverage gate.
7. Rate-limit scope policy contract.
8. Frontend optimistic-sync degradation helper.
9. Data-rights fire-drill snapshot automation.
10. Growth + unit economics snapshot automation.
11. Duplicate suffix file gate (`* 2.*`) to prevent accidental parallel copies.
12. Supply-chain workflow contract (pip-audit / npm audit / gitleaks).

## New Scripts
- `backend/scripts/check_api_contract_sot.py`
- `backend/scripts/check_write_idempotency_coverage.py`
- `backend/scripts/check_outbox_slo_gate.py`
- `backend/scripts/check_ai_runtime_gate.py`
- `backend/scripts/check_observability_payload_contract.py`
- `backend/scripts/check_bola_coverage_from_inventory.py`
- `backend/scripts/check_rate_limit_policy_contract.py`
- `backend/scripts/run_data_rights_fire_drill_snapshot.py`
- `backend/scripts/run_growth_cost_snapshot.py`
- `backend/scripts/run_openapi_inventory_snapshot.py`

## Release Gate Wiring
`/scripts/release-gate-local.sh` now runs these checks and records summaries into `/tmp/*-summary-local.json`.

## Reliability Preflight (Local + CI)
- `scripts/check-worktree-materialization.py` is now wired into release gate before backend bootstrap.
- On local/dev it can degrade (warn) when iCloud dataless files are detected; on protected branches/CI it fails closed.

## Frontend Resilience
`frontend/src/lib/optimistic-sync.ts` stores bounded local fallback operations when journal creation fails, and `frontend/src/hooks/queries/useJournalMutations.ts` now records a safe fallback entry on mutation error.

## Frontend API Contract Types
- Generator: `frontend/scripts/generate-api-contract-types.mjs`
- Output: `frontend/src/types/api-contract.ts`
- Gate hook: `npm run contract:types:check` in `scripts/release-gate-local.sh`

## Verify
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
ruff check .
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_optimization_scripts_contract.py \
  tests/test_frontend_resilience_hook_contract.py

cd /Users/alanzeng/Desktop/Projects/Haven
SECURITY_GATE_PROFILE=fast bash backend/scripts/security-gate.sh
SKIP_FRONTEND_TYPECHECK=1 SKIP_MOBILE_TYPECHECK=1 bash scripts/release-gate-local.sh
```

## Second-Pass Implementation Notes (2026-03-06)
The following high-ROI hardening items were applied in a single pass:

1. AI router runtime helper extraction (`ai_router_runtime_helpers.py`) to reduce `ai_router.py` coupling.
2. Cards router helper extraction (`card_helpers.py`) for category normalization and day-range logic.
3. Billing binding helper extraction (`billing_binding_helpers.py`) for user/binding resolution and upsert.
4. Home data in-flight request dedupe in `useHomeData` to reduce duplicate status refreshes.
5. Frontend API fallback utility centralization (`getWithFallback`) for resilient reads.
6. Added resilience-focused Playwright specs (`frontend/e2e/core-loop-resilience.spec.ts`).
7. Supply-chain workflow tightened: internal PR fail-closed; fork PR remains relaxed.
8. CI concurrency added to release/supply-chain workflows to reduce stale duplicate runs.
9. Observability live contract script + gate wiring (`check_observability_live_contract.py`).
10. Makefile release ergonomics: `release-check`, `release-check-full`, `security-gate-fast`, `evidence-clean`.

## Third-Pass Hardening Notes (2026-03-06)
Additional full-stack hardening updates completed:

1. `release-gate-local.sh` now has environment-aware gate policy (`dev`/`alpha`/`prod`), with alpha/prod promoting runtime checks and frontend e2e to required.
2. Local CUJ synthetic SLO payload now includes observability runtime keys (`sli.notification_runtime`, `sli.dynamic_content_runtime`, `checks.notification_outbox_depth`).
3. Local data-retention bundle defaults to `sqlite:///./test.db` in dev mode to avoid external DB DNS coupling.
4. Outbox health snapshot in local gate can reuse `/tmp/cuj-health-payload-local.json` as fallback source.
5. Frontend e2e wrappers now support passthrough spec args and hard timeout boundaries.
6. `api-transport.ts` introduced to centralize `apiGet/apiPost/apiDelete/getWithFallback`.
7. Home and Daily Card polling now share `startAdaptivePolling` helper to reduce duplicated timer/context logic.
8. Backend PostHog capture adds bounded in-flight guard and transient retry/backoff.
9. Duplicate suffix checker now scans tracked + untracked files by default.
10. Git hook installer script added (`scripts/install-git-hooks.sh`) and Makefile target (`install-git-hooks`) for local prevention.
