# Secrets & Key Rotation Runbook (SEC-05 / SEC-08)

## Purpose
- Keep secrets out of source control.
- Enforce periodic key rotation with auditable dry-run evidence.
- Ensure rollback path is explicit before any key change.

## Scope
- Backend required keys:
  - `DATABASE_URL`
  - `OPENAI_API_KEY`
  - `SECRET_KEY`
- Billing:
  - `BILLING_STRIPE_WEBHOOK_SECRET`
- Notification:
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL`
- Field-level encryption:
  - `FIELD_LEVEL_ENCRYPTION_ENABLED`
  - `FIELD_LEVEL_ENCRYPTION_KEY`
- Abuse guard:
  - `ABUSE_GUARD_STORE_BACKEND`
  - `ABUSE_GUARD_REDIS_URL`
  - `ABUSE_GUARD_REDIS_KEY_PREFIX`

## Rotation Cadence
- Default policy source: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/secrets-key-management-policy.json`
- Current cadence:
  - backend/billing/notification: 90 days
  - abuse_guard: 180 days

## Preconditions
- Do not run production rotation without approved maintenance window.
- Validate contract first:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_secrets_key_management_contract.py
```

## Dry-Run Drill (Required Before Real Rotation)
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/key-rotation-drill.sh
```

Expected artifacts:
- `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/key-rotation-drill-*.json`
- `/Users/alanzeng/Desktop/Projects/Haven/docs/security/evidence/key-rotation-drill-*.md`

## Field Encryption Key Generation
Generate a Fernet key (do not commit output):
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Rollout baseline:
1. Set `FIELD_LEVEL_ENCRYPTION_ENABLED=true`.
2. Set `FIELD_LEVEL_ENCRYPTION_KEY=<generated-key>`.
3. Run `scripts/check_env.py` and `scripts/security-gate.sh`.
4. Deploy canary first, monitor decrypt/config errors in logs.

## Production Rotation Procedure (High level)
1. Generate replacement key in secret manager (KMS-backed provider).
2. Stage key in non-prod environment and run release gates.
3. Deploy app reading new key version.
4. Verify health, auth, billing webhook signature, and notification pipelines.
5. Revoke previous key version only after verification window passes.

## Rollback Plan
1. Repoint secret manager reference to previous key version.
2. Restart affected services.
3. Re-run:
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/release-gate-local.sh
```
4. Record rollback reason in incident notes and schedule postmortem.

## Debug Checklist
- Contract failure:
  - run `backend/scripts/check_secrets_key_management_contract.py`
  - verify required keys in `backend/scripts/check_env.py` still match policy
- Drill evidence missing:
  - re-run `bash scripts/key-rotation-drill.sh`
  - confirm write permissions under `docs/security/evidence`
- Freshness gate failure:
  - generate new drill artifact and re-run security gate
