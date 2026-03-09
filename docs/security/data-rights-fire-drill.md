# Data Rights Fire Drill (P0-C)

Last updated: 2026-02-17

## Goal

Run a repeatable monthly drill for:

1. Right to Access (export)
2. Right to Erasure (erase)

## API Baseline

1. `GET /api/users/me/data-export`
2. `DELETE /api/users/me/data`
3. Contract specs:
   - `docs/security/data-rights-export-package-spec.json`
   - `docs/security/data-rights-deletion-graph.json`
   - `docs/security/data-deletion-lifecycle-policy.json`

## Automation

Run the unified P0 drill script (includes data-rights checks and evidence output):

1. `./scripts/p0-drill.sh`
2. Evidence files will be generated under `docs/security/evidence/`
3. CI workflow `.github/workflows/p0-drill.yml` runs monthly on UTC cron `0 2 1 * *` (and supports manual `workflow_dispatch`)
4. Security gate also enforces latest drill evidence freshness (`P0_DRILL_EVIDENCE_MAX_AGE_DAYS`, default `35`)
5. Security gate enforces latest data-rights subset drill freshness (`DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS`, default `35`) via `backend/scripts/validate_security_evidence.py --kind data-rights-fire-drill --contract-mode strict`
6. Security gate enforces export/deletion contract consistency via `backend/scripts/check_data_rights_contract.py`

## Drill Procedure

1. Create a dedicated drill account pair in staging.
2. Generate at least one journal, one card response, one card session, and one notification.
3. Call `GET /api/users/me/data-export` and archive the JSON output in the security evidence folder.
4. Verify export package includes only current-user scoped records.
5. Verify export package includes `expires_at` and `expires_at > exported_at` within configured policy window (`DATA_EXPORT_EXPIRY_DAYS`, default `7`).
6. Call `DELETE /api/users/me/data`.
7. Verify the caller account is removed and partner is unpaired.
8. Verify scoped records are removed: journals/analyses/card_responses/card_sessions/notification_events.
9. Verify `deleted_counts` includes all contract keys (`analyses`, `journals`, `card_responses`, `card_sessions`, `notification_events`, `users`).
10. Verify unrelated third-party records are unchanged.

## Pass Criteria

1. Export endpoint returns `200` with non-empty `exported_at`, `expires_at`, and `export_version`.
2. Erase endpoint returns `200` with `status=erased` (hard-delete phase) or `status=soft_deleted` (phase-gated soft-delete enabled).
3. No unauthorized data leak in export package.
4. No residual current-user data after erase.
5. Unrelated users and records remain intact.
6. Audit trail contains both `USER_DATA_EXPORT` and `USER_DATA_ERASE` events.

## Failure Handling

1. Mark drill as failed and open a P0 incident ticket.
2. Freeze non-critical releases until fixed.
3. Add regression test coverage before closing the ticket.
4. CI workflow auto-opens/updates a GitHub alert issue when the drill job fails.

## Evidence Checklist

1. Export response sample
2. Erase response sample
3. Before/after record counts
4. Incident link (if failed)
5. Drill evidence artifact path in `docs/security/evidence/`
