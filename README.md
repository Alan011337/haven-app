# Haven v2: Connection AI

## Quick Start

- Backend (with automatic env validation before startup). API listens on **port 8000**; frontend expects `http://localhost:8000/api` (or set `NEXT_PUBLIC_API_URL`).
  - `./backend/scripts/run-dev.sh`
  - startup also runs worktree materialization check (prevents iCloud/dataless critical files from silently breaking boot)
  - emergency bypass: `SKIP_WORKTREE_MATERIALIZATION_CHECK=1 ./backend/scripts/run-dev.sh`
- Frontend (with automatic env validation via `predev`). If you see `ECONNABORTED` or "request_failed" in the console, start the backend first.
  - `cd frontend && npm run dev`
  - frontend env check now runs the same materialization guard (same bypass env var)

## Deploy Backend To Fly.io

Fly.io is the active production deployment source-of-truth for Haven backend.

- config: `/Users/alanzeng/Desktop/Projects/Haven/backend/fly.toml`
- Dockerfile: `/Users/alanzeng/Desktop/Projects/Haven/backend/Dockerfile.fly`
- one-command deploy script: `/Users/alanzeng/Desktop/Projects/Haven/scripts/deploy-fly-backend.sh`
- runbook: `/Users/alanzeng/Desktop/Projects/Haven/docs/ops/flyio-backend-deploy.md`

## Deploy Backend To Render (Archived)

`/Users/alanzeng/Desktop/Projects/Haven/render.yaml` is retained for migration history only.

- Do not use Render as active deployment target unless there is a new architecture decision.
- See `/Users/alanzeng/Desktop/Projects/Haven/docs/ops/deploy-source-of-truth.md` for policy details.

## Quick Checks

- Local bootstrap doctor (materialization + backend/frontend env):
  - `./scripts/dev-doctor.sh`
- Backend env validation:
  - `python3 backend/scripts/check_env.py`
- Frontend env validation:
  - `cd frontend && npm run check:env`
- Frontend typecheck (with timeout guard):
  - `cd frontend && TYPECHECK_TIMEOUT_MS=180000 npm run typecheck`
- Card dataset validation (no DB write):
  - `cd frontend && npm run seed:cards:validate`
- Card dataset QA export (report + cleaned JSON, no DB write):
  - `cd frontend && npm run seed:cards:qa`
- Card dataset dry run (with deck mapping, no DB write):
  - `cd frontend && npm run seed:cards:dry`
- Card dataset dry run + QA export:
  - `cd frontend && npm run seed:cards:dry:qa`
- Adopt cleaned dataset as official source (`cards.json`, with backup):
  - `cd frontend && npm run seed:cards:adopt-cleaned`
- Full pipeline (QA export -> adopt cleaned source):
  - `cd frontend && npm run seed:cards:pipeline`
- Card seed (actual upsert):
  - `cd frontend && npm run seed:cards`
- Backend health probe:
  - `GET /health`
  - includes `runtime.ws` counters for WebSocket guard telemetry (rejects/throttles/active connections)
  - includes DB/Redis/provider checks, uptime, and WS SLI snapshot
- Backend SLO probe:
  - `GET /health/slo`
  - exposes WS SLI + target values for uptime monitor / dashboard integration
- Frontend e2e smoke (P0-I):
  - `cd frontend && npm run test` (auto-sets `PLAYWRIGHT_AUTO_INSTALL=1` unless explicitly overridden)
  - `cd frontend && npm run test:e2e` (requires app running at `http://localhost:3000` or set `E2E_BASE_URL`)
  - first-time local setup shortcut: `cd frontend && npm run test:e2e:auto` (will auto-install Chromium)
  - run via local release gate: `RUN_E2E=1 E2E_BASE_URL=http://localhost:3000 bash scripts/release-gate-local.sh`  
    (`E2E_AUTO_INSTALL_BROWSER=0` to disable browser auto-install)
  - local gate runs an URL probe before e2e (defaults: `E2E_BASE_URL_PROBE_PATH=/`, `E2E_BASE_URL_PROBE_TIMEOUT_SECONDS=5`)
  - CI runs `frontend-e2e` in `.github/workflows/release-gate.yml` (PR 可容錯，main 必過)

## Rate Limit Tuning

Backend supports configurable write-rate limits to protect AI cost and API stability:

