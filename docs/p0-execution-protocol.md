# Haven v2 P0 Execution Protocol

Last updated: 2026-02-17

Machine trackers (parseable sources):
- `docs/p0-machine-tracker.yaml` (P0 critical path)
- `docs/roadmap-machine-tracker.yaml` (P0/P1/P2 full roadmap)
- updater script: `./scripts/update-p0-tracker.sh`

## 1) Priority Protocol

- P0 (Blocker): Core closed-loop integrity (Bind/Ritual/Journal/Unlock), reliability, security/privacy/legal, billing correctness.
- P1: Strong retention and growth levers (push, sharing, quests, reports).
- P2: polish and advanced experiential upgrades.

No P1/P2 work starts if a P0 launch-gate item is red.

## 2) Critical Path Graph

1. Release Gate + deterministic tests
2. Security and authorization gates (OWASP/BOLA focus)
3. Data rights + consent foundation (access/export/erase)
4. Billing correctness (idempotency, webhook verify, ledger reconciliation)
5. Launch readiness gate (SLI green + incident drill pass)

## 3) Definition of Done (DoD) Template

Every task must include all items below:

1. Success definition
2. Failure/degraded behavior
3. Observability (log + metric + trace point)
4. Tests (unit + integration/e2e if applicable)
5. Security/privacy checks
6. Rollback strategy

## 4) P0 Workboard (Now)

### P0-A: Release Gate Baseline
- Status: Done locally (pending first CI run)
- Scope:
  - GitHub Actions gate for backend env check + backend tests + frontend env check + typecheck
  - deterministic backend test execution (no hard dependency on external Redis)
  - `/health` now includes WS SLI evaluation result (`ok` / `insufficient_data` / `degraded`) and can fail health when WS SLI is below target with enough samples
  - `/health` and `/health/slo` now include WS multi-window burn-rate baseline (`5m/1h/6h/24h`) with fast/slow pair policy evaluation
  - WS SLI/burn-rate thresholds are now env-configurable (no code change required for calibration)
  - release gate now wires burn-rate deploy policy check (`backend/scripts/check_slo_burn_rate_gate.py`):
    - PR: optional (skips when URL not configured)
    - `main`: required (blocks on degraded WS SLI/burn-rate)
  - scheduled burn-rate monitor workflow (`.github/workflows/slo-burn-rate-monitor.yml`) runs every 30 minutes and auto-opens/updates alert issue on failure
  - canary guard + rollback baseline (`backend/scripts/run_canary_guard.py`, `.github/workflows/canary-guard.yml`) with staged observation policy (`duration` / `interval` / `max_failures`) and optional rollout/rollback hook integration (`CANARY_GUARD_ROLLOUT_HOOK_URL` / `CANARY_GUARD_ROLLBACK_HOOK_URL`)
- Exit criteria:
  - Workflow passes on PR
  - same commands reproducible locally

