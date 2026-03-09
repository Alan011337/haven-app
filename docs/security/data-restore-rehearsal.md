# Data Restore Rehearsal (DATA-ERASE-01 / DATA-DEL-01)

Last updated: 2026-02-23

## Goal

Create reproducible evidence that erase + soft-delete purge can be recovered through documented restore procedures.

1. Validate deletion lifecycle policy contract before any destructive path.
2. Validate soft-delete purge evidence freshness.
3. Produce a restore drill artifact (`data-restore-drill-*.json`) with strict schema.

## Dry-Run Steps

1. Run the one-command local rehearsal:
   - `./scripts/data-restore-drill.sh`
2. Validate generated restore drill evidence explicitly:
   - `cd backend && .venv-gate/bin/python scripts/validate_security_evidence.py --kind data-restore-drill --contract-mode strict`
3. Confirm source purge evidence used by the drill is fresh:
   - Check `source_evidence_path` and `source_evidence_generated_at` in the generated JSON.

## Pass Criteria

1. `all_passed=true` in `data-restore-drill-*.json`.
2. Required checks all pass:
   - `runbook_present`
   - `rollback_plan_present`
   - `lifecycle_contract_passed`
   - `source_purge_evidence_fresh`
   - `nonprod_dry_run`
3. Security gate accepts latest restore drill evidence freshness (`DATA_RESTORE_DRILL_EVIDENCE_MAX_AGE_DAYS`, default `35`).

## CI Automation

1. Workflow: `/Users/alanzeng/Desktop/Projects/Haven/.github/workflows/data-restore-drill.yml`
2. Schedule: weekly UTC (`20 5 * * 1`) plus manual `workflow_dispatch`.
3. On failure: open/update GitHub alert issue and upload drill artifacts.

## Rollback Plan

1. If rehearsal fails, do not run destructive purge in production.
2. Keep `DATA_SOFT_DELETE_ENABLED=false` until contract + evidence checks are green.
3. Re-run soft-delete purge in dry-run mode:
   - `cd backend && .venv-gate/bin/python scripts/run_data_soft_delete_purge_audit.py`
4. Regenerate restore drill evidence:
   - `cd backend && .venv-gate/bin/python scripts/run_data_restore_drill_audit.py`
5. If production cleanup has already started, restore from latest encrypted backup snapshot per incident SOP (`/Users/alanzeng/Desktop/Projects/Haven/docs/ops/incident-response-playbook.md`) and re-run integrity checks before reopening traffic.

## Evidence Artifacts

Generated under `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/`:

1. `data-restore-drill-*.json`
2. `data-restore-drill-*.md`

Key fields:

1. `source_evidence_kind`
2. `source_evidence_path`
3. `source_evidence_generated_at`
4. `source_evidence_max_age_days`
5. `checks_total / checks_passed / checks_failed`
6. `all_passed`
