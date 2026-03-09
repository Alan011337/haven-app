# Data Soft-Delete Purge Audit (DATA-DEL-01)

Last updated: 2026-02-23

## Goal

Provide a repeatable audit for soft-delete purge lifecycle:

1. Count rows eligible for purge (`deleted_at <= cutoff`).
2. Run in `dry_run` mode by default (no physical delete).
3. Optionally run `apply` mode for controlled cleanup windows.
4. Produce machine-validated evidence artifacts.

## Commands

1. Local one-command dry-run audit:
   - `./scripts/data-soft-delete-purge.sh`
2. Backend script (dry-run):
   - `cd backend && venv/bin/python scripts/run_data_soft_delete_purge_audit.py`
3. Backend script (apply):
   - `cd backend && venv/bin/python scripts/run_data_soft_delete_purge_audit.py --apply`
4. Validator:
   - `cd backend && venv/bin/python scripts/validate_security_evidence.py --kind data-soft-delete-purge --contract-mode strict`
5. Restore rehearsal:
   - `./scripts/data-restore-drill.sh`

## Safety

1. `--apply` is blocked when `DATA_SOFT_DELETE_ENABLED=false`.
2. Use `--allow-when-disabled` only for explicit maintenance cleanup.
3. Purge order is fixed to avoid FK conflicts:
   - analyses -> journals -> card_responses -> card_sessions -> notification_events -> users
4. `AuditEvent.actor_user_id/target_user_id` are nulled before user row purge.

## Evidence

Generated under `docs/security/evidence/`:

1. `data-soft-delete-purge-*.json`
2. `data-soft-delete-purge-*.md`

Contract fields include:

1. `mode` (`dry_run` / `apply`)
2. `retention_days`
3. `cutoff_iso`
4. `candidate_counts`
5. `purged_counts`
6. `total_candidates`
7. `total_purged`
8. `healthy`

## CI

1. Workflow: `.github/workflows/data-soft-delete-purge.yml`
2. Schedule: daily UTC
3. On failure: auto-open/update GitHub alert issue

## Restore Linkage

1. Restore rehearsal runbook: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/data-restore-rehearsal.md`
2. Restore rehearsal evidence kind: `data-restore-drill`