### P0-B: Security Gate v1 (OWASP/BOLA)
- Status: In progress (API1/API2/API3/API4/API8/API9 baseline shipped)
- Scope:
  - endpoint authorization matrix expanded to critical write paths (`journals`, `cards`, `card-decks`, `users`)
  - endpoint authorization matrix contract gate for all mutating HTTP routes (`backend/scripts/check_endpoint_authorization_matrix.py`, `docs/security/endpoint-authorization-matrix.json`)
  - matrix `test_ref` marker contract (`# AUTHZ_MATRIX: METHOD /path`) to ensure claimed endpoint-test linkage stays machine-verifiable
  - critical-read authorization matrix contract gate (`backend/scripts/check_read_authorization_matrix.py`, `docs/security/read-authorization-matrix.json`)
  - read matrix `test_ref` marker contract (`# READ_AUTHZ_MATRIX: GET /path`) to keep read-path ownership and test linkage machine-verifiable
  - users pairing mutation matrix baseline (`POST /api/users/pair`, `POST /api/users/invite-code`) verifies pair-scope isolation and non-target integrity on rejection (`backend/tests/test_user_pairing_authorization_matrix.py`)
  - read-path BOLA matrix for `cards/{card_id}/conversation`, `cards/backlog`, `card-decks/history*`, `card-decks/stats`, `users/{user_id}`, `users/notifications*`, `users/me/data-export`, and `billing/reconciliation` isolation
  - API4 resource guard baseline for `GET /api/cards/`, `GET /api/cards/backlog`, `GET /api/cards/{card_id}/conversation`, and `GET /api/card-decks/history*` (`limit` bounded to `1..100`, deck history date-range bounded to `<=366` days) with gate tests (`backend/tests/test_card_resource_consumption_guard.py`, `backend/tests/test_card_deck_resource_consumption_guard.py`)
  - deck history observability baseline: structured telemetry log (`duration_ms`, `result_count`/`total_records`, filter window, pagination) on `GET /api/card-decks/history*` with contract tests (`backend/tests/test_card_deck_resource_consumption_guard.py`)
  - notifications observability baseline: structured telemetry log for `GET /api/users/notifications`, `GET /api/users/notifications/stats`, and `POST /api/users/notifications/mark-read` (`duration_ms` + filter/result metadata) with contract tests (`backend/tests/test_notification_authorization_matrix.py`)
  - abuse budget policy baseline: documented defaults + CI assertions for rate-limit/ws envelopes (`docs/security/abuse-budget-policy.md`, `backend/tests/test_abuse_budget_policy.py`)
  - write-path rate-limit hardening (`SEC-01`): `journals/cards/card-decks` new-response flows enforce user + IP + device + partner-pair dimensions with gate tests
  - rate-limit observability contract: structured `rate_limit_block` logs + `X-RateLimit-Scope/X-RateLimit-Action` headers + runtime counters in `/health` and `/health/slo`
  - `card-decks/draw` matrix guard added (unpaired reject + pair isolation)
  - notifications owner-only matrix guard (`list/stats/mark-read/read/retry`), including single-read owner success path isolation and retry state-policy rejection (`FAILED|THROTTLED` only)
  - API2 token misuse regression suite baseline (`backend/tests/test_auth_token_misuse_regression.py`) including notification write endpoint and data-rights endpoint checks (`GET /api/users/me/data-export`, `DELETE /api/users/me/data`)
  - auth misuse write-path coverage for `journals/cards/card-decks/users` (`backend/tests/test_auth_token_misuse_write_paths.py`)
  - audit log baseline for critical mutating endpoints (`users/journals/cards/card-decks`) with immutable event schema (`backend/app/models/audit_event.py`) and gate tests (`backend/tests/test_audit_log_baseline.py`)
  - denied/error forensics baseline for authorization and unexpected failures (`USER_READ_DENIED`, `JOURNAL_DELETE_DENIED`, `CARD_DECK_RESPOND_DENIED`, `JOURNAL_CREATE_ERROR`, `NOTIFICATION_READ_DENIED`, `NOTIFICATION_RETRY_DENIED`, `BILLING_STATE_CHANGE_DENIED`, `BILLING_WEBHOOK_DENIED`) via gate tests (`backend/tests/test_audit_log_security_controls.py`, `backend/tests/test_audit_log_billing_notification_controls.py`)
  - audit log retention baseline (`AUDIT_LOG_RETENTION_DAYS`, purge service + audit runner, retention policy doc) with CI assertions (`backend/tests/test_audit_log_security_controls.py`, `backend/tests/test_security_evidence_validation.py`)
  - local retention audit command: `./scripts/audit-log-retention.sh`
  - daily retention workflow: `.github/workflows/audit-log-retention.yml`
  - retention evidence freshness gate in security release gate (`--kind audit-log-retention --max-age-days ${AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS:-14}`)
  - API5 function-level authorization policy gate for privileged routes (`backend/scripts/check_function_level_authorization.py`, `backend/tests/test_function_level_authorization_policy.py`)
  - API8 misconfiguration baseline: security response header middleware + contract test (`backend/tests/test_security_headers.py`)
  - API9 inventory baseline: generated API snapshot + gate check with metadata contract (`owner_team`, `runbook_ref`, `data_sensitivity`) (`backend/scripts/export_api_inventory.py`, `docs/security/api-inventory.json`, `backend/tests/test_api_inventory_contract.py`)
  - API9 ownership attestation baseline: freshness + pre-expiry reminder threshold + inventory coverage + CODEOWNERS ref sync (`backend/scripts/check_api_inventory_owner_attestation.py`, `docs/security/api-inventory-owner-attestation.json`, `docs/security/api-inventory-owner-attestation.md`, `.github/CODEOWNERS`, `.github/workflows/api-inventory-attestation.yml`)
  - billing authorization matrix (`backend/tests/test_billing_authorization_matrix.py`) for per-user idempotency isolation and reconciliation scope isolation
  - websocket handshake token misuse integration tests (`backend/tests/test_websocket_auth_guard.py`)
  - API3 overposting rejection baseline on critical writes (`users`, `journals`, `billing`)
  - CI-required security test target
- Exit criteria:
  - authorization matrix tests fail on unauthorized data access paths
  - read endpoints do not leak cross-pair conversation/history data
  - auth token misuse tests fail on expired/forged/malformed credentials
  - billing idempotency and reconciliation remain isolated per user in matrix tests
  - overposted sensitive fields are rejected (422) on guarded write endpoints
  - release blocked when security test target fails

