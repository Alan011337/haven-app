# Backup Restore Drill

- Schema version: 1.1.0
- Generated at (UTC): 2026-02-23T03:05:25.613520+00:00
- Dry run: YES
- Source evidence kind: data-restore-drill
- Source evidence path: docs/security/evidence/data-restore-drill-20260223T030524Z.json
- Source evidence max age days: 120
- Backup encryption required: True
- Backup retention days: 35
- Checks passed: 7/7
- Overall: PASS

| Check | Result | Detail |
| --- | --- | --- |
| `runbook_present` | PASS | backup restore runbook exists and is readable |
| `rollback_plan_present` | PASS | rollback section found in runbook |
| `backup_policy_present` | PASS | backup policy exists and is valid JSON |
| `encryption_policy_enforced` | PASS | encryption policy enforced with algorithm=AES-256 |
| `restore_workflow_declared` | PASS | workflow exists: .github/workflows/backup-restore-drill.yml |
| `source_restore_evidence_fresh` | PASS | source data-restore evidence freshness check passed |
| `nonprod_dry_run` | PASS | dry-run environment accepted |

- Raw JSON: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/backup-restore-drill-20260223T030525Z.json`
