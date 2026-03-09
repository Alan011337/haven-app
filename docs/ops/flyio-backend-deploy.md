# Haven Backend Deploy on Fly.io

## Scope
- Backend service on Fly.io.
- Includes one `app` process (API) and one `worker` process (notification outbox dispatch loop).
- Frontend and other integrations remain unchanged.

## Files
- `/Users/alanzeng/Desktop/Projects/Haven/backend/fly.toml`
- `/Users/alanzeng/Desktop/Projects/Haven/backend/Dockerfile.fly`
- `/Users/alanzeng/Desktop/Projects/Haven/scripts/deploy-fly-backend.sh`

## Required Environment Variables
- `FLY_API_TOKEN`
- `FLY_APP_NAME`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `SECRET_KEY`
- `CORS_ORIGINS` (JSON array string)

## Optional Environment Variables
- `AI_ROUTER_REDIS_URL`（Fly secrets；production `backend/fly.toml` 會把 `AI_ROUTER_SHARED_STATE_BACKEND` 固定成 `redis`。若未提供，deploy preflight 也接受既有 `REDIS_URL` 或 `ABUSE_GUARD_REDIS_URL`）
- `ABUSE_GUARD_REDIS_URL`（Fly secrets；production `backend/fly.toml` 會把 `ABUSE_GUARD_STORE_BACKEND` 固定成 `redis`）
- `FLY_REGION` (default `nrt`)
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `GEMINI_API_KEY`
- `BILLING_STRIPE_SECRET_KEY`
- `BILLING_STRIPE_WEBHOOK_SECRET`
- `BILLING_STRIPE_PRICE_ID`
- `BILLING_STRIPE_SUCCESS_URL`
- `BILLING_STRIPE_CANCEL_URL`
- `BILLING_STRIPE_PORTAL_RETURN_URL`

## Deploy
```bash
cd /Users/alanzeng/Desktop/Projects/Haven
bash scripts/deploy-fly-backend.sh
```

- Preflight contract:
  - if `backend/fly.toml` pins `AI_ROUTER_SHARED_STATE_BACKEND=redis`, deploy fails unless `AI_ROUTER_REDIS_URL`、`REDIS_URL`、或 `ABUSE_GUARD_REDIS_URL` 其中之一已存在於當前 shell 或 Fly secrets。
  - if `backend/fly.toml` pins `ABUSE_GUARD_STORE_BACKEND=redis`, deploy fails unless `ABUSE_GUARD_REDIS_URL` is provided in the current shell or already exists in Fly secrets for `FLY_APP_NAME`.

## Post-Deploy Verification
```bash
HOME=/tmp /tmp/flybin/flyctl status --app "$FLY_APP_NAME"
HOME=/tmp /tmp/flybin/flyctl checks list --app "$FLY_APP_NAME"
curl -fsS "https://${FLY_APP_NAME}.fly.dev/health"
curl -fsS "https://${FLY_APP_NAME}.fly.dev/health/slo"
```

## Rollback
1. List releases:
```bash
HOME=/tmp /tmp/flybin/flyctl releases --app "$FLY_APP_NAME"
```
2. Roll back to previous stable release:
```bash
HOME=/tmp /tmp/flybin/flyctl releases rollback --app "$FLY_APP_NAME"
```
3. Emergency stop for async path:
- set `NOTIFICATION_OUTBOX_ENABLED=false` and redeploy.
