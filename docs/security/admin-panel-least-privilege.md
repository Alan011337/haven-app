# CS Admin Least-Privilege Baseline

## Purpose
- Provide customer-support operators with operational visibility and targeted recovery actions.
- Enforce least privilege so CS can inspect system state without reading private user content.

## Runtime controls
- Feature flag: `CS_ADMIN_ENABLED` must be `true` to enable admin endpoints.
- Identity allowlist: `CS_ADMIN_ALLOWED_EMAILS` (comma-separated lowercase emails).
- Guard dependency: `require_admin_user` in `/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/deps.py`.
- Router scope: `/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/admin.py`.

## Allowed actions
- `GET /api/admin/users/{user_id}/status`
  - Returns account status + aggregate counts only.
  - No journal/card content fields returned.
- `GET /api/admin/audit-events`
  - Returns action metadata only.
  - No raw `metadata_json` body returned.
- `POST /api/admin/users/{user_id}/unbind`
  - Manual unbind with bidirectional consistency check.
  - Every action emits an audit event.

## Security test coverage
- `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_admin_authorization_matrix.py`
  - allowlisted admin can read status/list events/unbind
  - non-admin user receives `403`
  - disabled admin panel returns `403`
  - response payload excludes sensitive content fields

## Observability
- Admin actions are written to audit log via `record_audit_event(...)`.
- Event names:
  - `ADMIN_VIEW_USER_STATUS`
  - `ADMIN_LIST_AUDIT_EVENTS`
  - `ADMIN_UNBIND_PARTNER`

## Rollback
1. Set `CS_ADMIN_ENABLED=false` in runtime config and redeploy.
2. If emergency rollback is required, revert:
   - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/routers/admin.py`
   - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/api/deps.py`
   - `/Users/alanzeng/Desktop/Projects/Haven/backend/app/main.py`
   - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_admin_authorization_matrix.py`
3. Re-run security gate:
   - `cd /Users/alanzeng/Desktop/Projects/Haven/backend && bash scripts/security-gate.sh`