### P0-C: Data Rights Foundation
- Status: In progress (baseline shipped + first local drill recorded)
- Scope:
  - export payload baseline: `GET /api/users/me/data-export`
  - export package expiry baseline: `expires_at` (`DATA_EXPORT_EXPIRY_DAYS`, default `7`)
  - erase flow baseline: `DELETE /api/users/me/data`
  - data-rights machine contract gate (`backend/scripts/check_data_rights_contract.py`)
  - data-retention lifecycle contract gate (`backend/scripts/check_data_retention_contract.py`)
  - data-classification policy contract gate (`backend/scripts/check_data_classification_contract.py`)
  - data-deletion lifecycle contract gate (`backend/scripts/check_data_deletion_lifecycle_contract.py`)
  - export package spec artifact (`docs/security/data-rights-export-package-spec.json`)
  - deletion graph spec artifact (`docs/security/data-rights-deletion-graph.json`)
  - retention policy artifact (`docs/security/data-retention-policy.json`)
  - classification policy artifact (`docs/security/data-classification-policy.json`)
  - deletion lifecycle policy artifact (`docs/security/data-deletion-lifecycle-policy.json`)
  - phase-gated soft-delete runtime scaffolding (`DATA_SOFT_DELETE_ENABLED`) with `deleted_at` schema hooks + migration baseline
  - soft-delete purge audit runbook (`docs/security/data-soft-delete-purge-audit.md`)
  - soft-delete purge audit workflow (`.github/workflows/data-soft-delete-purge.yml`)
  - soft-delete purge evidence contract gate (`backend/scripts/validate_security_evidence.py --kind data-soft-delete-purge --contract-mode strict`)
  - monthly fire-drill runbook: `docs/security/data-rights-fire-drill.md`
  - monthly CI drill workflow: `.github/workflows/p0-drill.yml`
  - drill check contract includes `data_rights_audit_trail` (`USER_DATA_EXPORT`/`USER_DATA_ERASE`)
  - evidence schema validation gate: `backend/scripts/validate_security_evidence.py --kind p0-drill --contract-mode strict` (`schema_version=1.1.0`)
  - data-rights subset evidence schema validation gate: `backend/scripts/validate_security_evidence.py --kind data-rights-fire-drill --contract-mode strict`
  - data-rights subset freshness gate in security release gate (`--kind data-rights-fire-drill --max-age-days ${DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`)
  - evidence freshness gate in security release gate (`--max-age-days ${P0_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`)
  - compatibility validator mode for historical artifacts: `--contract-mode compat`
- Exit criteria:
  - one full access/export/erase dry run documented and attached to release evidence
  - drill evidence JSON fails CI when required checks/schema drift

### P0-D: Billing Correctness Foundation
- Status: In progress (state machine + ledger + reconciliation + customer binding baseline shipped)
- Scope:
  - idempotency key enforced: `POST /api/billing/state-change`
  - webhook signature verify + replay-safe handler: `POST /api/billing/webhooks/stripe`
  - state machine + entitlement snapshot baseline (`trial/active/past_due/grace_period/canceled`)
  - customer/subscription binding for webhook identity mapping (metadata fallback only)
  - webhook identifier conflict guard (`customer` and `subscription` must map to same user)
  - webhook transition policy guard (invalid lifecycle jumps are rejected with 409)
  - reconciliation API baseline: `GET /api/billing/reconciliation`
  - ledger entries recorded for command/webhook paths
  - daily reconciliation audit workflow: `.github/workflows/billing-reconciliation.yml`
  - local reconciliation audit entrypoint: `./scripts/billing-reconciliation.sh`
  - reconciliation evidence schema validation gate: `backend/scripts/validate_security_evidence.py --kind billing-reconciliation --contract-mode strict` (`schema_version=1.1.0`)
  - reconciliation evidence freshness gate in security release gate (`--kind billing-reconciliation --max-age-days ${BILLING_RECON_EVIDENCE_MAX_AGE_DAYS:-14}`)
  - billing subset evidence schema validation gate: `backend/scripts/validate_security_evidence.py --kind billing-fire-drill --contract-mode strict`
  - billing subset freshness gate in security release gate (`--kind billing-fire-drill --max-age-days ${BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`)
  - compatibility validator mode for historical artifacts: `--contract-mode compat`
  - workflow failure auto-opens/updates a GitHub alert issue
  - regression tests for idempotency/signature/replay/state-transition/reconciliation added to gate
- Exit criteria:
  - contract tests for idempotency + webhook verification + reconciliation in CI
  - first sandbox webhook replay drill recorded
  - no missing command-ledger links in drill evidence
  - daily reconciliation workflow emits evidence artifacts and stays green
  - reconciliation failure path triggers CI alert issue automatically

### Latest Local Drill Evidence
- Timestamp (UTC): 2026-02-16T14:24:04Z
- Evidence JSON: `docs/security/evidence/p0-drill-20260216T142404Z.json`
- Evidence Markdown: `docs/security/evidence/p0-drill-20260216T142404Z.md`

### Latest Local Reconciliation Audit Evidence
- Timestamp (UTC): 2026-02-16T14:24:04Z
- Evidence JSON: `docs/security/evidence/billing-reconciliation-20260216T142404Z.json`
- Evidence Markdown: `docs/security/evidence/billing-reconciliation-20260216T142404Z.md`

## 5) Immediate Sequencing (Execution Order)

1. Run first PR through Release Gate and fix CI deltas
2. Expand BOLA tests to remaining mutating endpoints (`journals`, `cards`, `card-decks`, `users`)
3. Keep authorization/property-level tests aligned for any newly added mutating endpoints
4. Execute first monthly P0-C fire-drill and archive evidence
5. Execute first P0-D webhook replay drill and archive evidence
