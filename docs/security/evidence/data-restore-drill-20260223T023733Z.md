# Data Restore Rehearsal Drill

- Schema version: 1.1.0
- Generated at (UTC): 2026-02-23T02:37:33.753240+00:00
- Dry run: YES
- Source evidence kind: data-soft-delete-purge
- Source evidence path: docs/security/evidence/data-soft-delete-purge-20260223T023733Z.json
- Source evidence max age days: 35
- Checks passed: 5/5
- Overall: PASS

| Check | Result | Detail |
| --- | --- | --- |
| `runbook_present` | PASS | restore rehearsal runbook exists and is readable |
| `rollback_plan_present` | PASS | rollback section found in runbook |
| `lifecycle_contract_passed` | PASS | data deletion lifecycle contract satisfied |
| `source_purge_evidence_fresh` | PASS | source purge evidence freshness check passed |
| `nonprod_dry_run` | PASS | dry-run environment accepted |

- Raw JSON: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/data-restore-drill-20260223T023733Z.json`
