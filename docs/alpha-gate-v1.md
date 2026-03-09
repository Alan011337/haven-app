# Haven Alpha Gate v1

## Scope
Alpha 內測 Gate v1 目標：
- 只允許 allow-list 測試者進入（alpha 環境才 enforce）
- Core loop 可完整跑通（Daily Sync -> Daily Card -> Appreciation）
- PostHog 事件可觀測且不送 PII
- WebSocket 開啟並具重連/降級
- Web Push + Email fallback 可用，且可由 feature flag 快速止血

## Alpha Allow-list 維運

### Envs
- `ENV=alpha`
- `ALLOWLIST_ENFORCED=true`
- `ALLOWLIST_ENFORCED_ENVS=alpha`
- `ALLOWED_TEST_EMAILS="a@example.com,b@example.com"` 或 `ALLOWED_TEST_EMAILS_JSON='["a@example.com"]'`

### 行為
- 註冊與登入都會檢查 allow-list。
- 非 allow-list 一律返回統一訊息：`邀請制內測：目前僅開放受邀測試者。`
- 不暴露帳號存在性。

### 名單更新流程
1. 在 Fly alpha app 設定 secrets：
   - `fly secrets set ALLOWED_TEST_EMAILS="..." --app <alpha-api-app>`
2. 重新部署或 machine restart。
3. 用 `scripts/alpha-gate-v1-curl-check.sh` 驗證 allow/deny 路徑。

## PostHog（隱私策略）

### Distinct ID
- 強制用 `user_id`（UUID）
- 不使用 email 作 distinct_id

### 禁止欄位
事件 props 會過濾以下 key 片段：
- `email`, `token`, `password`, `secret`, `authorization`, `cookie`, `content`, `journal`, `body_text`, `raw`

### Alpha 最低必收事件
- Auth/entry: `signup_completed`, `login_succeeded`, `logout_clicked`, `token_refresh_succeeded`, `token_refresh_failed`, `allowlist_denied`
- Core loop: `daily_sync_submitted`, `daily_card_revealed`, `card_answer_submitted`, `appreciation_sent`, `daily_loop_completed`
- Security/runtime: `cors_preflight_failed`, `authz_denied_object_level`, `unauthorized_request`
- Realtime: `ws_connected`, `ws_disconnected`, `ws_reconnect_attempted`, `realtime_fallback_activated`
- Notifications: `webpush_subscribed`, `webpush_sent`, `email_notification_queued`, `email_notification_sent`

## Feature Flags / Kill Switch
- `websocket_realtime_enabled` / `disable_websocket_realtime`
- `webpush_enabled` / `disable_webpush`
- `email_notifications_enabled` / `disable_email_notifications`
- `timeline_cursor_enabled` / `disable_timeline_cursor`
- `safety_mode_enabled` / `disable_safety_mode`

預設關閉優先順序（止血）
1. 關 WebPush
2. 關 WebSocket realtime（前端降級 polling/manual refresh）
3. 關 email notifications（保護寄信成本/供應商故障）

## Fly Secrets 建議清單

### Backend (server-only)
- `POSTHOG_ENABLED`
- `POSTHOG_API_KEY`
- `POSTHOG_HOST`
- `ALLOWLIST_ENFORCED`
- `ALLOWLIST_ENFORCED_ENVS`
- `ALLOWED_TEST_EMAILS` 或 `ALLOWED_TEST_EMAILS_JSON`
- `WEBSOCKET_ENABLED`
- `WEBPUSH_ENABLED`
- `PUSH_NOTIFICATIONS_ENABLED`
- `PUSH_VAPID_PUBLIC_KEY`
- `PUSH_VAPID_PRIVATE_KEY`
- `EMAIL_NOTIFICATIONS_ENABLED`
- `RESEND_API_KEY` / SMTP provider secrets

### Frontend
- `NEXT_PUBLIC_POSTHOG_KEY`
- `NEXT_PUBLIC_POSTHOG_HOST`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_WS_URL`
- `NEXT_PUBLIC_WEBPUSH_ENABLED`
- `NEXT_PUBLIC_PUSH_VAPID_PUBLIC_KEY`
- `NEXT_PUBLIC_WEBSOCKET_ENABLED`

## QA 測試步驟

### Android Chrome
1. 登入 allow-list 帳號。
2. 完成 Daily Sync / Daily Card / Appreciation。
3. 關閉網路再恢復，確認 WS 重連與 fallback banner 行為。
4. 啟用通知權限，確認可建立 push subscription。

### iOS Safari / Add to Home Screen
1. 先將站點加入主畫面再開啟（Web App 模式）。
2. 驗證 push permission/subscription。
3. 若裝置或情境不支援 Web Push，確認 Email fallback 仍可收到通知。

## Dashboard 建議（PostHog）
- `ws_connected_rate = ws_connected / active_users`
- `realtime_fallback_rate = realtime_fallback_activated / ws_connected`
- `webpush_subscribed_rate = webpush_subscribed(status=ok) / active_users`
- `webpush_sent_rate = webpush_sent / notification_trigger_total`
- `email_sent_rate = email_notification_sent / email_notification_queued`
- `daily_loop_completion_rate = daily_loop_completed / daily_sync_submitted`

## 常見翻車排查

### CORS / Cookie
- 檢查 preflight：`Access-Control-Allow-Origin` 與 `Access-Control-Allow-Credentials`。
- 前端 API 呼叫必須 `credentials: include` / `withCredentials: true`。

### WebSocket
- 看 `ws_disconnected` close code bucket。
- 若重連達上限，前端應顯示 fallback banner，不應阻斷核心 HTTP 寫入。

### Push
- Service Worker 是否註冊成功。
- 檢查 `NEXT_PUBLIC_PUSH_VAPID_PUBLIC_KEY` 與後端 VAPID private key 配對。

### Service Worker Cache
- 更新版本後若行為異常，清除 SW + site data 後重試。

## Rollback Runbook

### 第一層（即時止血）
- 用 feature flags / env 關閉高風險功能：
  - `WEBSOCKET_ENABLED=false`
  - `WEBPUSH_ENABLED=false`
  - `EMAIL_NOTIFICATIONS_ENABLED=false`

### 第二層（平台回滾）
- Fly deploy rollback：
  - `fly releases --app <app>`
  - `fly deploy --image <previous-image> --app <app>` 或 `fly machine update/rollback` 按現行流程

### 回滾後驗證
- 跑 `scripts/alpha-gate-v1-curl-check.sh`
- 跑 `scripts/alpha-gate-v1-backend-check.sh`
