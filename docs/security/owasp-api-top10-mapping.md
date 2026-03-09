# OWASP API Top 10 Mapping (Working Draft)

Last updated: 2026-02-17

Target standard: OWASP API Security Top 10 (2023).

## Scope

Backend APIs in `backend/app/api` for users, journals, cards, card-decks, notifications, and websocket entrypoint.

## Current Mapping Snapshot

### API1: Broken Object Level Authorization (BOLA)
- Current controls:
  - self/partner access guard in users router
  - journal owner-only delete checks
  - notification ownership checks before read/retry
  - card deck non-participant rejection
  - mutating-route authorization matrix contract gate (`method/path` coverage + `owner_team` + `test_ref`)
  - critical-read authorization matrix contract gate (`GET` coverage + `owner_team` + `test_ref`)
- Evidence:
  - `backend/tests/security/test_bola_matrix.py`
  - `backend/tests/security/test_bola_subject_matrix.py`
  - `backend/tests/test_user_authorization_matrix.py`
  - `backend/tests/test_journal_authorization_matrix.py`
  - `backend/tests/test_card_authorization_matrix.py`
  - `backend/tests/test_card_deck_authorization_matrix.py`
  - `backend/tests/test_notification_api.py`
  - `backend/scripts/check_endpoint_authorization_matrix.py`
  - `docs/security/endpoint-authorization-matrix.json`
  - `backend/tests/test_endpoint_authorization_matrix_policy.py`
  - `backend/scripts/check_read_authorization_matrix.py`
  - `docs/security/read-authorization-matrix.json`
  - `backend/tests/test_read_authorization_matrix_policy.py`
  - `backend/tests/test_card_mode_isolation.py::CardModeIsolationTests::test_deck_respond_rejects_non_participant`
- Gap:
  - keep write/read matrix metadata (`subject_scope`, `test_ref`) updated when endpoint behavior changes.

### API2: Broken Authentication
- Current controls:
  - JWT token verification and subject matching in websocket handshake
  - token-required API dependency for authenticated routes
  - inactive-account enforcement on both login issue path and token-auth dependency
  - token misuse regression suite for expired/forged/malformed/missing-sub/nonexistent-user cases
- Evidence:
  - `backend/app/api/login.py`
  - `backend/app/api/deps.py`
  - `backend/tests/test_auth_token_endpoint_security.py`
  - `backend/tests/test_auth_token_misuse_regression.py`
  - `backend/tests/test_websocket_auth_guard.py`
- Gap:
  - maintain token-misuse regression coverage as new auth entrypoints are added.

### API3: Broken Object Property Level Authorization
- Current controls:
  - request schemas reject unknown/overposted fields on critical write paths:
    - `UserCreate` (`POST /api/users/`)
    - `PairingRequest` (`POST /api/users/pair`)
    - `JournalCreate` (`POST /api/journals/`)
    - `BillingStateChangeRequest` (`POST /api/billing/state-change`)
  - response schemas constrain exposed fields
  - data classification policy contract (mapping `data_sensitivity -> handling rules`) is machine-validated in security gate
- Evidence:
  - `backend/tests/test_user_field_level_authorization.py`
  - `backend/tests/test_journal_authorization_matrix.py`
  - `backend/tests/test_billing_idempotency_api.py`
  - `docs/security/data-classification-policy.json`
  - `backend/scripts/check_data_classification_contract.py`
  - `backend/tests/test_data_classification_contract_policy.py`
- Gap:
  - keep property-level authorization coverage aligned when new write schemas/endpoints are introduced.

### API4: Unrestricted Resource Consumption
- Current controls:
  - journal/card write-path limits now include user + IP + device + partner-pair scopes
  - pairing and websocket abuse limits
  - websocket payload cap + backoff
  - abuse budget policy + CI assertions for write-path and websocket envelopes
  - structured `429` observability contract (`X-RateLimit-Scope`, `X-RateLimit-Action`) and runtime counters in `/health` + `/health/slo`
- Evidence:
  - `backend/app/services/rate_limit.py`
  - `backend/app/services/rate_limit_runtime_metrics.py`
  - `backend/app/services/request_identity.py`
  - `backend/tests/test_rate_limit_runtime_metrics.py`
  - `backend/tests/test_health_endpoint.py`
  - `backend/tests/test_journal_notification_rules.py`
  - `backend/tests/test_card_mode_isolation.py`
  - `backend/tests/test_abuse_budget_policy.py`
  - `docs/security/abuse-budget-policy.md`
  - `backend/scripts/security-gate.sh`
- Gap:
  - add endpoint-specific burst/steady-state budgets derived from production SLO telemetry.

