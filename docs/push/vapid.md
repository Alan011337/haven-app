# Web Push VAPID Policy (P1 Skeleton)

## Why
- 確保 Web Push 發送身份可驗證，避免未授權推播。
- 降低金鑰外洩與長期 JWT 被重放的風險。

## How
- 使用 VAPID (ES256) 作為 Web Push 授權基礎。
- JWT claims contract：
  - `aud`: push service origin
  - `sub`: `mailto:` 或 HTTPS 聯絡資訊
  - `exp`: 不可超過 24 小時（`PUSH_JWT_MAX_EXP_SECONDS=86400`）
- 環境變數：
  - `PUSH_VAPID_PUBLIC_KEY`
  - `PUSH_VAPID_PRIVATE_KEY`
  - `PUSH_VAPID_SUBJECT`
  - `PUSH_JWT_MAX_EXP_SECONDS`

## What
- 前端 service worker: `/Users/alanzeng/Desktop/Projects/Haven/frontend/public/sw-push.js`
- 前端註冊 helper: `/Users/alanzeng/Desktop/Projects/Haven/frontend/src/lib/push.ts`
- 後端 push 開關與策略設定: `/Users/alanzeng/Desktop/Projects/Haven/backend/app/core/config.py`

## DoD
- 無有效 VAPID key 時，不執行實際推播（僅 dry-run/回退）。
- JWT `exp` 預設 <= 24h，超過即視為配置違規。
- 金鑰輪替流程有可操作 runbook（下方）。

## Key Rotation Runbook
1. 產生新 VAPID key pair（保留舊 key 於短暫切換期）。
2. 將新 key 先部署到 non-prod 驗證 subscribe + dry-run。
3. 生產環境先更新 `PUSH_VAPID_PUBLIC_KEY`，讓新訂閱逐步轉換。
4. 再更新 `PUSH_VAPID_PRIVATE_KEY`，監看失敗率與 invalid ratio。
5. 超過門檻立即回滾到前一組 key。

## Debug Checklist
1. 推播完全收不到：
   - 檢查 `PUSH_NOTIFICATIONS_ENABLED` 是否開啟。
   - 檢查前端是否成功註冊 `/sw-push.js`。
2. 大量 401/403：
   - 檢查 VAPID private/public key 是否成對。
   - 檢查 JWT `aud/sub/exp` 是否符合 provider 要求。
3. 新舊裝置表現不一致：
   - 檢查是否仍有舊 key 建立的 subscription 未更新。
   - 先跑 dry-run 觀察 sampled 訂閱狀態，再做 cleanup。

## Push/VAPID readiness check (P1-C-WEB-PUSH)
- Script: `backend/scripts/check_push_vapid_readiness.py` — exit 0 when `PUSH_VAPID_PUBLIC_KEY` and `PUSH_VAPID_PRIVATE_KEY` are set, else 1. Use in CI to enforce push config or skip in non-push envs.

## E2E validation checklist (P1-C-WEB-PUSH)
- **Runtime**: Ensure `PUSH_NOTIFICATIONS_ENABLED=true` and VAPID keys set in the target env. Backend uses pywebpush/VAPID to send; provider-enabled runtime required for real delivery.
- **VAPID**: Run `python -c "from pywebpush import webpush; ..."` or backend health check that validates key pair; confirm JWT `aud`/`sub`/`exp` match provider expectations.
- **Subscribe**: In browser, register service worker (`/sw-push.js`), call push subscribe, POST subscription to backend; confirm subscription stored (e.g. `push_subscriptions` table).
- **Trigger**: Trigger a notification (e.g. journal_created) and confirm backend dispatches via `notification_multichannel`; check logs for success/failure and push SLI metrics (`GET /health/slo` push section).
- **Delivery**: On a real device/browser with push enabled, confirm notification appears; optional: use a test page that logs `push` events in the service worker.
- **CI**: For PRs without prod VAPID, use dry-run or allow-missing so E2E is validated only in staging/prod.

