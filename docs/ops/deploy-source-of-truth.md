# Deployment Source of Truth

## Decision
- Production deployment source of truth is Fly.io.
- Active manifests:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/fly.toml`
  - `/Users/alanzeng/Desktop/Projects/Haven/frontend/fly.toml`
- Backend production manifest pins `AI_ROUTER_SHARED_STATE_BACKEND=redis`; deploy preflight accepts `AI_ROUTER_REDIS_URL`, `REDIS_URL`, or `ABUSE_GUARD_REDIS_URL` from deploy secrets, but never from repo files.

## Render Blueprint Status
- `/Users/alanzeng/Desktop/Projects/Haven/render.yaml` is archived reference only.
- It is kept for migration history, not for active deploys.

## Contract Gate
- Validation script:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/scripts/check_deploy_source_of_truth.py`
- Contract test:
  - `/Users/alanzeng/Desktop/Projects/Haven/backend/tests/test_deploy_source_of_truth_contract.py`

## Rollback
1. If Fly deploy is unhealthy, run feature-flag rollback first.
2. If needed, run `flyctl releases rollback` to previous healthy release.
3. Do not re-enable Render deployment without an explicit architecture decision record.
