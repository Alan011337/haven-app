# API Inventory Owner Attestation Runbook (API9)

Last updated: 2026-02-17

## Goal

Keep API inventory ownership metadata fresh and accountable.

## Sources

1. API inventory snapshot: `docs/security/api-inventory.json`
2. Owner attestation source: `docs/security/api-inventory-owner-attestation.json`
3. CODEOWNERS sync source: `.github/CODEOWNERS`

## Local Validation

Run before merge:

1. `cd backend && venv/bin/python scripts/export_api_inventory.py --check`
2. `cd backend && venv/bin/python scripts/check_api_inventory_owner_attestation.py`

## Monthly CI Check

Workflow: `.github/workflows/api-inventory-attestation.yml`

Schedule: monthly (`workflow_dispatch` also supported).

If check fails, workflow opens/updates an alert issue.

## Update Procedure

1. Regenerate inventory if routes changed.
2. Ensure each `owner_team` in inventory has one attestation row.
3. Refresh `attested_at` and `attested_by` for each owner row.
4. Keep `codeowners_refs` aligned with `.github/CODEOWNERS` path patterns.
5. Keep `updated_at >= max(owners[].attested_at)`.
6. Keep `min_attestation_days_remaining` aligned with reminder policy (default 14 days).

## Pass Criteria

1. No missing/stale owner teams between inventory and attestation file.
2. No stale attestation over `max_attestation_age_days` (default 90).
3. No owner attestation within `min_attestation_days_remaining` (or refresh immediately).
4. All `codeowners_refs` exist in `.github/CODEOWNERS`.

## Failure Handling

1. Treat as P0 security governance failure.
2. Block release until attestation and CODEOWNERS drift are fixed.
