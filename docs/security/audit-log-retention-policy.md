# Audit Log Retention Policy (Baseline)

Last updated: 2026-02-17

## Scope

- Table: `audit_events`
- Data class: security/forensics telemetry for critical mutating endpoints
- Cross-policy artifact: `docs/security/data-retention-policy.json`

## Baseline Rules

1. Default retention window is `365` days.
2. Records older than retention cutoff are purged by batch job.
3. Purge operation must be deterministic and auditable (`before_count`, `deleted_count`, `after_count`, `cutoff_iso`).
4. Retention value must be a positive integer (`AUDIT_LOG_RETENTION_DAYS > 0`).

## Runtime Controls

- Config key: `AUDIT_LOG_RETENTION_DAYS` (default `365`)
- Purge logic: `backend/app/services/audit_log_retention.py`
- Local runner: `backend/scripts/run_audit_log_retention.py`
- Contract gate: `backend/scripts/check_data_retention_contract.py`

## Verification

Run local purge dry execution in a non-production environment:

```bash
cd backend
venv/bin/python scripts/run_audit_log_retention.py --retention-days 365
```

Security gate coverage:

- `backend/tests/test_audit_log_security_controls.py`
  - denied/error audit event coverage
  - retention purge correctness (`old deleted`, `fresh kept`)
- `backend/scripts/validate_security_evidence.py --kind audit-log-retention --contract-mode strict --max-age-days ${AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS:-14}`
  - evidence freshness guard for release gate

## Rollback

If purge behavior is incorrect:

1. Stop scheduled retention runs.
2. Restore from latest encrypted backup snapshot.
3. Patch retention logic + tests before re-enabling purge.