- `JOURNAL_RATE_LIMIT_COUNT` (default: `12`)
- `JOURNAL_RATE_LIMIT_WINDOW_SECONDS` (default: `60`)
- `CARD_RESPONSE_RATE_LIMIT_COUNT` (default: `30`)
- `CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS` (default: `60`)
- `PAIRING_ATTEMPT_RATE_LIMIT_COUNT` (default: `10`)
- `PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS` (default: `300`)
- `PAIRING_FAILURE_COOLDOWN_THRESHOLD` (default: `5`)
- `PAIRING_FAILURE_COOLDOWN_SECONDS` (default: `600`)
- `PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT` (default: `30`)
- `PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS` (default: `300`)
- `PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD` (default: `15`)
- `PAIRING_IP_FAILURE_COOLDOWN_SECONDS` (default: `900`)
- `WS_MAX_CONNECTIONS_PER_USER` (default: `1`)
- `WS_MAX_CONNECTIONS_GLOBAL` (default: `2000`)
- `WS_MESSAGE_RATE_LIMIT_COUNT` (default: `120`)
- `WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS` (default: `60`)
- `WS_MESSAGE_BACKOFF_SECONDS` (default: `30`)
- `WS_MAX_PAYLOAD_BYTES` (default: `4096`)
- `ABUSE_GUARD_STORE_BACKEND` (default: `memory`, options: `memory` / `redis`)
- `ABUSE_GUARD_REDIS_URL` (required when backend is `redis`)
- `ABUSE_GUARD_REDIS_KEY_PREFIX` (default: `haven:abuse`)

Applied scopes:

- `POST /api/journals/`:
  - limits new journal submissions per user in rolling window
- `POST /api/cards/respond`:
  - limits only **new** response creation in rolling window
  - editing existing response is still allowed
- `POST /api/card-decks/respond/{session_id}`:
  - limits only **new** response creation in rolling window
  - editing existing response is still allowed
- `POST /api/users/pair`:
  - limits pairing attempts by `user_id + client_ip` in rolling window
  - also enforces IP-level limit across different accounts
  - activates temporary cooldown after repeated invalid attempts
- `GET /ws/{user_id}`:
  - enforces per-user/global connection cap
  - enforces message rate limit with temporary backoff
  - rejects oversized payloads
- Write paths (`POST /api/journals/`, `POST /api/cards/respond`, `POST /api/card-decks/respond/{session_id}`):
  - enforce user + IP + device + partner-pair rate-limit scopes for new writes
  - device scope reads header `X-Device-Id` (configurable via `RATE_LIMIT_DEVICE_HEADER`)

When exceeded, backend returns `429 Too Many Requests` with localized detail message and `Retry-After` response header.

### Abuse Guard State Backend

- `memory` (default): in-process state, suitable for single-instance deployment.
- `redis`: shared state across multiple backend instances for consistent throttling/cooldown.
- Redis mode writes guard state with TTL (based on window/cooldown), so stale keys auto-expire without periodic full key scans.
- Notification dedupe also follows the same backend; in Redis mode it uses atomic `SET NX EX` to prevent cross-instance duplicate send.
- If Redis backend is selected but unavailable/misconfigured, backend logs a warning and falls back to memory mode.

### Notification Dedupe Rollout Checklist

1. Run latest DB migrations:
   - `cd backend && ./scripts/run-alembic.sh upgrade head`
   - If local sqlite is brand-new and migration chain reports missing legacy tables, bootstrap once:
     - `cd backend && DATABASE_URL=sqlite:///./test.db .venv-gate/bin/python scripts/bootstrap-sqlite-schema.py`
2. For multi-instance deployment, enable Redis backend:
   - `ABUSE_GUARD_STORE_BACKEND=redis`
   - `ABUSE_GUARD_REDIS_URL=redis://<host>:<port>/<db>`
   - optional: `ABUSE_GUARD_REDIS_KEY_PREFIX=haven:abuse`
3. Validate env before startup:
   - `python3 backend/scripts/check_env.py`

## Release Gate (P0)

- CI workflow: `.github/workflows/release-gate.yml`
- Local one-command gate: `./scripts/release-gate.sh`
  - Optional include frontend e2e smoke: `RUN_E2E=1 ./scripts/release-gate.sh`
