# Authorization Matrix (BOLA)

- Canonical mutating matrix: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/endpoint-authorization-matrix.json`
- Canonical read matrix: `/Users/alanzeng/Desktop/Projects/Haven/docs/security/read-authorization-matrix.json`

## Coverage contract
- Every core API route that reads/writes user-owned resources must have:
  - matrix row (owner team, subject scope, test_ref)
  - idempotency policy annotation for exempt routes (`idempotency_policy: "exempt"`)
  - at least one legal-subject test and one illegal-subject test (BOLA focus)
  - for mutating routes with path params (`{...}`), `test_ref` must include an explicit deny marker:
    - `# AUTHZ_DENY_MATRIX: <METHOD> <PATH>`
- CI gates:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_endpoint_authorization_matrix.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_read_authorization_matrix.py`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/export_endpoint_authorization_matrix.py --check-current`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/export_read_authorization_matrix.py --check-current`
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/security/test_bola_matrix.py`

## Core resources
- Admin operations (`POST /api/admin/users/{user_id}/unbind`) guarded by allowlisted admin identities
- User profile / pairing
- Journals
- Cards / card sessions / deck history
- Notifications
- Repair flow (`POST /api/mediation/repair/start`, `POST /api/mediation/repair/step-complete`)
- Billing reconciliation
- CUJ telemetry ingest (`POST /api/users/events/cuj`)
- Core-loop telemetry ingest (`POST /api/users/events/core-loop`)

## Local verify
```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_endpoint_authorization_matrix.py
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_read_authorization_matrix.py
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/export_endpoint_authorization_matrix.py --check-current
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/export_read_authorization_matrix.py --check-current
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider tests/security/test_bola_matrix.py
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider tests/test_admin_authorization_matrix.py
```