### API5: Broken Function Level Authorization
- Current controls:
  - user-specific notification operations bound to current_user ownership
  - function-level policy gate for privileged routes (`/api/admin*`, `/api/ops*`, `/api/internal*` or `admin|ops|internal` tags) requires explicit admin-guard dependency names
- Evidence:
  - `backend/scripts/check_function_level_authorization.py`
  - `backend/tests/test_function_level_authorization_policy.py`
  - `backend/scripts/security-gate.sh`
- Gap:
  - when admin/operator endpoints are introduced, add endpoint-level allowlist matrix tests and explicit role model.

### API6: Unrestricted Access to Sensitive Business Flows
- Current controls:
  - pairing abuse guard, invite code constraints, retry guards
  - billing state-change endpoint enforces idempotency key and payload consistency
  - billing state machine transition guard (`trial/active/past_due/grace_period/canceled`)
  - billing entitlement snapshot and ledger write on state changes
  - stripe webhook endpoint enforces signature verification + replay-safe event receipt
  - webhook user mapping supports provider customer/subscription binding (metadata fallback only)
  - webhook rejects mixed identifiers that map to different users (`customer` vs `subscription`)
  - billing reconciliation endpoint verifies command logs and ledger consistency
  - daily reconciliation audit workflow with evidence artifacts
  - reconciliation CI failure path auto-opens/updates GitHub alert issue
  - data-rights export/erase contract gate (`backend/scripts/check_data_rights_contract.py`) for export package structure, expiry policy, and deletion graph consistency
  - deletion lifecycle phase-gate contract (`backend/scripts/check_data_deletion_lifecycle_contract.py`) to keep hard-delete baseline and future trash/purge transition explicit
  - phase-gated soft-delete runtime scaffolding for erase flow (`DATA_SOFT_DELETE_ENABLED`, `deleted_at` schema hooks, and `status=soft_deleted`)
  - scheduled soft-delete purge dry-run audit + evidence contract validation
- Evidence:
  - `backend/tests/test_billing_idempotency_api.py`
  - `backend/tests/test_billing_webhook_security.py`
  - `backend/scripts/run_p0_drills.py` (`billing_reconciliation_health`)
  - `backend/scripts/run_billing_reconciliation_audit.py`
  - `.github/workflows/billing-reconciliation.yml`
  - `backend/scripts/check_data_rights_contract.py`
  - `docs/security/data-rights-export-package-spec.json`
  - `docs/security/data-rights-deletion-graph.json`
  - `docs/security/data-deletion-lifecycle-policy.json`
  - `backend/scripts/check_data_deletion_lifecycle_contract.py`
  - `backend/tests/test_data_deletion_lifecycle_contract_policy.py`
  - `backend/app/services/data_deletion_lifecycle.py`
  - `backend/app/services/data_soft_delete_purge.py`
  - `backend/alembic/versions/ab8c9d0e1f3a_add_deleted_at_columns_for_soft_delete.py`
  - `backend/tests/test_data_rights_api.py::DataRightsApiTests::test_data_erase_soft_delete_marks_rows_when_feature_enabled`
  - `backend/tests/test_data_soft_delete_purge_service.py`
  - `backend/scripts/run_data_soft_delete_purge_audit.py`
  - `.github/workflows/data-soft-delete-purge.yml`
  - `docs/security/data-soft-delete-purge-audit.md`
  - `docs/security/evidence/data-soft-delete-purge-*.json`
  - `backend/tests/test_data_rights_contract_policy.py`
- Gap:
  - provider coverage is currently Stripe-focused; additional provider adapters still pending.

### API7: SSRF
- Current controls:
  - no open user-controlled fetch proxy endpoints in current backend
- Gap:
  - keep deny-by-default rule when adding external fetch features.

