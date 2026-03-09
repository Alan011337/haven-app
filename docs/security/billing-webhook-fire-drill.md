# Billing Webhook Fire Drill (P0-D)

Last updated: 2026-02-16

## Goal

Verify billing webhook correctness controls:

1. signature verification
2. replay-safe handling
3. idempotency behavior for billing state change
4. reconciliation consistency (command log vs ledger)
5. customer binding resolution for webhook identity mapping

## API Baseline

1. `POST /api/billing/state-change` (requires `Idempotency-Key`)
2. `POST /api/billing/webhooks/stripe` (requires `Stripe-Signature`)
3. `GET /api/billing/reconciliation`
4. Daily audit workflow: `.github/workflows/billing-reconciliation.yml`
5. Security release gate freshness check:
   - `python backend/scripts/validate_security_evidence.py --kind billing-reconciliation --contract-mode strict --max-age-days ${BILLING_RECON_EVIDENCE_MAX_AGE_DAYS:-14}`
6. Security release gate billing-drill subset freshness check:
   - `python backend/scripts/validate_security_evidence.py --kind billing-fire-drill --contract-mode strict --max-age-days ${BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS:-35}`

## Automation

Run:

1. `./scripts/p0-drill.sh`
2. Inspect output for:
   - `billing_state_change_idempotency: PASS`
   - `billing_reconciliation_health: PASS`
   - `billing_webhook_binding_resolution: PASS`
   - `billing_webhook_identifier_conflict_guard: PASS`
   - `billing_webhook_replay_safety: PASS`
3. Validator contract gate:
   - `python backend/scripts/validate_security_evidence.py --kind billing-fire-drill --contract-mode strict`
4. Archive generated evidence files in `docs/security/evidence/`

## Pass Criteria

1. Same idempotency key + same payload returns replayed result.
2. Same idempotency key + different payload is rejected (`409`).
3. Valid webhook signature is accepted.
4. Same webhook event replay returns replayed response.
5. Same event id with different payload is rejected (`409`).
6. Reconciliation reports healthy state after valid billing command (`healthy=true`, no missing ledger entry).
7. Follow-up webhook without `metadata.user_id` still resolves user via customer binding.
8. Webhook payload that mixes `customer`/`subscription` identifiers from different users is rejected (`409`).

## Failure Handling

1. Open a P0 billing incident ticket.
2. Freeze billing-related feature releases.
3. Add or tighten regression tests before closing.
4. Verify CI alert issue has been opened/updated for incident tracking.

## Evidence Checklist

1. Drill command output
2. JSON evidence file
3. Markdown evidence file
4. Incident link (if failed)
