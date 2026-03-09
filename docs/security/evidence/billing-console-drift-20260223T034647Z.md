# Billing Console Drift Audit

- Generated at (UTC): 2026-02-23T03:46:47.357357+00:00
- Provider: stripe
- Dry run: YES
- Checks passed: 7/7
- Overall: PASS

| Check | Result | Detail |
| --- | --- | --- |
| `runbook_present` | PASS | runbook exists and is non-empty |
| `policy_contract_passed` | PASS | policy contract satisfied |
| `store_compliance_contract_passed` | PASS | store compliance contract satisfied |
| `webhook_secret_configured` | PASS | billing webhook secret is configured |
| `webhook_tolerance_within_policy` | PASS | runtime tolerance=300s within max=300s |
| `async_mode_within_policy` | PASS | runtime async_mode=False allowed |
| `nonprod_dry_run` | PASS | dry-run environment accepted |

- Raw JSON: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/billing-console-drift-20260223T034647Z.json`