### API8: Security Misconfiguration
- Current controls:
  - startup env validation script, CORS config centralization
  - baseline response security headers middleware on API/health routes (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`)
  - regression test for security header contract
- Evidence:
  - `backend/app/main.py`
  - `backend/tests/test_security_headers.py`
  - `backend/scripts/security-gate.sh`
- Gap:
  - add deployment-level CSP/HSTS enforcement verification in production edge config.

### API9: Improper Inventory Management
- Current controls:
  - deterministic API inventory snapshot generated from FastAPI routes (HTTP + WebSocket)
  - snapshot check is part of security gate CI to prevent unmanaged endpoint drift
  - inventory schema includes endpoint metadata (`owner_team`, `runbook_ref`, `data_sensitivity`)
  - owner-team attestation contract (freshness + inventory owner coverage + CODEOWNERS ref sync)
  - monthly attestation workflow with failure alert issue
- Evidence:
  - `backend/scripts/export_api_inventory.py`
  - `docs/security/api-inventory.json`
  - `backend/tests/test_api_inventory_contract.py`
  - `backend/scripts/check_api_inventory_owner_attestation.py`
  - `docs/security/api-inventory-owner-attestation.json`
  - `docs/security/api-inventory-owner-attestation.md`
  - `backend/tests/test_api_inventory_owner_attestation_policy.py`
  - `.github/CODEOWNERS`
  - `.github/workflows/api-inventory-attestation.yml`
  - `backend/scripts/security-gate.sh`
- Gap:
  - add chatops/slack notification channel for attestation failures in addition to GitHub issues.

### API10: Unsafe Consumption of APIs
- Current controls:
  - provider fallback for notification dedupe when Redis is unavailable
- Gap:
  - explicit external-provider timeout/retry/circuit-breaker policy pending.

## Cross-Cutting Forensics Baseline

- Current controls:
  - immutable audit event schema for critical mutating endpoints (`users/journals/cards/card-decks`)
  - audit gate tests validating event write on core write paths
  - denied/error audit events for key authorization and error paths (`users`, `notifications`, `billing`)
  - data-rights audit events on export/erase flows (`USER_DATA_EXPORT`, `USER_DATA_ERASE`, `USER_DATA_ERASE_ERROR`)
  - retention baseline with configurable purge policy (`AUDIT_LOG_RETENTION_DAYS`)
  - lifecycle retention policy contract for erase-scoped data + audit/export TTL (`backend/scripts/check_data_retention_contract.py`)
- Evidence:
  - `backend/app/models/audit_event.py`
  - `backend/app/services/audit_log.py`
  - `backend/app/services/audit_log_retention.py`
  - `backend/scripts/run_audit_log_retention.py`
  - `backend/scripts/run_audit_log_retention_audit.py`
  - `backend/tests/test_audit_log_baseline.py`
  - `backend/tests/test_audit_log_security_controls.py`
  - `backend/tests/test_audit_log_billing_notification_controls.py`
  - `backend/tests/test_security_evidence_validation.py`
  - `.github/workflows/audit-log-retention.yml`
  - `docs/security/audit-log-retention-policy.md`
  - `docs/security/data-retention-policy.json`
  - `backend/tests/test_data_retention_contract_policy.py`
- Gap:
  - add scheduled archival workflow and long-term immutable storage target.

## AI Safety & Prompt Supply Chain

- Current controls:
  - Prompt version tracking (`CURRENT_PROMPT_VERSION`) and integrity hash (`PROMPT_POLICY_HASH`)
  - Prompt injection detection via regex baseline (`backend/app/services/prompt_abuse.py`)
  - OpenAI Moderation API pre-check before analysis
  - Safety circuit breaker for tier 2/3 responses
  - Non-impersonation, coaching boundaries, crisis consistency policies in system prompt
  - Canary rollout policy for prompt changes
- Evidence:
  - `backend/tests/test_prompt_abuse_policy.py`
  - `backend/tests/test_ai_safety_redteam.py`
  - `backend/tests/test_safety_regression.py`
  - `backend/tests/test_prompt_supply_chain.py`
  - `backend/tests/test_ai_safety_logic.py`
  - `backend/tests/test_ai_schema_contract.py`
  - `docs/security/prompt-rollout-policy.json`
  - `docs/security/prompt-abuse-policy.json`
  - `POLICY_AI.md`
- Gap:
  - add semantic-similarity prompt injection detection beyond regex patterns.

## Age Gating & Consent

- Current controls:
  - Age confirmation required at registration (18+ policy)
  - Terms of Service and Privacy Policy acceptance required
  - Consent receipt audit trail
  - Store compliance matrix for App Store / Google Play
- Evidence:
  - `docs/security/consent-receipt-policy.json`
  - `docs/security/store-compliance-matrix.json`
  - `backend/tests/test_user_consent_receipt_api.py`
  - `backend/tests/test_store_compliance_contract_policy.py`
  - `docs/legal/PRIVACY_POLICY.md`
  - `docs/legal/TERMS_OF_SERVICE.md`
- Gap:
  - implement server-side age verification beyond self-declaration for jurisdictions that require it.

## CI Gate

Security gate command:

```bash
cd backend
./scripts/security-gate.sh
```

OWASP mapping contract gate:
- `backend/scripts/check_owasp_api_top10_mapping_contract.py`

This command is wired into release gate CI and should stay green before merging feature work.

Safety regression tests are now included in the security gate:
- `test_safety_regression.py` — prompt policy constants + thresholds
- `test_ai_safety_redteam.py` — adversarial input patterns
- `test_prompt_supply_chain.py` — prompt hash integrity
