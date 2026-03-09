# Device/Session Hardening (ID-01)

Last updated: 2026-02-23

## Goal

Harden authentication sessions with replay-resistant refresh token rotation and device binding.

## Implemented Controls

1. Refresh session table (`auth_refresh_sessions`) with:
   - `current_token_hash`
   - `device_id`
   - `expires_at`
   - `revoked_at` / `replayed_at`
   - `rotation_counter`
2. `POST /api/auth/token` issues:
   - short-lived access token
   - rotating refresh token (when `REFRESH_TOKEN_ROTATION_ENABLED=true`)
3. `POST /api/auth/refresh` validates:
   - token type is `refresh`
   - `sub/sid/jti` binding
   - user/session ownership
   - device binding consistency
4. Replay handling:
   - stale/mismatched refresh token revokes refresh session
   - subsequent refresh attempts fail closed
5. Access-token guard:
   - `get_current_user` rejects tokens with `typ=refresh`

## Feature Flag / Rollback

1. `REFRESH_TOKEN_ROTATION_ENABLED=false` disables refresh issuance/rotation and falls back to access-token-only login behavior.
2. Rollback path:
   - set `REFRESH_TOKEN_ROTATION_ENABLED=false`
   - redeploy
   - optional DB rollback: downgrade migration `f1a2b3c4d5e6`

## Verification

```bash
cd /Users/alanzeng/Desktop/Projects/Haven/backend
PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_auth_token_endpoint_security.py \
  tests/test_auth_token_misuse_regression.py \
  tests/test_auth_token_misuse_write_paths.py

PYTHONUTF8=1 PYTHONPATH=. .venv-gate/bin/python scripts/check_endpoint_authorization_matrix.py
```

## Security Notes

1. Raw refresh tokens are never persisted.
2. Stored values are SHA-256 hashes only.
3. Logs avoid token content; rejection logging includes reason only.
