# Migration Rehearsal Report

Use `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_migration_rehearsal_report.py`
to produce machine-readable migration rehearsal evidence.

## Dry-run

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run_migration_rehearsal_report.py --dry-run --report-path /tmp/haven-migration-rehearsal.json
```

## Execute rehearsal

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
./scripts/run_migration_rehearsal_report.py \
  --database-url sqlite:////tmp/haven-alembic-rehearsal.db \
  --report-path /tmp/haven-migration-rehearsal.json
```

## Report contract

The JSON report contains:

- `artifact_kind`: `migration-rehearsal-report`
- `schema_version`: `v1`
- `status`: `pass | fail | dry_run`
- `steps[]`: command, exit code, duration, output tails

## Rollback

If this rehearsal wrapper causes gate friction, restore:

```bash
cd /Users/alanzeng/Desktop/Projects/Haven
git restore /Users/alanzeng/Desktop/Projects/Haven/backend/scripts/run_migration_rehearsal_report.py \
  /Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_migration_rehearsal_report_script.py \
  /Users/alanzeng/Desktop/Projects/Haven/docs/backend/MIGRATION_REHEARSAL.md
```