- Backend dev dependencies for tests: `backend/requirements-dev.txt`
- Backend security gate: `cd backend && ./scripts/security-gate.sh`
- Burn-rate deploy gate checker: `cd backend && PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_slo_burn_rate_gate.py --allow-missing-url`
  - Required on `main` in CI via `.github/workflows/release-gate.yml`
  - Uses `SLO_GATE_HEALTH_SLO_URL` (and optional `SLO_GATE_BEARER_TOKEN`)
  - WS SLI / burn-rate thresholds are env-configurable:
    - `HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET`
    - `HEALTH_WS_MESSAGE_PASS_RATE_TARGET`
    - `HEALTH_WS_SLI_MIN_CONNECTION_ATTEMPTS`
    - `HEALTH_WS_SLI_MIN_MESSAGES`
    - `HEALTH_WS_BURN_RATE_FAST_THRESHOLD`
    - `HEALTH_WS_BURN_RATE_SLOW_THRESHOLD`
    - `HEALTH_WS_BURN_RATE_MIN_CONNECTION_ATTEMPTS`
    - `HEALTH_WS_BURN_RATE_MIN_MESSAGES`
  - Scheduled monitor workflow: `.github/workflows/slo-burn-rate-monitor.yml` (every 30 minutes + `workflow_dispatch`)
    - On failure, workflow auto-opens/updates a GitHub alert issue.
- Canary guard and rollback baseline (REL-GATE-02):
  - Local runner: `./scripts/canary-guard.sh --dry-run-hooks --allow-missing-health-url`
  - Script: `backend/scripts/run_canary_guard.py` (supports rollout/rollback webhook hooks)
  - CI workflow: `.github/workflows/canary-guard.yml` (`workflow_dispatch`, configurable duration/interval/max_failures)
  - Hook envs: `CANARY_GUARD_ROLLOUT_HOOK_URL`, `CANARY_GUARD_ROLLBACK_HOOK_URL`, optional `CANARY_GUARD_HOOK_BEARER_TOKEN`
    - On failure, workflow auto-opens/updates a GitHub alert issue.
- Machine tracker (P0): `docs/p0-machine-tracker.yaml`
- Machine tracker (Roadmap): `docs/roadmap-machine-tracker.yaml`
- Tracker updater: `./scripts/update-p0-tracker.sh`
- API3 overposting guard baseline:
  - `POST /api/users/`, `POST /api/users/pair`, `POST /api/journals/`, `POST /api/billing/state-change` reject unknown/sensitive fields (`422`)
- Data rights baseline export API: `GET /api/users/me/data-export`
  - Export package now includes `expires_at` with policy default `DATA_EXPORT_EXPIRY_DAYS=7`
- Data rights baseline erase API: `DELETE /api/users/me/data`
- Monthly fire-drill runbook: `docs/security/data-rights-fire-drill.md`
  - Export package spec: `docs/security/data-rights-export-package-spec.json`
  - Deletion graph spec: `docs/security/data-rights-deletion-graph.json`
  - Deletion lifecycle policy spec: `docs/security/data-deletion-lifecycle-policy.json`
  - Data-rights contract gate (security gate): `cd backend && venv/bin/python scripts/check_data_rights_contract.py`
  - Deletion lifecycle contract gate (security gate): `cd backend && venv/bin/python scripts/check_data_deletion_lifecycle_contract.py`
  - Soft-delete purge audit runbook: `docs/security/data-soft-delete-purge-audit.md`
  - Soft-delete purge local audit: `./scripts/data-soft-delete-purge.sh`
  - Soft-delete purge workflow: `.github/workflows/data-soft-delete-purge.yml` (daily + `workflow_dispatch`)
  - Optional env: `DATA_EXPORT_EXPIRY_DAYS` (default `7`)
  - Phase-gated soft-delete envs (default hard-delete baseline):
    - `DATA_SOFT_DELETE_ENABLED` (`false`)
    - `DATA_SOFT_DELETE_TRASH_RETENTION_DAYS` (`30`)
    - `DATA_SOFT_DELETE_PURGE_RETENTION_DAYS` (`90`)
  - Freshness gate (security gate): `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind data-soft-delete-purge --contract-mode strict --max-age-days ${DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS:-14}`
  - Optional env: `DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS` (default `14`)
  - Freshness gate (security gate): `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind p0-drill --contract-mode strict --max-age-days ${P0_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`
  - Optional env: `P0_DRILL_EVIDENCE_MAX_AGE_DAYS` (default `35`)
  - Data-rights subset freshness gate (security gate): `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind data-rights-fire-drill --contract-mode strict --max-age-days ${DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`
  - Optional env: `DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS` (default `35`)
  - Billing subset freshness gate (security gate): `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind billing-fire-drill --contract-mode strict --max-age-days ${BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`
  - Optional env: `BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS` (default `35`)
