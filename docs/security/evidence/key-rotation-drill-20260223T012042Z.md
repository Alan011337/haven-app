# Key Rotation Dry-Run Drill

- Schema version: 1.1.0
- Generated at (UTC): 2026-02-23T01:20:42.397461+00:00
- Dry run: YES
- KMS provider: mock-kms
- Checks passed: 5/5
- Overall: PASS

| Check | Result | Detail |
| --- | --- | --- |
| `runbook_present` | PASS | runbook file exists and is readable |
| `policy_contract_passed` | PASS | policy contract satisfied |
| `env_separation_enforced` | PASS | prod secret manager required and prohibited secret files absent |
| `rollback_plan_present` | PASS | rollback section found in runbook |
| `nonprod_dry_run` | PASS | dry-run environment accepted |

- Raw JSON: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/key-rotation-drill-20260223T012042Z.json`
