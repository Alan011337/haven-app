# Billing Console Drift Monitor

## Why
- Detect drift between expected Stripe webhook console settings and runtime configuration before it impacts entitlements.
- Keep billing correctness controls observable and auditable with recurring evidence.

## How
- Run `backend/scripts/run_billing_console_drift_audit.py` to evaluate policy vs runtime.
- Validate generated evidence with `backend/scripts/validate_security_evidence.py --kind billing-console-drift`.
- Enforce freshness in `backend/scripts/security-gate.sh`.

## What
- Policy source: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/billing-console-drift-policy.json`
- Evidence artifacts:
  - `docs/security/evidence/billing-console-drift-*.json`
  - `docs/security/evidence/billing-console-drift-*.md`
- Required checks:
  - `runbook_present`
  - `policy_contract_passed`
  - `store_compliance_contract_passed`
  - `webhook_secret_configured`
  - `webhook_tolerance_within_policy`
  - `async_mode_within_policy`
  - `nonprod_dry_run`

## DoD
- Daily workflow generates billing console drift evidence.
- Security gate fails when evidence is stale beyond policy window.
- Drift conditions create actionable issue alerts from CI workflow.

## Debug Checklist
1. Evidence check fails with missing file:
   - Run `python scripts/run_billing_console_drift_audit.py` under `backend/`.
2. `webhook_secret_configured` fails:
   - Ensure `BILLING_STRIPE_WEBHOOK_SECRET` is set in secure runtime config.
3. `webhook_tolerance_within_policy` fails:
   - Compare runtime `BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS` with policy max.
4. `store_compliance_contract_passed` fails:
   - Fix `docs/security/store-compliance-matrix.json` contract violations first.

## Rollback
1. Disable freshness enforcement temporarily by raising `BILLING_CONSOLE_DRIFT_EVIDENCE_MAX_AGE_DAYS` in CI/runtime gate env.
2. Revert changes:
   - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_billing_console_drift_audit.py`
   - `/Users/alanzeng/Desktop/Projects/Haven/docs/security/billing-console-drift-policy.json`
   - `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/billing-console-drift.yml`
3. Re-run security gate:
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && bash scripts/security-gate.sh`