- Billing idempotency baseline: `POST /api/billing/state-change` (requires `Idempotency-Key`)
- Billing webhook baseline: `POST /api/billing/webhooks/stripe` (requires `Stripe-Signature`)
- Billing reconciliation baseline: `GET /api/billing/reconciliation`
- Local billing reconciliation audit: `./scripts/billing-reconciliation.sh`
- Billing daily reconciliation workflow: `.github/workflows/billing-reconciliation.yml` (daily + `workflow_dispatch`)
  - On failure, workflow auto-opens/updates a GitHub alert issue.
  - Freshness gate (security gate): `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind billing-reconciliation --contract-mode strict --max-age-days ${BILLING_RECON_EVIDENCE_MAX_AGE_DAYS:-14}`
  - Optional env: `BILLING_RECON_EVIDENCE_MAX_AGE_DAYS` (default `14`)
- Audit log retention local audit: `./scripts/audit-log-retention.sh`
- Audit log retention workflow: `.github/workflows/audit-log-retention.yml` (daily + `workflow_dispatch`)
  - On failure, workflow auto-opens/updates a GitHub alert issue.
  - Freshness gate (security gate): `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind audit-log-retention --contract-mode strict --max-age-days ${AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS:-14}`
  - Optional env: `AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS` (default `14`)
- Data retention lifecycle policy artifact: `docs/security/data-retention-policy.json`
- Data retention lifecycle contract gate (security gate): `cd backend && venv/bin/python scripts/check_data_retention_contract.py`
- Data classification policy artifact: `docs/security/data-classification-policy.json`
- Data classification contract gate (security gate): `cd backend && venv/bin/python scripts/check_data_classification_contract.py`
- Data deletion lifecycle policy artifact: `docs/security/data-deletion-lifecycle-policy.json`
- Data deletion lifecycle contract gate (security gate): `cd backend && venv/bin/python scripts/check_data_deletion_lifecycle_contract.py`
- API inventory snapshot check (in security gate): `cd backend && venv/bin/python scripts/export_api_inventory.py --check`
- Regenerate API inventory snapshot after route changes: `cd backend && venv/bin/python scripts/export_api_inventory.py --write`
  - Inventory schema now includes `owner_team`, `runbook_ref`, `data_sensitivity`
- Function-level auth policy check (in security gate): `cd backend && venv/bin/python scripts/check_function_level_authorization.py`
- Endpoint authorization matrix check (in security gate): `cd backend && venv/bin/python scripts/check_endpoint_authorization_matrix.py`
  - Matrix source: `docs/security/endpoint-authorization-matrix.json`
  - `test_ref` contract: each referenced test file must include `# AUTHZ_MATRIX: METHOD /path` markers for claimed endpoint coverage
- Read authorization matrix check (in security gate): `cd backend && venv/bin/python scripts/check_read_authorization_matrix.py`
  - Matrix source: `docs/security/read-authorization-matrix.json`
  - `test_ref` contract: each referenced test file must include `# READ_AUTHZ_MATRIX: GET /path` markers for claimed endpoint coverage
- API inventory owner attestation check (in security gate): `cd backend && venv/bin/python scripts/check_api_inventory_owner_attestation.py`
  - Attestation source: `docs/security/api-inventory-owner-attestation.json`
  - CODEOWNERS sync source: `.github/CODEOWNERS`
  - Pre-expiry reminder gate: `min_attestation_days_remaining` (default 14, override with `API_INVENTORY_ATTESTATION_MIN_DAYS_REMAINING`)
  - Runbook: `docs/security/api-inventory-owner-attestation.md`
- Monthly owner attestation workflow: `.github/workflows/api-inventory-attestation.yml` (monthly + `workflow_dispatch`)
- Unified local drill command (P0-C/P0-D): `./scripts/p0-drill.sh`
- Drill evidence output folder: `docs/security/evidence/`
- CI drill workflow: `.github/workflows/p0-drill.yml` (monthly schedule + `workflow_dispatch`)
  - On failure, workflow auto-opens/updates a GitHub alert issue.
